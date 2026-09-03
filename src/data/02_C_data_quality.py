import os
import sys
import pandas as pd
import numpy as np

# ============================================================
# MPLADS INSIGHT AI
# PHASE 2 - DATA QUALITY & INTEGRITY CHECK
# ============================================================

# ------------------------------------------------------------
# 1. WINDOWS UTF-8 SUPPORT
# ------------------------------------------------------------

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ------------------------------------------------------------
# 2. PROJECT PATHS
# ------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "data_quality")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------------------------------------
# 3. DATASET CONFIGURATION
# ------------------------------------------------------------

DATASETS = {
    "Allocated_Limit.csv": {
        "numeric": [
            "allocated_amount"
        ],
        "dates": [],
        "text": [
            "state",
            "honble_members_of_parliaments",
            "constituency"
        ]
    },

    "Completed_On-going_Works.csv": {
        "numeric": [
            "fund_disbursed_amount"
        ],
        "dates": [
            "expenditure_date"
        ],
        "text": [
            "state",
            "work",
            "work_id",
            "ida",
            "honble_members_of_parliament",
            "constituency",
            "vendor_name",
            "payment_status"
        ]
    },

    "consented_Calamity.csv": {
        "numeric": [
            "consent_amount"
        ],
        "dates": [
            "date_of_consent"
        ],
        "text": [
            "calamity_type",
            "calamity_name",
            "honble_members_of_parliament"
        ]
    },

    "Works Completed.csv": {
        "numeric": [
            "amount_disbursed"
        ],
        "dates": [
            "completion_date"
        ],
        "text": [
            "work_category",
            "work",
            "state",
            "ida",
            "work_description",
            "honble_members_of_parliament",
            "constituency"
        ]
    },

    "Works Sanctioned.csv": {
        "numeric": [
            "sanction_amount"
        ],
        "dates": [
            "recommended_date",
            "sanction_date"
        ],
        "text": [
            "work_category",
            "work",
            "state",
            "ida",
            "work_description",
            "honble_members_of_parliament",
            "constituency",
            "work_status"
        ]
    },

    "Works_Recommended.csv": {
        "numeric": [
            "recommended_amount"
        ],
        "dates": [
            "recommended_date",
            "sanction_date"
        ],
        "text": [
            "work_category",
            "work",
            "state",
            "ida",
            "work_description",
            "honble_members_of_parliament",
            "elected_nominated"
        ]
    }
}


# ------------------------------------------------------------
# 4. HELPER FUNCTION
# ------------------------------------------------------------

def is_blank(value):
    """
    Returns True when a value is empty, NaN,
    or contains only whitespace.
    """

    if pd.isna(value):
        return True

    if isinstance(value, str):
        return value.strip() == ""

    return False


# ------------------------------------------------------------
# 5. ADD ISSUE
# ------------------------------------------------------------

issues = []
quarantine_rows = []


def add_issue(
    dataset,
    row_number,
    field,
    defect_class,
    original_value
):
    issues.append({
        "dataset": dataset,
        "row_number": row_number,
        "field": field,
        "defect_class": defect_class,
        "original_value": original_value
    })


# ------------------------------------------------------------
# 6. READ CSV SAFELY
# ------------------------------------------------------------

def read_csv_safely(filepath):

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin1"
    ]

    for encoding in encodings:

        try:
            return pd.read_csv(
                filepath,
                encoding=encoding,
                low_memory=False
            )

        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Could not read CSV using supported encodings."
    )


# ------------------------------------------------------------
# 7. PROCESS EACH DATASET
# ------------------------------------------------------------

print()
print("==============================================")
print("MPLADS INSIGHT AI")
print("PHASE 2 - DATA QUALITY & INTEGRITY CHECK")
print("==============================================")
print()

all_files = [
    file for file in os.listdir(RAW_DIR)
    if file.lower().endswith(".csv")
]

print("Datasets found:", len(all_files))
print()


for filename in all_files:

    if filename not in DATASETS:
        print("Skipping unknown dataset:", filename)
        continue

    filepath = os.path.join(RAW_DIR, filename)

    print("----------------------------------------------")
    print("Checking:", filename)
    print("----------------------------------------------")

    try:
        df = read_csv_safely(filepath)

    except Exception as e:

        print("ERROR reading dataset:", str(e))
        continue

    config = DATASETS[filename]

    dataset_issue_count = 0

    # --------------------------------------------------------
    # A. MISSING / BLANK VALUES
    # --------------------------------------------------------

    for column in df.columns:

        for index, value in df[column].items():

            if is_blank(value):

                add_issue(
                    filename,
                    index + 2,
                    column,
                    "MISSING_OR_BLANK",
                    value
                )

                dataset_issue_count += 1


    # --------------------------------------------------------
    # B. NUMERIC VALIDATION
    # --------------------------------------------------------

    for column in config["numeric"]:

        if column not in df.columns:
            continue

        numeric_series = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        for index, original_value in df[column].items():

            # Ignore missing values here because
            # they were already captured above.
            if is_blank(original_value):
                continue

            converted_value = numeric_series.loc[index]

            # Non-numeric value
            if pd.isna(converted_value):

                add_issue(
                    filename,
                    index + 2,
                    column,
                    "INVALID_NUMERIC_VALUE",
                    original_value
                )

                dataset_issue_count += 1

                continue

            # Negative financial value
            if converted_value < 0:

                add_issue(
                    filename,
                    index + 2,
                    column,
                    "NEGATIVE_FINANCIAL_VALUE",
                    original_value
                )

                dataset_issue_count += 1


    # --------------------------------------------------------
    # C. DATE VALIDATION
    # --------------------------------------------------------

    for column in config["dates"]:

        if column not in df.columns:
            continue

        parsed_dates = pd.to_datetime(
            df[column],
            errors="coerce",
            dayfirst=True
        )

        for index, original_value in df[column].items():

            if is_blank(original_value):
                continue

            parsed_value = parsed_dates.loc[index]

            if pd.isna(parsed_value):

                add_issue(
                    filename,
                    index + 2,
                    column,
                    "INVALID_DATE",
                    original_value
                )

                dataset_issue_count += 1


    # --------------------------------------------------------
    # D. EXACT DUPLICATE RECORDS
    # --------------------------------------------------------

    duplicate_mask = df.duplicated(
        keep=False
    )

    duplicate_indices = df.index[duplicate_mask]

    for index in duplicate_indices:

        add_issue(
            filename,
            index + 2,
            "ROW",
            "EXACT_DUPLICATE_RECORD",
            "Duplicate row"
        )

        dataset_issue_count += 1


    # --------------------------------------------------------
    # E. WORK ID CHECK
    # --------------------------------------------------------

    if filename == "Completed_On-going_Works.csv":

        if "work_id" in df.columns:

            non_blank_work_id = df["work_id"].astype(str).str.strip()

            duplicate_work_ids = (
                non_blank_work_id[
                    non_blank_work_id != ""
                ]
                .duplicated(keep=False)
            )

            for index in df.index[duplicate_work_ids]:

                add_issue(
                    filename,
                    index + 2,
                    "work_id",
                    "DUPLICATE_WORK_ID",
                    df.loc[index, "work_id"]
                )

                dataset_issue_count += 1


    # --------------------------------------------------------
    # F. DATE LOGIC - WORKS SANCTIONED
    # --------------------------------------------------------

    if filename == "Works Sanctioned.csv":

        if (
            "recommended_date" in df.columns
            and
            "sanction_date" in df.columns
        ):

            recommended = pd.to_datetime(
                df["recommended_date"],
                errors="coerce",
                dayfirst=True
            )

            sanctioned = pd.to_datetime(
                df["sanction_date"],
                errors="coerce",
                dayfirst=True
            )

            invalid_order = (
                recommended.notna()
                &
                sanctioned.notna()
                &
                (recommended > sanctioned)
            )

            for index in df.index[invalid_order]:

                add_issue(
                    filename,
                    index + 2,
                    "recommended_date",
                    "DATE_ORDER_VIOLATION",
                    df.loc[index, "recommended_date"]
                )

                dataset_issue_count += 1


    # --------------------------------------------------------
    # G. DATE LOGIC - WORKS RECOMMENDED
    # --------------------------------------------------------

    if filename == "Works_Recommended.csv":

        if (
            "recommended_date" in df.columns
            and
            "sanction_date" in df.columns
        ):

            recommended = pd.to_datetime(
                df["recommended_date"],
                errors="coerce",
                dayfirst=True
            )

            sanctioned = pd.to_datetime(
                df["sanction_date"],
                errors="coerce",
                dayfirst=True
            )

            invalid_order = (
                recommended.notna()
                &
                sanctioned.notna()
                &
                (recommended > sanctioned)
            )

            for index in df.index[invalid_order]:

                add_issue(
                    filename,
                    index + 2,
                    "recommended_date",
                    "DATE_ORDER_VIOLATION",
                    df.loc[index, "recommended_date"]
                )

                dataset_issue_count += 1


    # --------------------------------------------------------
    # H. CREATE QUARANTINE RECORDS
    # --------------------------------------------------------

    dataset_issue_rows = [
        issue for issue in issues
        if issue["dataset"] == filename
    ]

    issue_row_numbers = set(
        issue["row_number"]
        for issue in dataset_issue_rows
    )

    for row_number in sorted(issue_row_numbers):

        original_index = row_number - 2

        if original_index < 0:
            continue

        if original_index >= len(df):
            continue

        row = df.iloc[original_index].copy()

        row_dict = row.to_dict()

        row_dict["dataset"] = filename
        row_dict["row_number"] = row_number

        row_issues = [
            issue["defect_class"]
            for issue in dataset_issue_rows
            if issue["row_number"] == row_number
        ]

        row_dict["quality_issues"] = "; ".join(
            sorted(set(row_issues))
        )

        quarantine_rows.append(row_dict)


    print("Rows checked:", len(df))
    print("Issues found:", dataset_issue_count)
    print()


# ------------------------------------------------------------
# 8. SAVE QUALITY ISSUES
# ------------------------------------------------------------

issues_df = pd.DataFrame(
    issues,
    columns=[
        "dataset",
        "row_number",
        "field",
        "defect_class",
        "original_value"
    ]
)

quality_issues_path = os.path.join(
    OUTPUT_DIR,
    "quality_issues.csv"
)

issues_df.to_csv(
    quality_issues_path,
    index=False,
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# 9. SAVE QUARANTINE RECORDS
# ------------------------------------------------------------

if quarantine_rows:

    quarantine_df = pd.DataFrame(
        quarantine_rows
    )

else:

    quarantine_df = pd.DataFrame(
        columns=["dataset", "row_number", "quality_issues"]
    )


quarantine_path = os.path.join(
    OUTPUT_DIR,
    "quarantine_records.csv"
)

quarantine_df.to_csv(
    quarantine_path,
    index=False,
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# 10. FINAL SUMMARY
# ------------------------------------------------------------

print("==============================================")
print("PHASE 2 COMPLETE")
print("==============================================")
print()

print("Total quality issues:", len(issues_df))
print("Quarantined rows:", len(quarantine_df))
print()

print("Created:")
print(quality_issues_path)
print(quarantine_path)

print()
print("Existing Phase 1A data_quality_summary.csv")
print("was NOT modified.")

print()
print("Next phase: Phase 3 - Canonicalization + Cleaning")
print()