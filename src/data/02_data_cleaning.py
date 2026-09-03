# ============================================================
# MPLADS AI MONITORING SYSTEM
# PHASE 3 - DATA CLEANING & STANDARDIZATION
# ============================================================

from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

CLEANED_DATA_DIR = (
    PROJECT_ROOT / "src" / "data" / "cleaned"
)

REPORTS_DIR = (
    PROJECT_ROOT / "outputs" / "reports"
)

CLEANED_DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. SAFE CSV READING
# ============================================================

def read_csv_safely(file_path):

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin1"
    ]

    last_error = None

    for encoding in encodings:

        try:

            df = pd.read_csv(
                file_path,
                encoding=encoding,
                low_memory=False
            )

            print(f"Encoding used: {encoding}")

            return df

        except Exception as error:

            last_error = error

    raise ValueError(
        f"Could not read {file_path.name}. "
        f"Last error: {last_error}"
    )


# ============================================================
# 3. STANDARDIZE COLUMN NAMES
# ============================================================

def standardize_column_name(column_name):

    name = str(column_name).strip()

    name = name.lower()

    name = name.replace("₹", "rupees")

    name = re.sub(
        r"[\s\-/]+",
        "_",
        name
    )

    name = name.replace("'", "")

    name = re.sub(
        r"[^a-z0-9_]",
        "",
        name
    )

    name = re.sub(
        r"_+",
        "_",
        name
    )

    name = name.strip("_")

    return name


def standardize_column_names(df):

    df = df.copy()

    new_columns = []

    used_names = set()

    for column in df.columns:

        new_name = standardize_column_name(
            column
        )

        if not new_name:
            new_name = "unnamed_column"

        base_name = new_name

        counter = 1

        while new_name in used_names:

            new_name = (
                f"{base_name}_{counter}"
            )

            counter += 1

        used_names.add(new_name)

        new_columns.append(new_name)

    df.columns = new_columns

    return df


# ============================================================
# 4. CLEAN TEXT VALUES
# ============================================================

def clean_text_values(df):

    df = df.copy()

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    missing_strings = {
        "",
        " ",
        "na",
        "n/a",
        "null",
        "none",
        "nan"
    }

    for column in text_columns:

        series = (
            df[column]
            .astype("string")
            .str.replace(
                r"\s+",
                " ",
                regex=True
            )
            .str.strip()
        )

        # Replace common missing representations
        lowered = series.str.lower()

        series = series.mask(
            lowered.isin(missing_strings),
            pd.NA
        )

        # Preserve original text otherwise
        df[column] = series

    return df


# ============================================================
# 5. REMOVE COMPLETELY EMPTY ROWS
# ============================================================

def remove_completely_empty_rows(df):

    before = len(df)

    non_empty = df.dropna(
        how="all"
    )

    removed = before - len(non_empty)

    return non_empty.copy(), removed


# ============================================================
# 6. DETECT SUMMARY / GRAND TOTAL ROWS
# ============================================================

def is_summary_row(row):

    values = row.astype(
        "string"
    ).fillna("")

    text_values = [
        str(value).strip().lower()
        for value in values.tolist()
    ]

    first_value = (
        text_values[0]
        if len(text_values) > 0
        else ""
    )

    summary_keywords = [
        "grand total",
        "total"
    ]

    # Strongest and safest case:
    # first column contains Grand Total / Total
    if first_value in summary_keywords:
        return True

    # Search all columns for grand total
    for value in text_values:

        if value == "grand total":
            return True

    return False


def remove_summary_rows(df):

    if len(df) == 0:

        return df.copy(), 0

    summary_mask = df.apply(
        is_summary_row,
        axis=1
    )

    summary_count = int(
        summary_mask.sum()
    )

    cleaned_df = df.loc[
        ~summary_mask
    ].copy()

    return (
        cleaned_df,
        summary_count
    )


# ============================================================
# 7. REMOVE EXACT DUPLICATE ROWS ONLY
# ============================================================

def remove_exact_duplicates(df):

    duplicate_count = int(
        df.duplicated().sum()
    )

    cleaned_df = df.drop_duplicates().copy()

    return (
        cleaned_df,
        duplicate_count
    )


# ============================================================
# 8. CLEAN NUMERIC VALUES
# ============================================================

def clean_numeric_series(series):

    values = (
        series.astype("string")
        .str.strip()
        .str.replace(
            "₹",
            "",
            regex=False
        )
        .str.replace(
            "Rs.",
            "",
            regex=False
        )
        .str.replace(
            "Rs",
            "",
            regex=False
        )
        .str.replace(
            ",",
            "",
            regex=False
        )
        .str.strip()
    )

    return pd.to_numeric(
        values,
        errors="coerce"
    )


# ============================================================
# 9. IDENTIFY FINANCIAL / NUMERIC COLUMNS
# ============================================================

def is_numeric_column_name(column):

    column = column.lower()

    keywords = [
        "amount",
        "allocated",
        "disbursed",
        "expenditure",
        "fund",
        "consent"
    ]

    return any(
        keyword in column
        for keyword in keywords
    )


# ============================================================
# 10. CONVERT ONLY FINANCIAL COLUMNS
# ============================================================

def convert_financial_columns(df):

    df = df.copy()

    converted_columns = []

    for column in df.columns:

        if not is_numeric_column_name(
            column
        ):
            continue

        original = df[column]

        # Already numeric
        if pd.api.types.is_numeric_dtype(
            original
        ):

            continue

        converted = clean_numeric_series(
            original
        )

        original_non_missing = (
            original.notna().sum()
        )

        converted_non_missing = (
            converted.notna().sum()
        )

        if original_non_missing == 0:
            continue

        conversion_ratio = (
            converted_non_missing
            /
            original_non_missing
        )

        # Only convert if at least 80%
        # of non-missing values are numeric
        if conversion_ratio >= 0.80:

            df[column] = converted

            converted_columns.append(
                column
            )

    return df, converted_columns


# ============================================================
# 11. IDENTIFY DATE COLUMNS
# ============================================================

def is_date_column(column):

    column = column.lower()

    date_keywords = [
        "date",
        "recommended_date",
        "sanction_date",
        "completion_date",
        "expenditure_date",
        "consent_date"
    ]

    return any(
        keyword in column
        for keyword in date_keywords
    )


# ============================================================
# 12. SAFE DATE CONVERSION
#
# IMPORTANT:
# Invalid dates become missing values.
# ROWS ARE NEVER REMOVED.
# ============================================================

def convert_date_columns(df):

    df = df.copy()

    converted_columns = []

    for column in df.columns:

        if not is_date_column(
            column
        ):
            continue

        original = df[column]

        if pd.api.types.is_datetime64_any_dtype(
            original
        ):
            continue

        try:

            # First try common MPLADS date formats
            converted = pd.to_datetime(
                original,
                errors="coerce",
                dayfirst=True
            )

            # Only replace column if a reasonable
            # number of non-missing values parse
            original_non_missing = (
                original.notna().sum()
            )

            converted_non_missing = (
                converted.notna().sum()
            )

            if original_non_missing > 0:

                conversion_ratio = (
                    converted_non_missing
                    /
                    original_non_missing
                )

                if conversion_ratio >= 0.50:

                    df[column] = converted

                    converted_columns.append(
                        column
                    )

        except Exception as error:

            print(
                f"  Date conversion skipped "
                f"for {column}: {error}"
            )

    return df, converted_columns


# ============================================================
# 13. CREATE INVALID VALUE FLAGS
#
# FLAGS DO NOT DELETE ROWS.
# ============================================================

def create_invalid_flags(df):

    df = df.copy()

    flags_created = []

    for column in df.columns:

        column_lower = column.lower()

        # Financial negative value flag
        if is_numeric_column_name(
            column
        ):

            if pd.api.types.is_numeric_dtype(
                df[column]
            ):

                flag_column = (
                    f"{column}_invalid_negative"
                )

                df[flag_column] = (
                    df[column] < 0
                )

                flags_created.append(
                    flag_column
                )

    return df, flags_created


# ============================================================
# 14. ADD DATASET SOURCE COLUMN
#
# Useful later during integration.
# ============================================================

def add_source_column(df, dataset_name):

    df = df.copy()

    df["source_dataset"] = (
        dataset_name
    )

    return df


# ============================================================
# 15. CLEAN ONE DATASET
# ============================================================

def clean_dataset(file_path):

    print("\n" + "=" * 70)

    print(
        f"PROCESSING: {file_path.name}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # READ RAW DATA
    # --------------------------------------------------------

    df = read_csv_safely(
        file_path
    )

    original_rows = len(df)

    original_columns = len(
        df.columns
    )

    print(
        f"Original rows: {original_rows}"
    )

    print(
        f"Original columns: "
        f"{original_columns}"
    )

    # --------------------------------------------------------
    # STANDARDIZE COLUMN NAMES
    # --------------------------------------------------------

    df = standardize_column_names(
        df
    )

    # --------------------------------------------------------
    # CLEAN TEXT
    # --------------------------------------------------------

    df = clean_text_values(
        df
    )

    # --------------------------------------------------------
    # REMOVE COMPLETELY EMPTY ROWS
    # --------------------------------------------------------

    (
        df,
        empty_rows_removed
    ) = remove_completely_empty_rows(
        df
    )

    # --------------------------------------------------------
    # REMOVE GRAND TOTAL / SUMMARY ROWS
    # --------------------------------------------------------

    (
        df,
        summary_rows_removed
    ) = remove_summary_rows(
        df
    )

    print(
        f"Summary rows removed: "
        f"{summary_rows_removed}"
    )

    # --------------------------------------------------------
    # REMOVE EXACT DUPLICATES ONLY
    # --------------------------------------------------------

    (
        df,
        duplicate_rows_removed
    ) = remove_exact_duplicates(
        df
    )

    print(
        f"Exact duplicate rows removed: "
        f"{duplicate_rows_removed}"
    )

    # --------------------------------------------------------
    # CONVERT FINANCIAL COLUMNS
    # --------------------------------------------------------

    (
        df,
        numeric_columns_converted
    ) = convert_financial_columns(
        df
    )

    # --------------------------------------------------------
    # CONVERT DATE COLUMNS
    #
    # NO ROWS ARE DELETED HERE
    # --------------------------------------------------------

    (
        df,
        date_columns_converted
    ) = convert_date_columns(
        df
    )

    # --------------------------------------------------------
    # INVALID FLAGS
    #
    # NO ROWS ARE DELETED HERE
    # --------------------------------------------------------

    (
        df,
        invalid_flags_created
    ) = create_invalid_flags(
        df
    )

    # --------------------------------------------------------
    # ADD SOURCE DATASET
    # --------------------------------------------------------

    df = add_source_column(
        df,
        file_path.name
    )

    # --------------------------------------------------------
    # FINAL STATISTICS
    # --------------------------------------------------------

    final_rows = len(df)

    final_columns = len(
        df.columns
    )

    missing_values = int(
        df.isna().sum().sum()
    )

    # --------------------------------------------------------
    # SAVE CLEANED FILE
    # --------------------------------------------------------

    output_file = (
        CLEANED_DATA_DIR
        /
        f"cleaned_{file_path.stem}.csv"
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = {

        "dataset":
            file_path.name,

        "original_rows":
            original_rows,

        "original_columns":
            original_columns,

        "empty_rows_removed":
            empty_rows_removed,

        "summary_rows_removed":
            summary_rows_removed,

        "duplicate_rows_removed":
            duplicate_rows_removed,

        "rows_after_cleaning":
            final_rows,

        "columns_after_cleaning":
            final_columns,

        "numeric_columns_converted":
            len(
                numeric_columns_converted
            ),

        "date_columns_converted":
            len(
                date_columns_converted
            ),

        "invalid_flags_created":
            len(
                invalid_flags_created
            ),

        "missing_values_after_cleaning":
            missing_values,

        "output_file":
            str(output_file)

    }

    # --------------------------------------------------------
    # PRINT FINAL RESULT
    # --------------------------------------------------------

    print(
        f"\nFinal rows: {final_rows}"
    )

    print(
        f"Final columns: "
        f"{final_columns}"
    )

    print(
        f"Missing values remaining: "
        f"{missing_values}"
    )

    print(
        f"Numeric columns converted: "
        f"{len(numeric_columns_converted)}"
    )

    print(
        f"Date columns converted: "
        f"{len(date_columns_converted)}"
    )

    print(
        f"Saved to: {output_file}"
    )

    return summary


# ============================================================
# 16. MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)

    print(
        "MPLADS AI MONITORING SYSTEM"
    )

    print(
        "PHASE 3 - DATA CLEANING "
        "& STANDARDIZATION"
    )

    print("#" * 70)

    print(
        "\nIMPORTANT:"
    )

    print(
        "Raw files will NOT be modified."
    )

    print(
        f"\nRaw directory: "
        f"{RAW_DATA_DIR}"
    )

    print(
        f"Cleaned directory: "
        f"{CLEANED_DATA_DIR}"
    )

    # --------------------------------------------------------
    # CHECK RAW DIRECTORY
    # --------------------------------------------------------

    if not RAW_DATA_DIR.exists():

        print(
            "\nERROR: Raw data directory "
            "does not exist."
        )

        return

    # --------------------------------------------------------
    # FIND CSV FILES
    # --------------------------------------------------------

    csv_files = sorted(
        RAW_DATA_DIR.glob(
            "*.csv"
        )
    )

    if len(csv_files) == 0:

        print(
            "\nERROR: No CSV files found."
        )

        return

    print(
        f"\nDatasets found: "
        f"{len(csv_files)}"
    )

    # --------------------------------------------------------
    # CLEAN ALL DATASETS
    # --------------------------------------------------------

    summaries = []

    for file_path in csv_files:

        try:

            summary = clean_dataset(
                file_path
            )

            summaries.append(
                summary
            )

        except Exception as error:

            print("\n" + "!" * 70)

            print(
                f"ERROR PROCESSING: "
                f"{file_path.name}"
            )

            print(
                f"ERROR: {error}"
            )

            print("!" * 70)

    # --------------------------------------------------------
    # SAVE CLEANING SUMMARY
    # --------------------------------------------------------

    if len(summaries) == 0:

        print(
            "\nNo datasets were cleaned."
        )

        return

    summary_df = pd.DataFrame(
        summaries
    )

    summary_file = (
        REPORTS_DIR
        /
        "cleaning_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # DISPLAY SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    print(
        "CLEANING SUMMARY"
    )

    print("=" * 70)

    print(
        summary_df[
            [
                "dataset",
                "original_rows",
                "summary_rows_removed",
                "duplicate_rows_removed",
                "rows_after_cleaning",
                "missing_values_after_cleaning"
            ]
        ].to_string(
            index=False
        )
    )

    print(
        f"\nSummary saved to: "
        f"{summary_file}"
    )

    print("\n" + "=" * 70)

    print(
        "PHASE 3 CLEANING COMPLETE"
    )

    print("=" * 70)

    print(
        "\nIMPORTANT:"
    )

    print("Only summary rows, completely empty "
        "rows and exact duplicates were removed."
    )

    print(
        "Rows with missing values or invalid "
        "dates were preserved."
    )

    print(
        "\nYou can now verify row counts."
    )


# ============================================================
# 17. RUN
# ============================================================

if __name__ == "__main__":

    main()
         