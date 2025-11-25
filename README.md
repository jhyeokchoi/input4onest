# input4onest

**input4onest** is a Python script designed to generate input files for [ONEST](https://github.com/jhyeokchoi/ONEST) (Optimization of NMR Ensemble Structure) by converting modified Sparky CEST (Chemical Exchange Saturation Transfer) data.

## Features
- **ONEST Compatibility**: Converts tab-separated values (TSV) from Sparky into the specific format required by ONEST.
- **Flexible Filtering**: Allows filtering of data by residue number or residue name.
- **Automatic Error Estimation**: Calculates error estimates based on noise levels at the edges of the spectrum (using the first and last data points).
- **Parameter Customization**: Supports command-line arguments for key NMR parameters such as Nitrogen Frequency, Saturation Frequency, and Mixing Time.

## Requirements
- Python 3.x
- pandas

## Installation

1. Clone the repository or download the script:
   ```bash
   git clone <repository_url>
   cd input4onest
   ```

2. Install the required Python package:
   ```bash
   pip install -r requirements.txt
   ```

## Input Data Format
The input file must be a **Tab-Separated Values (TSV)** file with the following structure:

- **Header Row**: 
  - The first column should be labeled (e.g., `Residue`).
  - Subsequent columns must represent the frequency offsets (typically in Hz).
- **Data Rows**: 
  - The first column contains the residue identifier (e.g., `A1`, `G2`).
  - Subsequent columns contain the intensity values corresponding to the frequency offsets in the header.

**Example Input (`example/example_input.tsv`):**
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
| **Select Number** | `-s`, `--select_number` | `list` | `None` | Filter specific residues by number (space-separated). |
| **Select Name** | `-sn`, `--select_name` | `list` | `None` | Filter specific residues by name (space-separated). |

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
Process only specific residues (e.g., Alanine and Glycine):
```bash
python3 input4onest.py -f input_data.tsv -o output.estp -sn A G
```

**4. Filter by Residue Number**
Process only residues with specific numbers (e.g., 10, 12, 15):
```bash
python3 input4onest.py -f input_data.tsv -o output.estp -s 10 12 15
```

## Output Format
The generated output file is formatted for use with **ONEST**. It includes:
- Global parameters (Frequency, Mixing Time, Saturation Frequency).
- Per-residue data blocks containing:
  - Initial estimates for R2a, R2b, and dw.
  - Frequency offsets, intensity values, and calculated errors.
