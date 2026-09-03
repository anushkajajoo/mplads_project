from pathlib import Path
import pandas as pd

# Find the main project folder
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Find the raw data folder
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

print("=" * 50)
print("MPLADS PROJECT SETUP TEST")
print("=" * 50)

# Find all CSV files
csv_files = list(RAW_DATA_DIR.glob("*.csv"))

print(f"\nNumber of CSV files found: {len(csv_files)}")

# Read every dataset
for file in csv_files:
    print("\n" + "-" * 50)
    print(f"File: {file.name}")

    try:
        df = pd.read_csv(file, low_memory=False)

        print(f"Rows: {df.shape[0]}")
        print(f"Columns: {df.shape[1]}")
        print("Status: Successfully read")

    except Exception as e:
        print(f"Error: {e}")

print("\nSETUP TEST COMPLETE")