# ======================================================================
# MPLADS AI MONITORING SYSTEM
# PHASE 4 - DATA INTEGRATION
# ======================================================================
#
# PURPOSE
# -------
# 1. Integrate only the 4 work-related datasets:
#       - Works Recommended
#       - Works Sanctioned
#       - Works Completed
#       - Completed / On-going Works
#
# 2. Create:
#       - work_master.csv
#       - allocation_master.csv
#       - calamity_master.csv
#       - integration_summary.csv
#
# IMPORTANT
# ---------
# - Raw files are NOT modified.
# - Cleaned files are NOT modified.
# - Allocation and calamity datasets are NOT merged with work_master.
# - Lifecycle flags are created AFTER work consolidation.
# ======================================================================


from pathlib import Path
import hashlib
import re

import pandas as pd


# ======================================================================
# 1. PROJECT PATHS
# ======================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLEANED_DATA_DIR = (
    PROJECT_ROOT
    / "src"
    / "data"
    / "cleaned"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "integration"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ======================================================================
# 2. REQUIRED FILES
# ======================================================================

REQUIRED_FILES = {

    "allocation":
        "cleaned_Allocated_Limit.csv",

    "ongoing":
        "cleaned_Completed_On-going_Works.csv",

    "calamity":
        "cleaned_consented_Calamity.csv",

    "completed":
        "cleaned_Works Completed.csv",

    "sanctioned":
        "cleaned_Works Sanctioned.csv",

    "recommended":
        "cleaned_Works_Recommended.csv"
}


# ======================================================================
# 3. DISPLAY HELPER
# ======================================================================

def print_line(character="=", length=70):

    print(character * length)


# ======================================================================
# 4. SAFE CSV READER
# ======================================================================

def read_csv_safely(file_path):

    encodings = [
        "utf-8-sig",
        "utf-8",
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

            return df

        except Exception as error:

            last_error = error

    raise ValueError(
        f"Could not read {file_path.name}. "
        f"Last error: {last_error}"
    )


# ======================================================================
# 5. LOAD DATASETS
# ======================================================================

def load_dataset(dataset_name, file_name):

    file_path = (
        CLEANED_DATA_DIR
        / file_name
    )

    print(
        f"\nReading: {file_name}"
    )

    df = read_csv_safely(
        file_path
    )

    print(
        f"Rows    : {len(df):,}"
    )

    print(
        f"Columns : {len(df.columns)}"
    )

    return df


# ======================================================================
# 6. NORMALIZE TEXT
# ======================================================================

def normalize_text(value):

    if pd.isna(value):

        return pd.NA

    value = str(value)

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    value = value.lower()

    return value


# ======================================================================
# 7. NORMALIZE TEXT COLUMN
# ======================================================================

def normalize_text_column(series):

    return (
        series
        .astype("string")
        .apply(normalize_text)
    )


# ======================================================================
# 8. FIND FIRST EXISTING COLUMN
# ======================================================================

def first_existing_column(
    df,
    possible_columns
):

    for column in possible_columns:

        if column in df.columns:

            return column

    return None


# ======================================================================
# 9. CREATE SAFE DATE
# ======================================================================

def parse_date(series):

    values = (
        series
        .astype("string")
        .str.strip()
    )

    # Try ISO format first.
    result = pd.to_datetime(
        values,
        errors="coerce",
        format="mixed"
    )

    return result


# ======================================================================
# 10. CLEAN NUMERIC COLUMN
# ======================================================================

def clean_numeric(series):

    values = (
        series
        .astype("string")
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


# ======================================================================
# 11. CREATE WORK KEY
# ======================================================================

def create_work_key(
    df,
    stage_name
):

    df = df.copy()

    # --------------------------------------------------------------
    # BEST CASE:
    # Dataset has original work_id
    # --------------------------------------------------------------

    if "work_id" in df.columns:

        work_id = (
            df["work_id"]
            .astype("string")
            .str.strip()
        )

        valid_work_id = (
            work_id.notna()
            &
            (work_id != "")
        )

        df["work_key"] = pd.NA

        df.loc[
            valid_work_id,
            "work_key"
        ] = (
            "WID_"
            +
            work_id.loc[
                valid_work_id
            ].astype(str)
        )

    else:

        df["work_key"] = pd.NA

    # --------------------------------------------------------------
    # FALLBACK KEY
    #
    # Uses stable descriptive fields.
    # This is required because some datasets do not contain work_id.
    # --------------------------------------------------------------

    missing_key = (
        df["work_key"].isna()
        |
        (
            df["work_key"]
            .astype("string")
            .str.strip()
            == ""
        )
    )

    if missing_key.any():

        key_columns = []

        for column in [
            "work",
            "work_description",
            "state",
            "constituency",
            "ida",
            "work_category"
        ]:

            if column in df.columns:

                key_columns.append(
                    column
                )

        if len(key_columns) == 0:

            key_source = (
                pd.Series(
                    index=df.index,
                    dtype="string"
                )
            )

        else:

            key_source = (
                df[key_columns]
                .astype("string")
                .fillna("")
                .apply(
                    lambda row:
                    "|".join(
                        normalize_text(value)
                        if pd.notna(value)
                        else ""
                        for value in row
                    ),
                    axis=1
                )
            )

        # Add stage-independent stable hash
        fallback_keys = key_source.apply(
            lambda value:
            "WH_"
            +
            hashlib.sha1(
                str(value).encode(
                    "utf-8"
                )
            ).hexdigest()[:20]
        )

        df.loc[
            missing_key,
            "work_key"
        ] = fallback_keys.loc[
            missing_key
        ]

    return df


# ======================================================================
# 12. ADD MISSING COLUMN
# ======================================================================

def ensure_column(
    df,
    column,
    default_value=pd.NA
):

    if column not in df.columns:

        df[column] = default_value

    return df


# ======================================================================
# 13. PREPARE RECOMMENDED WORKS
# ======================================================================

def prepare_recommended(df):

    print(
        "Preparing Recommended Works..."
    )

    df = df.copy()

    df = create_work_key(
        df,
        "Recommended"
    )

    df["source_recommended"] = 1
    df["source_sanctioned"] = 0
    df["source_completed"] = 0
    df["source_ongoing"] = 0

    return df


# ======================================================================
# 14. PREPARE SANCTIONED WORKS
# ======================================================================

def prepare_sanctioned(df):

    print(
        "Preparing Sanctioned Works..."
    )

    df = df.copy()

    df = create_work_key(
        df,
        "Sanctioned"
    )

    df["source_recommended"] = 0
    df["source_sanctioned"] = 1
    df["source_completed"] = 0
    df["source_ongoing"] = 0

    return df


# ======================================================================
# 15. PREPARE COMPLETED WORKS
# ======================================================================

def prepare_completed(df):

    print(
        "Preparing Completed Works..."
    )

    df = df.copy()

    df = create_work_key(
        df,
        "Completed"
    )

    df["source_recommended"] = 0
    df["source_sanctioned"] = 0
    df["source_completed"] = 1
    df["source_ongoing"] = 0

    return df


# ======================================================================
# 16. PREPARE ONGOING WORKS
# ======================================================================

def prepare_ongoing(df):

    print(
        "Preparing Completed/On-going Works..."
    )

    df = df.copy()

    # --------------------------------------------------------------
    # This dataset may contain work_id.
    # --------------------------------------------------------------

    df = create_work_key(
        df,
        "Ongoing"
    )

    # --------------------------------------------------------------
    # If "work" is actually an ID and work_id is missing,
    # use it as work_id.
    # --------------------------------------------------------------

    if "work_id" not in df.columns:

        df["work_id"] = pd.NA

    if "work" in df.columns:

        work_as_id = (
            df["work"]
            .astype("string")
            .str.strip()
        )

        missing_work_id = (
            df["work_id"].isna()
            |
            (
                df["work_id"]
                .astype("string")
                .str.strip()
                == ""
            )
        )

        # Only use values that look like actual MPLADS work IDs.
        looks_like_work_id = (
            work_as_id
            .str.contains(
                r"/",
                regex=True,
                na=False
            )
        )

        fill_mask = (
            missing_work_id
            &
            looks_like_work_id
        )

        df.loc[
            fill_mask,
            "work_id"
        ] = (
            work_as_id.loc[
                fill_mask
            ].astype("string")
        )

        # Update key using recovered work_id.
        if fill_mask.any():

            df.loc[
                fill_mask,
                "work_key"
            ] = (
                "WID_"
                +
                df.loc[
                    fill_mask,
                    "work_id"
                ].astype(str)
            )

    df["source_recommended"] = 0
    df["source_sanctioned"] = 0
    df["source_completed"] = 0
    df["source_ongoing"] = 1

    return df


# ======================================================================
# 17. NORMALIZE LIFECYCLE COLUMNS
# ======================================================================

MASTER_COLUMNS = [

    "work_key",

    "work_id",

    "work",

    "state",

    "constituency",

    "ida",

    "work_category",

    "work_description",

    "honble_members_of_parliament",

    "recommended_date",

    "sanction_date",

    "completion_date",

    "recommended_amount",

    "sanction_amount",

    "amount_disbursed",

    "fund_disbursed_amount",

    "work_status",

    "payment_status",

    "vendor_name",

    "source_recommended",

    "source_sanctioned",

    "source_completed",

    "source_ongoing"
]


def standardize_lifecycle_columns(df):

    df = df.copy()

    # --------------------------------------------------------------
    # Possible alternate column names
    # --------------------------------------------------------------

    rename_map = {

        "description":
            "work_description",

        "completiondate":
            "completion_date",

        "completed_date":
            "completion_date",

        "recommendedamount":
            "recommended_amount",

        "sanctionamount":
            "sanction_amount",

        "amountdisbursed":
            "amount_disbursed",

        "funddisbursedamount":
            "fund_disbursed_amount",

        "vendor":
            "vendor_name",

        "paymentstatus":
            "payment_status",

        "workstatus":
            "work_status"
    }

    for old_column, new_column in rename_map.items():

        if (
            old_column in df.columns
            and
            new_column not in df.columns
        ):

            df = df.rename(
                columns={
                    old_column:
                    new_column
                }
            )

    # --------------------------------------------------------------
    # Ensure every required column exists
    # --------------------------------------------------------------

    for column in MASTER_COLUMNS:

        df = ensure_column(
            df,
            column
        )

    # --------------------------------------------------------------
    # Select only required columns
    # --------------------------------------------------------------

    df = df[
        MASTER_COLUMNS
    ].copy()

    return df


# ======================================================================
# 18. FIRST NON-NULL VALUE
# ======================================================================

def first_valid(series):

    values = series.dropna()

    if len(values) == 0:

        return pd.NA

    for value in values:

        if isinstance(value, str):

            if value.strip() != "":

                return value

        else:

            return value

    return pd.NA


# ======================================================================
# 19. MAX DATE
# ======================================================================

def latest_date(series):

    dates = pd.to_datetime(
        series,
        errors="coerce",
        format="mixed"
    )

    dates = dates.dropna()

    if len(dates) == 0:

        return pd.NaT

    return dates.max()


# ======================================================================
# 20. CONSOLIDATE WORK RECORDS
# ======================================================================

def consolidate_work_records(lifecycle):

    print(
        "Consolidating records by work_key..."
    )

    # IMPORTANT:
    # At this stage lifecycle status columns DO NOT EXIST.
    # Only actual source columns are aggregated here.

    text_columns = [

        "work_id",

        "work",

        "state",

        "constituency",

        "ida",

        "work_category",

        "work_description",

        "honble_members_of_parliament",

        "work_status",

        "payment_status",

        "vendor_name"
    ]

    numeric_columns = [

        "recommended_amount",

        "sanction_amount",

        "amount_disbursed",

        "fund_disbursed_amount"
    ]

    flag_columns = [

        "source_recommended",

        "source_sanctioned",

        "source_completed",

        "source_ongoing"
    ]

    aggregation = {}

    # --------------------------------------------------------------
    # Text: first meaningful value
    # --------------------------------------------------------------

    for column in text_columns:

        aggregation[column] = first_valid

    # --------------------------------------------------------------
    # Dates: latest available date
    # --------------------------------------------------------------

    aggregation[
        "recommended_date"
    ] = latest_date

    aggregation[
        "sanction_date"
    ] = latest_date

    aggregation[
        "completion_date"
    ] = latest_date

    # --------------------------------------------------------------
    # Numeric values: first non-null value
    #
    # We do NOT sum here because repeated lifecycle records could
    # represent the same work.
    # --------------------------------------------------------------

    for column in numeric_columns:

        aggregation[column] = first_valid

    # --------------------------------------------------------------
    # Source flags: maximum
    # --------------------------------------------------------------

    for column in flag_columns:

        aggregation[column] = "max"

    work_master = (

        lifecycle
        .groupby(
            "work_key",
            dropna=False,
            as_index=False
        )
        .agg(
            aggregation
        )
    )

    return work_master


# ======================================================================
# 21. CREATE LIFECYCLE FLAGS
# ======================================================================

def create_lifecycle_features(work_master):

    print(
        "Determining current work stage..."
    )

    work_master = (
        work_master.copy()
    )

    # --------------------------------------------------------------
    # Source flags
    # --------------------------------------------------------------

    work_master[
        "has_recommended"
    ] = (
        work_master[
            "source_recommended"
        ]
        .fillna(0)
        .astype(int)
    )

    work_master[
        "has_sanctioned"
    ] = (
        work_master[
            "source_sanctioned"
        ]
        .fillna(0)
        .astype(int)
    )

    work_master[
        "has_completed"
    ] = (
        work_master[
            "source_completed"
        ]
        .fillna(0)
        .astype(int)
    )

    work_master[
        "has_ongoing"
    ] = (
        work_master[
            "source_ongoing"
        ]
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------------------
    # Current Stage
    #
    # Priority:
    # Completed > Ongoing > Sanctioned > Recommended
    # --------------------------------------------------------------

    conditions = [

        work_master[
            "has_completed"
        ] == 1,

        work_master[
            "has_ongoing"
        ] == 1,

        work_master[
            "has_sanctioned"
        ] == 1,

        work_master[
            "has_recommended"
        ] == 1
    ]

    choices = [

        "Completed",

        "Ongoing",

        "Sanctioned",

        "Recommended"
    ]

    work_master[
        "current_stage"
    ] = pd.NA
    for condition, stage in zip(
        conditions,
        choices
    ):

        work_master.loc[
            condition,
            "current_stage"
        ] = stage

    # --------------------------------------------------------------
    # Lifecycle Status
    # --------------------------------------------------------------

    work_master[
        "lifecycle_status"
    ] = "Unknown"

    # Complete lifecycle
    complete_lifecycle = (

        (
            work_master[
                "has_recommended"
            ] == 1
        )

        &

        (
            work_master[
                "has_sanctioned"
            ] == 1
        )

        &

        (
            work_master[
                "has_completed"
            ] == 1
        )
    )

    work_master.loc[
        complete_lifecycle,
        "lifecycle_status"
    ] = "Complete_Lifecycle"

    # Recommended only
    recommended_only = (

        (
            work_master[
                "has_recommended"
            ] == 1
        )

        &

        (
            work_master[
                "has_sanctioned"
            ] == 0
        )

        &

        (
            work_master[
                "has_completed"
            ] == 0
        )

        &

        (
            work_master[
                "has_ongoing"
            ] == 0
        )
    )

    work_master.loc[
        recommended_only,
        "lifecycle_status"
    ] = "Recommended_Only"

    # Sanctioned but not completed
    sanctioned_not_completed = (

        (
            work_master[
                "has_sanctioned"
            ] == 1
        )

        &

        (
            work_master[
                "has_completed"
            ] == 0
        )

        &

        (
            work_master[
                "has_ongoing"
            ] == 0
        )
    )

    work_master.loc[
        sanctioned_not_completed,
        "lifecycle_status"
    ] = "Sanctioned_But_Not_Completed"

    # Ongoing
    ongoing_status = (

        work_master[
            "has_ongoing"
        ] == 1
    )

    work_master.loc[
        ongoing_status,
        "lifecycle_status"
    ] = "Ongoing"

    # Completed only / completed stage
    completed_status = (

        (
            work_master[
                "has_completed"
            ] == 1
        )

        &

        (
            work_master[
                "lifecycle_status"
            ] == "Unknown"
        )
    )

    work_master.loc[
        completed_status,
        "lifecycle_status"
    ] = "Completed_Without_Full_History"

    return work_master


# ======================================================================
# 22. PREPARE ALLOCATION MASTER
# ======================================================================

def prepare_allocation_master(df):

    print(
        "Preparing allocation master..."
    )

    allocation = df.copy()

    allocation_columns = [

        "state",

        "constituency",

        "honble_members_of_parliaments",

        "allocated_amount"
    ]

    # Keep existing columns only.
    existing_columns = [

        column
        for column in allocation_columns
        if column in allocation.columns
    ]

    allocation = allocation[
        existing_columns
    ].copy()

    # --------------------------------------------------------------
    # Rename MP column
    # --------------------------------------------------------------

    if (
        "honble_members_of_parliaments"
        in allocation.columns
    ):

        allocation = allocation.rename(
            columns={
                "honble_members_of_parliaments":
                "honble_members_of_parliament"
            }
        )

    # --------------------------------------------------------------
    # Numeric amount
    # --------------------------------------------------------------

    if (
        "allocated_amount"
        in allocation.columns
    ):

        allocation[
            "allocated_amount"
        ] = clean_numeric(
            allocation[
                "allocated_amount"
            ]
        )

    # --------------------------------------------------------------
    # Create allocation ID
    # --------------------------------------------------------------

    key_source = (

        allocation
        .astype("string")
        .fillna("")
        .apply(
            lambda row:
            "|".join(
                row.astype(str)
            ),
            axis=1
        )
    )

    allocation.insert(
        0,
        "allocation_id",
        key_source.apply(
            lambda value:
            "ALLOC_"
            +
            hashlib.sha1(
                str(value).encode(
                    "utf-8"
                )
            ).hexdigest()[:20]
        )
    )

    return allocation


# ======================================================================
# 23. PREPARE CALAMITY MASTER
# ======================================================================

def prepare_calamity_master(df):

    print(
        "Preparing calamity master..."
    )

    calamity = df.copy()

    # --------------------------------------------------------------
    # Remove technical cleaning flags
    # --------------------------------------------------------------

    keep_columns = []

    for column in calamity.columns:

        if (
            "invalid_negative"
            not in column
        ):

            keep_columns.append(
                column
            )

    calamity = calamity[
        keep_columns
    ].copy()

    # --------------------------------------------------------------
    # Clean amount
    # --------------------------------------------------------------

    if (
        "consent_amount"
        in calamity.columns
    ):

        calamity[
            "consent_amount"
        ] = clean_numeric(
            calamity[
                "consent_amount"
            ]
        )

    # --------------------------------------------------------------
    # Create calamity ID
    # --------------------------------------------------------------

    key_source = (

        calamity
        .astype("string")
        .fillna("")
        .apply(
            lambda row:
            "|".join(
                row.astype(str)
            ),
            axis=1
        )
    )

    calamity.insert(
        0,
        "calamity_id",
        key_source.apply(
            lambda value:
            "CAL_"
            +
            hashlib.sha1(
                str(value).encode(
                    "utf-8"
                )
            ).hexdigest()[:20]
        )
    )

    return calamity


# ======================================================================
# 24. SORT WORK MASTER
# ======================================================================

def sort_work_master(work_master):

    sort_columns = []

    if "current_stage" in work_master.columns:

        stage_order = {

            "Completed": 1,

            "Ongoing": 2,

            "Sanctioned": 3,

            "Recommended": 4
        }

        work_master[
            "_stage_order"
        ] = (
            work_master[
                "current_stage"
            ]
            .map(
                stage_order
            )
            .fillna(99)
        )

        sort_columns.append(
            "_stage_order"
        )

    sort_columns.append(
        "work_key"
    )

    work_master = (

        work_master
        .sort_values(
            sort_columns
        )
        .drop(
            columns=[
                "_stage_order"
            ],
            errors="ignore"
        )
        .reset_index(
            drop=True
        )
    )

    return work_master


# ======================================================================
# 25. CREATE INTEGRATION SUMMARY
# ======================================================================

def create_integration_summary(

    allocation,

    ongoing,

    calamity,

    completed,

    sanctioned,

    recommended,

    work_master,

    allocation_master,

    calamity_master
):

    summary_rows = []

    # --------------------------------------------------------------
    # Source datasets
    # --------------------------------------------------------------

    source_datasets = [

        (
            "Allocated_Limit",
            allocation,
            "Allocation dataset"
        ),

        (
            "Completed_On-going_Works",
            ongoing,
            "Ongoing expenditure dataset"
        ),

        (
            "consented_Calamity",
            calamity,
            "Calamity consent dataset"
        ),

        (
            "Works Completed",
            completed,
            "Completed works dataset"
        ),

        (
            "Works Sanctioned",
            sanctioned,
            "Sanctioned works dataset"
        ),

        (
            "Works Recommended",
            recommended,
            "Recommended works dataset"
        )
    ]

    for dataset_name, df, notes in source_datasets:

        unique_keys = ""

        if "work_key" in df.columns:

            unique_keys = int(
                df[
                    "work_key"
                ].nunique()
            )

        summary_rows.append({

            "section":
                "source_dataset",

            "dataset":
                dataset_name,

            "rows":
                len(df),

            "columns":
                len(df.columns),

            "unique_work_keys":
                unique_keys,

            "notes":
                notes
        })

    # --------------------------------------------------------------
    # Integrated masters
    # --------------------------------------------------------------

    summary_rows.append({

        "section":
            "integrated_master",

        "dataset":
            "work_master",

        "rows":
            len(work_master),

        "columns":
            len(work_master.columns),

        "unique_work_keys":
            int(
                work_master[
                    "work_key"
                ].nunique()
            ),

        "notes":
            "Consolidated work lifecycle master"
    })

    summary_rows.append({

        "section":
            "integrated_master",

        "dataset":
            "allocation_master",

        "rows":
            len(allocation_master),

        "columns":
            len(allocation_master.columns),

        "unique_work_keys":
            "",

        "notes":
            "Allocation master"
    })

    summary_rows.append({

        "section":
            "integrated_master",

        "dataset":
            "calamity_master",

        "rows":
            len(calamity_master),

        "columns":
            len(calamity_master.columns),

        "unique_work_keys":
            "",

        "notes":
            "Calamity master"
    })

    # --------------------------------------------------------------
    # Current stage counts
    # --------------------------------------------------------------

    stage_counts = (

        work_master[
            "current_stage"
        ]
        .value_counts(
            dropna=False
        )
    )

    for stage, count in stage_counts.items():

        summary_rows.append({

            "section":
                "current_stage",

            "dataset":
                stage,

            "rows":
                int(count),

            "columns":
                "",

            "unique_work_keys":
                "",

            "notes":
                "Current lifecycle stage"
        })

    # --------------------------------------------------------------
    # Lifecycle status
    # --------------------------------------------------------------

    status_counts = (

        work_master[
            "lifecycle_status"
        ]
        .value_counts(
            dropna=False
        )
    )

    for status, count in status_counts.items():

        summary_rows.append({

            "section":
                "lifecycle_status",

            "dataset":
                status,

            "rows":
                int(count),

            "columns":
                "",

            "unique_work_keys":
                "",

            "notes":
                "Lifecycle integration status"
        })

    return pd.DataFrame(
        summary_rows
    )


# ======================================================================
# 26. SAVE OUTPUTS
# ======================================================================

def save_outputs(

    work_master,

    allocation_master,

    calamity_master,

    integration_summary
):

    work_master_file = (
        OUTPUT_DIR
        / "work_master.csv"
    )

    allocation_master_file = (
        OUTPUT_DIR
        / "allocation_master.csv"
    )

    calamity_master_file = (
        OUTPUT_DIR
        / "calamity_master.csv"
    )

    summary_file = (
        OUTPUT_DIR
        / "integration_summary.csv"
    )

    work_master.to_csv(
        work_master_file,
        index=False,
        encoding="utf-8-sig"
    )

    allocation_master.to_csv(
        allocation_master_file,
        index=False,
        encoding="utf-8-sig"
    )

    calamity_master.to_csv(
        calamity_master_file,
        index=False,
        encoding="utf-8-sig"
    )

    integration_summary.to_csv(
        summary_file,
        index=False,
        encoding="utf-8-sig"
    )

    return (

        work_master_file,

        allocation_master_file,

        calamity_master_file,

        summary_file
    )


# ======================================================================
# 27. MAIN
# ======================================================================

def main():

    print("\n")

    print_line()

    print(
        "PHASE 4 - DATA INTEGRATION"
    )

    print_line()

    print(
        "\nProject root:"
    )

    print(
        PROJECT_ROOT
    )

    print(
        "\nCleaned data directory:"
    )

    print(
        CLEANED_DATA_DIR
    )

    # --------------------------------------------------------------
    # CHECK FILES
    # --------------------------------------------------------------

    print("\nChecking required files...")

    missing_files = []

    for file_name in REQUIRED_FILES.values():

        file_path = (
            CLEANED_DATA_DIR
            / file_name
        )

        if file_path.exists():

            print(
                f"[OK] {file_name}"
            )

        else:

            print(
                f"[MISSING] {file_name}"
            )

            missing_files.append(
                file_name
            )

    if missing_files:

        print(
            "\nERROR:"
        )

        print(
            "Some required cleaned files are missing."
        )

        return

    print(
        "\nAll 6 cleaned files found."
    )

    # --------------------------------------------------------------
    # LOAD DATASETS
    # --------------------------------------------------------------

    print("\n")

    print_line()

    print(
        "LOADING DATASETS"
    )

    print_line()

    allocation = load_dataset(
        "allocation",
        REQUIRED_FILES[
            "allocation"
        ]
    )

    ongoing = load_dataset(
        "ongoing",
        REQUIRED_FILES[
            "ongoing"
        ]
    )

    calamity = load_dataset(
        "calamity",
        REQUIRED_FILES[
            "calamity"
        ]
    )

    completed = load_dataset(
        "completed",
        REQUIRED_FILES[
            "completed"
        ]
    )

    sanctioned = load_dataset(
        "sanctioned",
        REQUIRED_FILES[
            "sanctioned"
        ]
    )

    recommended = load_dataset(
        "recommended",
        REQUIRED_FILES[
            "recommended"
        ]
    )

    # --------------------------------------------------------------
    # NORMALIZATION
    # --------------------------------------------------------------

    print("\n")

    print_line()

    print(
        "NORMALIZING DATA"
    )

    print_line()

    # Standardize lifecycle column names to lowercase.
    lifecycle_datasets = [

        recommended,

        sanctioned,

        completed,

        ongoing
    ]

    normalized_datasets = []

    for df in lifecycle_datasets:

        df = df.copy()

        df.columns = [

            str(column)
            .strip()
            .lower()
            .replace(" ", "_")

            for column in df.columns
        ]

        normalized_datasets.append(
            df
        )

    (
        recommended,

        sanctioned,

        completed,

        ongoing

    ) = normalized_datasets

    print(
        "Text normalization completed."
    )

    # --------------------------------------------------------------
    # PREPARE WORK DATASETS
    # --------------------------------------------------------------

    recommended = prepare_recommended(
        recommended
    )

    sanctioned = prepare_sanctioned(
        sanctioned
    )

    completed = prepare_completed(
        completed
    )

    ongoing = prepare_ongoing(
        ongoing
    )

    # --------------------------------------------------------------
    # STANDARDIZE COLUMNS
    # --------------------------------------------------------------

    recommended = (
        standardize_lifecycle_columns(
            recommended
        )
    )

    sanctioned = (
        standardize_lifecycle_columns(
            sanctioned
        )
    )

    completed = (
        standardize_lifecycle_columns(
            completed
        )
    )

    ongoing = (
        standardize_lifecycle_columns(
            ongoing
        )
    )

    # --------------------------------------------------------------
    # PARSE DATE COLUMNS
    # --------------------------------------------------------------

    for df in [

        recommended,

        sanctioned,

        completed,

        ongoing

    ]:

        for column in [

            "recommended_date",

            "sanction_date",

            "completion_date"
        ]:

            if column in df.columns:

                df[column] = parse_date(
                    df[column]
                )

    # --------------------------------------------------------------
    # CLEAN NUMERIC COLUMNS
    # --------------------------------------------------------------

    for df in [

        recommended,

        sanctioned,

        completed,

        ongoing

    ]:

        for column in [

            "recommended_amount",

            "sanction_amount",

            "amount_disbursed",

            "fund_disbursed_amount"
        ]:

            if column in df.columns:

                df[column] = clean_numeric(
                    df[column]
                )

    # --------------------------------------------------------------
    # COMBINE WORK DATASETS
    # --------------------------------------------------------------

    print("\n")

    print_line()

    print(
        "COMBINING WORK DATASETS"
    )

    print_line()

    lifecycle = pd.concat(

        [

            recommended,

            sanctioned,

            completed,

            ongoing

        ],

        ignore_index=True,

        sort=False
    )

    print(
        f"\nTotal lifecycle records before consolidation: "
        f"{len(lifecycle):,}"
    )

    # --------------------------------------------------------------
    # CONSOLIDATE
    # --------------------------------------------------------------

    work_master = (
        consolidate_work_records(
            lifecycle
        )
    )

    # --------------------------------------------------------------
    # CREATE STAGES AND LIFECYCLE STATUS
    #
    # IMPORTANT:
    # These are created AFTER consolidation.
    # --------------------------------------------------------------

    work_master = (
        create_lifecycle_features(
            work_master
        )
    )

    work_master = (
        sort_work_master(
            work_master
        )
    )

    # --------------------------------------------------------------
    # PREPARE OTHER MASTERS
    # --------------------------------------------------------------

    print("\n")

    allocation_master = (
        prepare_allocation_master(
            allocation
        )
    )

    calamity_master = (
        prepare_calamity_master(
            calamity
        )
    )

    # --------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------

    integration_summary = (
        create_integration_summary(

            allocation,

            ongoing,

            calamity,

            completed,

            sanctioned,

            recommended,

            work_master,

            allocation_master,

            calamity_master
        )
    )

    # --------------------------------------------------------------
    # SAVE
    # --------------------------------------------------------------

    (

        work_master_file,

        allocation_master_file,

        calamity_master_file,

        summary_file

    ) = save_outputs(

        work_master,

        allocation_master,

        calamity_master,

        integration_summary
    )

    # --------------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------------

    print("\n")

    print_line()

    print(
        "PHASE 4 INTEGRATION COMPLETE"
    )

    print_line()

    print(
        "\nOUTPUT FILES:"
    )

    print(
        f"1. {work_master_file}"
    )

    print(
        f"2. {allocation_master_file}"
    )

    print(
        f"3. {calamity_master_file}"
    )

    print(
        f"4. {summary_file}"
    )

    print(
        "\n"
        + "-" * 70
    )

    print(
        "ROW COUNTS"
    )

    print(
        "-" * 70
    )

    print(
        f"Recommended source rows : "
        f"{len(recommended):,}"
    )

    print(
        f"Sanctioned source rows  : "
        f"{len(sanctioned):,}"
    )

    print(
        f"Completed source rows   : "
        f"{len(completed):,}"
    )

    print(
        f"Ongoing source rows     : "
        f"{len(ongoing):,}"
    )

    print(
        f"Lifecycle records       : "
        f"{len(lifecycle):,}"
    )

    print(
        f"Unique works            : "
        f"{len(work_master):,}"
    )

    print(
        f"Allocation records      : "
        f"{len(allocation_master):,}"
    )

    print(
        f"Calamity records        : "
        f"{len(calamity_master):,}"
    )

    print(
        "\n"
        + "-" * 70
    )

    print(
        "CURRENT WORK STAGES"
    )

    print(
        "-" * 70
    )

    print(
        work_master[
            "current_stage"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\n"
        + "-" * 70
    )

    print(
        "LIFECYCLE STATUS"
    )

    print(
        "-" * 70
    )

    print(
        work_master[
            "lifecycle_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print("\n")

    print_line()

    print(
        "NEXT STEP: PHASE 5 - FEATURE ENGINEERING"
    )

    print_line()


# ======================================================================
# 28. RUN
# ======================================================================

if __name__ == "__main__":

    main()