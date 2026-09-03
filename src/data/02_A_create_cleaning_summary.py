from pathlib import Path
import pandas as pd

# Project path
PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Find cleaned CSV files
cleaned_files = sorted(
    PROCESSED_DIR.glob("cleaned_*.csv")
)

print(f"Cleaned files found: {len(cleaned_files)}")

summaries = []

for file_path in cleaned_files:

    print(f"Reading: {file_path.name}")

    df = pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        low_memory=False
    )

    summary = {
        "dataset": file_path.name,
        "rows_after_cleaning": len(df),
        "columns_after_cleaning": len(df.columns),
        "missing_values_after_cleaning": int(
            df.isna().sum().sum()
        ),
        "duplicate_rows_remaining": int(
            df.duplicated().sum()
        )
    }

    summaries.append(summary)


# Create summary DataFrame
summary_df = pd.DataFrame(summaries)

# Save report
output_file = (
    REPORTS_DIR / "cleaning_summary.csv"
)

summary_df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print("\n======================================")
print("CLEANING SUMMARY CREATED")
print("======================================")
print(f"Saved to:")
print(output_file)