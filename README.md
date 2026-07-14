# Input4onest

**Input4onest** converts modified Sparky CEST data into input files for
[ONEST](https://github.com/jhyeokchoi/ONEST) (Optimized Novel Exchange
Saturation Transfer).

## Features
- **ONEST Compatibility**: Converts tab-separated values (TSV) from Sparky into the specific format required by ONEST.
- **Validated Input**: Rejects malformed offsets, intensities, duplicate residues, and incomplete rows before writing output.
- **Flexible Filtering**: Filters by the numeric part of a residue ID, a complete residue ID, or a residue code.
- **Automatic Error Estimation**: Estimates noise from non-overlapping regions at the edges of the spectrum.
- **Safe Output**: Atomically replaces the output only after conversion succeeds.
- **Parameter Customization**: Supports command-line arguments for key NMR parameters such as Nitrogen Frequency, Saturation Frequency, and Mixing Time.

## Requirements
- Python 3.9 or newer

No third-party Python packages are required.

### Python compatibility

- Python 3.9: supported and tested
- Python 3.13: supported and tested with Python 3.13.13
- Python 3.14: supported; the script uses only stable standard-library APIs

Run `python3 -m unittest -v` after changing Python versions to verify the local
interpreter and filesystem environment.

## Installation

1. Clone the repository or download the script:
   ```bash
   git clone <repository_url>
   cd input4onest
   ```

2. Optional: verify the program and run its tests:
   ```bash
   python3 -m unittest -v
   ```

## Input Data Format
The input file must be a **Tab-Separated Values (TSV)** file with the following structure:

- **Header Row**: 
  - The first column should be labeled (e.g., `Residue`).
  - Subsequent columns must be unique, finite numeric offsets in **ppm**.
- **Data Rows**: 
  - The first column contains the residue identifier (e.g., `A1`, `G2`).
  - Subsequent columns contain finite numeric intensity values corresponding to the offsets.
  - Residue IDs should combine a letter code and integer number, such as `A1` or `I36`, when filters are used.

At least two offset columns and one residue row are required. Blank data rows are
ignored; incomplete rows and duplicate residue IDs are rejected.

**Simplified input excerpt:**
```tsv
Residue	100.0	101.0	102.0	103.0
A1	0.90	0.80	0.20	0.85
G2	0.95	0.85	0.10	0.90
```

## Usage

Run the script from the command line:

```bash
python3 input4onest.py -f <input_file> -o <output_file> [options]
```

### Arguments

| Argument | Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Input File** | `-f`, `--file` | `str` | **Required** | Path to the input data file (TSV format). |
| **Output File** | `-o`, `--output` | `str` | **Required** | Path to the generated ONEST input file. |
| **Frequency** | `-frq`, `--frequency` | `float` | `80.12` | Nitrogen Frequency (MHz). |
| **Saturation Freq** | `-sf`, `--sat_freq` | `float` | `15.0` | Saturation Frequency (Hz). |
| **Mixing Time** | `-mix`, `--mixing_time` | `float` | `0.4` | Mixing Time of CEST (s). |
| **Initial R2a** | `-r2a`, `--ini_R2a` | `float` | `25.0` | Initial value of R2a (s). |
| **Initial R2b** | `-r2b`, `--ini_R2b` | `float` | `0.0` | Initial value of R2b (s). |
| **Initial dw** | `-dw`, `--ini_dw` | `float` | `0.0` | Initial value of dw (s). |
| **Select Number** | `-s`, `--select_number` | `list[int]` | `None` | Filter by the numeric part of residue IDs (space-separated). |
| **Select Name** | `-sn`, `--select_name` | `list[str]` | `None` | Filter by complete residue IDs or letter codes (space-separated). |

### Examples

**1. Basic Conversion**
Convert `input_data.tsv` to `output.estp` using default parameters:
```bash
python3 input4onest.py -f input_data.tsv -o output.estp
```

**2. Custom NMR Parameters**
Specify frequency, saturation frequency, and mixing time:
```bash
python3 input4onest.py -f input_data.tsv -o output.estp -frq 60.8 -sf 25.0 -mix 0.5
```

**3. Filter by Residue Name**
Process every Alanine and Glycine residue:
```bash
python3 input4onest.py -f input_data.tsv -o output.estp -sn A G
```

To select complete residue IDs instead, use:

```bash
python3 input4onest.py -f input_data.tsv -o output.estp -sn I36 Q49 E51
```

**4. Filter by Residue Number**
Process only residues with specific numbers (e.g., 10, 12, 15):
```bash
python3 input4onest.py -f input_data.tsv -o output.estp -s 10 12 15
```

The number filter examines the number in the residue ID; it does not select TSV
row positions. Every requested number or name must exist, otherwise conversion
fails without creating or replacing the output file.

## Output Format
The generated output file is formatted for use with **ONEST**. It includes:
- Global parameters (Frequency, Mixing Time, Saturation Frequency).
- Per-residue data blocks containing:
  - Initial estimates for R2a, R2b, and dw.
  - Frequency offsets, intensity values, and calculated errors.

For 18 or more points, the error is the smaller sample standard deviation of the
first nine and last nine intensities. For 2–17 points, it is the sample standard
deviation of all intensities. This prevents the edge windows from overlapping.

## Error handling

Validation failures are written to standard error and return a non-zero exit
status. The message identifies the affected row or column where possible. The
output is written through a temporary file, so an existing valid result is not
truncated when conversion fails.
