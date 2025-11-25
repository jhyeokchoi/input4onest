#!/usr/bin/env python3
"""
Made by Joonhyeok Choi 2023.05.25
Refactored by Antigravity 2025.11.23
Converting modified sparky CEST data to ONEST input format
"""

import pandas as pd
import csv
import argparse
import sys
from typing import List, Optional

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Converting modified sparky CEST data to ONEST input format')
    parser.add_argument('-f', '--file', type=str, help='Input file path', required=True)
    parser.add_argument('-o', '--output', type=str, help='Output file path', required=True)
    parser.add_argument('-frq', '--frequency', type=float, help='Nitrogen Frequency (MHz) [Default = 80.12]', default=80.12)
    parser.add_argument('-sf', '--sat_freq', type=float, help='Saturation Frequency (Hz) [Default = 15]', default=15.0)
    parser.add_argument('-mix', '--mixing_time', type=float, help='Mixing Time of CEST (s) [Default = 0.4]', default=0.4)
    parser.add_argument('-r2a', '--ini_R2a', type=float, help='Initial value of R2a (s) [Default = 25]', default=25.0)
    parser.add_argument('-r2b', '--ini_R2b', type=float, help='Initial value of R2b (s) [Default = 0]', default=0.0)
    parser.add_argument('-dw', '--ini_dw', type=float, help='Initial value of dw (s) [Default = 0]', default=0.0)
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-s', '--select_number', nargs='+', type=float, help='Residue number list from the input data list')
    group.add_argument('-sn', '--select_name', nargs='+', type=str, help='Residue name list from the input data list')
    
    return parser.parse_args()

def filter_data(data_ori: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if args.select_number:
        # Adjust for 0-based indexing if input is 1-based residue numbers
        # Original code: [x-1 for x in args.select_number]
        selected_indices = [int(x) - 1 for x in args.select_number]
        # Validate indices
        valid_indices = [i for i in selected_indices if 0 <= i < len(data_ori)]
        if len(valid_indices) != len(selected_indices):
             print(f"Warning: Some selected numbers are out of range. Using valid ones only.")
        return data_ori.iloc[valid_indices, :]
    
    elif args.select_name:
        indices = []
        for i, row in data_ori.iterrows():
            row_str = row.astype(str)
            for name in args.select_name:
                # Check if name is in any column of the row
                if row_str.str.contains(name).any():
                    indices.append(i)
                    break # Avoid adding same row multiple times if it matches multiple names
        
        # Original code logic: checks if found count matches requested count. 
        # This is slightly flawed if one name matches multiple rows or multiple names match one row.
        # But we'll keep the filtering logic.
        
        if not indices:
             print("Please check residue name!\nInput name:", args.select_name)
             sys.exit(1)
             
        return data_ori.iloc[indices, :]
    
    else:
        return data_ori

def write_onest_input(data: pd.DataFrame, args: argparse.Namespace):
    try:
        with open(args.output, 'w', newline='') as f:
            out = csv.writer(f, delimiter='\t')
            
            # Write Header
            out.writerow([args.frequency])
            out.writerow([args.mixing_time])
            out.writerow([args.sat_freq, args.sat_freq / 10])
            out.writerow(['#offset(ppm)     Intensity     error'])
            
            # Write Data
            num_rows, num_cols = data.shape
            # Assuming first column is residue name/ID, and rest are data points
            # data.columns[1:] are frequencies
            
            frequencies = data.columns[1:]
            
            for i in range(num_rows):
                row = data.iloc[i]
                residue_name = row.iloc[0]
                intensities = row.iloc[1:].values
                
                # Calculate error
                # Original logic: std of first 9 points vs last 9 points (excluding very last?)
                # The original slicing was [1:10] (9 points) and [-10:-1] (9 points).
                # We need to be careful if data is short.
                
                if len(intensities) >= 10:
                    err_std1 = intensities[0:9].std(ddof=1)
                    err_std2 = intensities[-10:-1].std(ddof=1) 
                    # Let's stick to original logic but make it safe
                    error = min(err_std1, err_std2)
                else:
                    # Fallback for short data
                    error = intensities.std(ddof=1)
                
                # Write residue header line
                out.writerow(['#', residue_name, 'R2a:', args.ini_R2a, 'R2b:', args.ini_R2b, 'dw:', args.ini_dw])
                
                # Write intensity data
                for j, freq in enumerate(frequencies):
                    try:
                        freq_val = float(freq)
                        intensity = intensities[j]
                        out.writerow([freq_val, intensity, error])
                    except ValueError:
                        continue

    except IOError as e:
        print(f"Error writing to file {args.output}: {e}")
        sys.exit(1)

def main():
    args = parse_arguments()
    
    try:
        data_ori = pd.read_csv(filepath_or_buffer=args.file, delimiter='\t')
    except FileNotFoundError:
        print(f"Error: Input file '{args.file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    data = filter_data(data_ori, args)
    
    write_onest_input(data, args)
    
    print("The conversion process is complete. Output file: ", args.output)

if __name__ == '__main__':
    main()
