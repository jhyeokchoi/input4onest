#!/usr/bin/env python3
"""Convert modified Sparky CEST data to the ONEST input format."""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import stat
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


RESIDUE_PATTERN = re.compile(r"^([A-Za-z]+)(-?\d+)$")
EDGE_POINT_COUNT = 9


class ConversionError(Exception):
    """Raised when the input or requested conversion is invalid."""


@dataclass(frozen=True)
class ResidueRecord:
    name: str
    intensities: tuple[float, ...]


@dataclass(frozen=True)
class CestData:
    offsets: tuple[float, ...]
    records: tuple[ResidueRecord, ...]


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert modified Sparky CEST data to ONEST input format"
    )
    parser.add_argument("-f", "--file", required=True, help="Input TSV file")
    parser.add_argument("-o", "--output", required=True, help="Output file")
    parser.add_argument(
        "-frq", "--frequency", type=float, default=80.12,
        help="Nitrogen frequency in MHz (default: 80.12)",
    )
    parser.add_argument(
        "-sf", "--sat_freq", type=float, default=15.0,
        help="Saturation frequency in Hz (default: 15)",
    )
    parser.add_argument(
        "-mix", "--mixing_time", type=float, default=0.4,
        help="CEST mixing time in seconds (default: 0.4)",
    )
    parser.add_argument(
        "-r2a", "--ini_R2a", type=float, default=25.0,
        help="Initial R2a value (default: 25)",
    )
    parser.add_argument(
        "-r2b", "--ini_R2b", type=float, default=0.0,
        help="Initial R2b value (default: 0)",
    )
    parser.add_argument(
        "-dw", "--ini_dw", type=float, default=0.0,
        help="Initial dw value (default: 0)",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s", "--select_number", nargs="+", type=int,
        help="Residue numbers to include, for example: 10 12 15",
    )
    group.add_argument(
        "-sn", "--select_name", nargs="+",
        help="Residue IDs or residue codes to include, for example: I36 Q49 or I Q",
    )
    return parser.parse_args(argv)


def _finite_float(value: str, location: str) -> float:
    try:
        result = float(value.strip())
    except ValueError as exc:
        raise ConversionError(f"{location} must be numeric; got {value!r}") from exc
    if not math.isfinite(result):
        raise ConversionError(f"{location} must be finite; got {value!r}")
    return result


def read_cest_data(path: str | Path) -> CestData:
    input_path = Path(path)
    try:
        with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter="\t"))
    except FileNotFoundError as exc:
        raise ConversionError(f"input file not found: {input_path}") from exc
    except (OSError, UnicodeError) as exc:
        raise ConversionError(f"cannot read input file {input_path}: {exc}") from exc

    if not rows or not any(cell.strip() for cell in rows[0]):
        raise ConversionError("input file is empty or has no header")

    header = rows[0]
    if len(header) < 3:
        raise ConversionError(
            "input must contain a residue column and at least two offset columns"
        )
    if not header[0].strip():
        raise ConversionError("the first header cell (residue column) is empty")

    raw_offsets = [cell.strip() for cell in header[1:]]
    if any(not value for value in raw_offsets):
        raise ConversionError("offset headers cannot be empty")
    offsets = tuple(
        _finite_float(value, f"offset header at column {index}")
        for index, value in enumerate(raw_offsets, start=2)
    )
    if len(set(offsets)) != len(offsets):
        raise ConversionError("offset headers must be unique")

    records: list[ResidueRecord] = []
    seen_residues: set[str] = set()
    expected_columns = len(header)
    for row_number, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != expected_columns:
            raise ConversionError(
                f"row {row_number} has {len(row)} columns; expected {expected_columns}"
            )
        residue = row[0].strip()
        if not residue:
            raise ConversionError(f"row {row_number} has an empty residue ID")
        residue_key = residue.casefold()
        if residue_key in seen_residues:
            raise ConversionError(f"duplicate residue ID at row {row_number}: {residue}")
        seen_residues.add(residue_key)

        intensities = tuple(
            _finite_float(value, f"intensity at row {row_number}, column {column}")
            for column, value in enumerate(row[1:], start=2)
        )
        records.append(ResidueRecord(residue, intensities))

    if not records:
        raise ConversionError("input contains no residue data rows")
    return CestData(offsets, tuple(records))


def _residue_parts(residue: str) -> tuple[str, int] | None:
    match = RESIDUE_PATTERN.fullmatch(residue)
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def filter_data(data: CestData, args: argparse.Namespace) -> CestData:
    if args.select_number:
        requested = set(args.select_number)
        matched_numbers: set[int] = set()
        selected: list[ResidueRecord] = []
        unparseable: list[str] = []
        for record in data.records:
            parts = _residue_parts(record.name)
            if parts is None:
                unparseable.append(record.name)
                continue
            number = parts[1]
            if number in requested:
                selected.append(record)
                matched_numbers.add(number)

        missing = sorted(requested - matched_numbers)
        if missing:
            detail = (
                f"; unrecognized residue IDs: {', '.join(unparseable)}"
                if unparseable
                else ""
            )
            raise ConversionError(f"residue number(s) not found: {missing}{detail}")
        return CestData(data.offsets, tuple(selected))

    if args.select_name:
        requested = {name.casefold(): name for name in args.select_name}
        matched_queries: set[str] = set()
        selected = []
        for record in data.records:
            residue_key = record.name.casefold()
            parts = _residue_parts(record.name)
            code_key = parts[0].casefold() if parts else None
            record_matches = {
                query for query in requested
                if query == residue_key or (code_key is not None and query == code_key)
            }
            if record_matches:
                selected.append(record)
                matched_queries.update(record_matches)

        missing = [requested[key] for key in requested if key not in matched_queries]
        if missing:
            raise ConversionError(f"residue name(s) not found: {missing}")
        return CestData(data.offsets, tuple(selected))

    return data


def estimate_error(intensities: Sequence[float]) -> float:
    """Estimate noise from spectrum edges, avoiding overlapping edge windows."""
    if len(intensities) < 2:
        raise ConversionError("at least two intensity points are required")
    if len(intensities) >= EDGE_POINT_COUNT * 2:
        left = statistics.stdev(intensities[:EDGE_POINT_COUNT])
        right = statistics.stdev(intensities[-EDGE_POINT_COUNT:])
        return min(left, right)
    return statistics.stdev(intensities)


def validate_parameters(args: argparse.Namespace) -> None:
    positive = {
        "frequency": args.frequency,
        "saturation frequency": args.sat_freq,
        "mixing time": args.mixing_time,
    }
    for name, value in positive.items():
        if not math.isfinite(value) or value <= 0:
            raise ConversionError(f"{name} must be a positive finite number")
    initial_values = {
        "R2a": args.ini_R2a,
        "R2b": args.ini_R2b,
        "dw": args.ini_dw,
    }
    for name, value in initial_values.items():
        if not math.isfinite(value):
            raise ConversionError(f"initial {name} must be finite")
    if args.ini_R2a < 0 or args.ini_R2b < 0:
        raise ConversionError("initial R2a and R2b cannot be negative")


def _write_rows(handle, data: CestData, args: argparse.Namespace) -> None:
    writer = csv.writer(handle, delimiter="\t")
    writer.writerow([args.frequency])
    writer.writerow([args.mixing_time])
    writer.writerow([args.sat_freq, args.sat_freq / 10])
    writer.writerow(["#offset(ppm)     Intensity     error"])

    for record in data.records:
        error = estimate_error(record.intensities)
        writer.writerow(
            ["#", record.name, "R2a:", args.ini_R2a, "R2b:", args.ini_R2b, "dw:", args.ini_dw]
        )
        for offset, intensity in zip(data.offsets, record.intensities):
            writer.writerow([offset, intensity, error])


def write_onest_input(data: CestData, args: argparse.Namespace) -> None:
    """Write a complete output atomically so failures do not leave partial files."""
    output_path = Path(args.output)
    temporary_path: Path | None = None
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_mode = (
            stat.S_IMODE(output_path.stat().st_mode) if output_path.exists() else 0o644
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            _write_rows(handle, data, args)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(output_mode)
        os.replace(temporary_path, output_path)
    except OSError as exc:
        raise ConversionError(f"cannot write output file {output_path}: {exc}") from exc
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    try:
        validate_parameters(args)
        data = filter_data(read_cest_data(args.file), args)
        write_onest_input(data, args)
    except ConversionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"The conversion process is complete. Output file: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
