# ============================================================
# MPLADS AI MONITORING SYSTEM
# PHASE 1 - DATA PROFILING
# ============================================================

from pathlib import Path
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

# Current file:
# mplads_project/src/data/01_data_profiling.py

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROFILING_DIR = PROJECT_ROOT / "data" / "profiling"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"


# Create output folders if they do not exist
PROFILING_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. READ CSV SAFELY
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

            print(f"SUCCESS: {file_path.name}")
            print(f"Encoding used: {encoding}")

            return df

        except Exception as error:

            last_error = error
            print(
                f"Could not read using {encoding}"
            )

    raise ValueError(
        f"Could not read {file_path.name}. "
        f"Last error: {last_error}"
    )


# ============================================================
# 2. CREATE SUGGESTED STANDARD COLUMN NAME
# ============================================================

def create_standardized_column_name(column_name):

    name = str(column_name).lower().strip()

    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    name = name.replace("-", "_")
    name = name.replace("'", "")
    name = name.replace(".", "")

    # Keep only letters, numbers and underscores
    name = "".join(
        char
        for char in name
        if char.isalnum() or char == "_"
    )

    # Remove repeated underscores
    while "__" in name:
        name = name.replace("__", "_")

    name = name.strip("_")

    return name


# ============================================================
# 3. CLASSIFY COLUMN
# ============================================================

def classify_column(column_name):

    name = str(column_name).lower().strip()

    # Identifier
    if any(keyword in name for keyword in [
        "ida",
        "work id",
        "work_id",
        "project id",
        "project_id",
        "unique id",
        "unique_id",
        "reference",
        "sanction no",
        "sanction number"
    ]):
        return "Identifier"

    # Date
    elif any(keyword in name for keyword in [
        "date",
        "year",
        "month",
        "time"
    ]):
        return "Date / Time"

    # Financial
    elif any(keyword in name for keyword in [
        "amount",
        "cost",
        "fund",
        "expenditure",
        "payment",
        "allocation",
        "allocated",
        "financial",
        "estimate",
        "limit"
    ]):
        return "Financial"

    # Status
    elif any(keyword in name for keyword in [
        "status",
        "completed",
        "ongoing",
        "on-going",
        "pending",
        "progress"
    ]):
        return "Status"

    # Location
    elif any(keyword in name for keyword in [
        "state",
        "district",
        "city",
        "location",
        "village",
        "constituency",
        "area"
    ]):
        return "Location"

    # Text
    elif any(keyword in name for keyword in [
        "description",
        "details",
        "remark",
        "name",
        "member",
        "parliament",
        "agency"
    ]):
        return "Text / Description"

    else:
        return "Other"


# ============================================================
# 4. IDENTIFY POSSIBLE JOIN KEY
# ============================================================

def identify_potential_join_key(column_name):

    name = str(column_name).lower().strip()

    possible_keys = [
        "ida",
        "work id",
        "work_id",
        "project id",
        "project_id",
        "unique id",
        "unique_id"
    ]

    if name in possible_keys:
        return "Possible"

    return "No"


# ============================================================
# 5. GET SAMPLE VALUES
# ============================================================

def get_sample_values(series, number_of_samples=3):

    try:

        samples = (
            series
            .dropna()
            .astype(str)
            .drop_duplicates()
            .head(number_of_samples)
            .tolist()
        )

        return " | ".join(samples)

    except Exception:

        return ""


# ============================================================
# 6. PROFILE ONE DATASET
# ============================================================

def profile_dataset(file_path):

    print("\n" + "=" * 80)
    print(f"PROFILING: {file_path.name}")
    print("=" * 80)

    try:

        # ----------------------------------------------------
        # Read dataset
        # ----------------------------------------------------

        df = read_csv_safely(file_path)

        total_rows = len(df)
        total_columns = len(df.columns)

        print(f"Rows: {total_rows}")
        print(f"Columns: {total_columns}")

        # ----------------------------------------------------
        # Duplicate rows
        # ----------------------------------------------------

        exact_duplicate_rows = int(
            df.duplicated().sum()
        )

        duplicate_column_names = int(
            df.columns.duplicated().sum()
        )

        # ----------------------------------------------------
        # Profile every column
        # ----------------------------------------------------

        profile_rows = []

        for column in df.columns:

            series = df[column]

            # Missing values
            missing_count = int(
                series.isna().sum()
            )

            if total_rows > 0:
                missing_percentage = round(
                    (missing_count / total_rows) * 100,
                    2
                )
            else:
                missing_percentage = 0

            # Unique values
            unique_count = int(
                series.nunique(dropna=True)
            )

            if total_rows > 0:
                unique_percentage = round(
                    (unique_count / total_rows) * 100,
                    2
                )
            else:
                unique_percentage = 0

            # Data type
            data_type = str(series.dtype)

            # Numeric statistics
            numeric_min = None
            numeric_max = None
            numeric_mean = None
            numeric_median = None

            if pd.api.types.is_numeric_dtype(series):

                numeric_min = series.min()
                numeric_max = series.max()
                numeric_mean = series.mean()
                numeric_median = series.median()

            # Add column profile
            profile_rows.append({

                "dataset": file_path.name,

                "column_name": column,

                "suggested_standard_name":
                    create_standardized_column_name(column),

                "data_type": data_type,

                "total_rows": total_rows,

                "missing_count": missing_count,

                "missing_percentage": missing_percentage,

                "unique_count": unique_count,

                "unique_percentage": unique_percentage,

                "column_category":
                    classify_column(column),

                "potential_join_key":
                    identify_potential_join_key(column),

                "sample_values":
                    get_sample_values(series),

                "numeric_min": numeric_min,

                "numeric_max": numeric_max,

                "numeric_mean": numeric_mean,

                "numeric_median": numeric_median

            })

        # ----------------------------------------------------
        # Create profile DataFrame
        # ----------------------------------------------------

        profile_df = pd.DataFrame(profile_rows)

        # ----------------------------------------------------
        # Save individual dataset profile
        # ----------------------------------------------------

        profile_file = (
            PROFILING_DIR /
            f"{file_path.stem}_profile.csv"
        )

        profile_df.to_csv(
            profile_file,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"Profile saved: {profile_file.name}"
        )

        # ----------------------------------------------------
        # Create dataset summary
        # ----------------------------------------------------

        total_missing_cells = int(
            df.isna().sum().sum()
        )

        columns_with_missing = int(
            (df.isna().sum() > 0).sum()
        )

        numeric_columns = int(
            df.select_dtypes(
                include=["number"]
            ).shape[1]
        )

        text_columns = int(
            df.select_dtypes(
                include=["object"]
            ).shape[1]
        )

        dataset_summary = {

            "dataset": file_path.name,

            "rows": total_rows,

            "columns": total_columns,

            "exact_duplicate_rows":
                exact_duplicate_rows,

            "duplicate_column_names":
                duplicate_column_names,

            "total_missing_cells":
                total_missing_cells,

            "columns_with_missing_values":
                columns_with_missing,

            "numeric_columns":
                numeric_columns,

            "text_columns":
                text_columns

        }

        return dataset_summary, profile_df

    except Exception as error:

        print(
            f"\nERROR PROCESSING "
            f"{file_path.name}"
        )

        print(f"ERROR: {error}")

        return None, None


# ============================================================
# 7. CREATE DATASET INVENTORY
# ============================================================

def create_dataset_inventory(all_dataset_summaries):

    if not all_dataset_summaries:
        return pd.DataFrame()

    inventory_df = pd.DataFrame(
        all_dataset_summaries
    )

    inventory_file = (
        PROFILING_DIR /
        "dataset_inventory.csv"
    )

    inventory_df.to_csv(
        inventory_file,
        index=False,
        encoding="utf-8-sig"
    )

    return inventory_df


# ============================================================
# 8. CREATE MASTER COLUMN PROFILE
# ============================================================

def create_master_column_profile(all_column_profiles):

    if not all_column_profiles:
        return pd.DataFrame()

    master_profile_df = pd.concat(
        all_column_profiles,
        ignore_index=True
    )

    master_profile_file = (
        PROFILING_DIR /
        "master_column_profile.csv"
    )

    master_profile_df.to_csv(
        master_profile_file,
        index=False,
        encoding="utf-8-sig"
    )

    return master_profile_df


# ============================================================
# 9. CREATE INITIAL COLUMN MAPPING
# ============================================================

def create_initial_column_mapping(master_profile_df):

    if master_profile_df.empty:
        return pd.DataFrame()

    column_mapping_df = master_profile_df[
        [
            "dataset",
            "column_name",
            "suggested_standard_name",
            "data_type",
            "column_category",
            "missing_percentage",
            "unique_percentage",
            "potential_join_key",
            "sample_values"
        ]
    ].copy()

    # Rename for clarity
    column_mapping_df = column_mapping_df.rename(
        columns={
            "column_name":
                "original_column_name"
        }
    )

    mapping_file = (
        REPORTS_DIR /
        "column_mapping_initial.csv"
    )

    column_mapping_df.to_csv(
        mapping_file,
        index=False,
        encoding="utf-8-sig"
    )

    return column_mapping_df


# ============================================================
# 10. CREATE DATA QUALITY SUMMARY
# ============================================================

def create_data_quality_summary(inventory_df):

    if inventory_df.empty:
        return pd.DataFrame()

    quality_df = inventory_df.copy()

    quality_scores = []

    for _, row in quality_df.iterrows():

        score = 100.0

        # Missing data percentage
        if row["rows"] > 0 and row["columns"] > 0:

            total_cells = (
                row["rows"] *
                row["columns"]
            )

            missing_percentage = (
                row["total_missing_cells"] /
                total_cells
            ) * 100

            score -= missing_percentage

        # Duplicate percentage
        if row["rows"] > 0:

            duplicate_percentage = (
                row["exact_duplicate_rows"] /
                row["rows"]
            ) * 100

            score -= duplicate_percentage

        # Score cannot be below 0
        score = max(0, score)

        quality_scores.append(
            round(score, 2)
        )

    quality_df[
        "initial_data_quality_score"
    ] = quality_scores

    quality_file = (
        REPORTS_DIR /
        "data_quality_summary.csv"
    )

    quality_df.to_csv(
        quality_file,
        index=False,
        encoding="utf-8-sig"
    )

    return quality_df


# ============================================================
# 11. MAIN PROGRAM
# ============================================================

def main():

    print("\n" + "#" * 80)
    print("MPLADS AI MONITORING SYSTEM")
    print("PHASE 1 - DATA PROFILING")
    print("#" * 80)

    print(f"\nPROJECT ROOT:\n{PROJECT_ROOT}")
    print(f"\nRAW DATA:\n{RAW_DATA_DIR}")

    # --------------------------------------------------------
    # Check raw folder
    # --------------------------------------------------------

    if not RAW_DATA_DIR.exists():

        print(
            "\nERROR: data/raw folder "
            "does not exist."
        )

        return

    # --------------------------------------------------------
    # Find all CSV files
    # --------------------------------------------------------

    csv_files = sorted(
        RAW_DATA_DIR.glob("*.csv")
    )

    print(
        f"\nDATASETS FOUND: "
        f"{len(csv_files)}"
    )

    if len(csv_files) == 0:

        print(
            "\nERROR: No CSV files found "
            "inside data/raw"
        )

        return

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    all_dataset_summaries = []
    all_column_profiles = []

    # --------------------------------------------------------
    # Profile each dataset
    # --------------------------------------------------------

    for file_path in csv_files:

        summary, profile = profile_dataset(
            file_path
        )

        if summary is not None:
            all_dataset_summaries.append(
                summary
            )

        if profile is not None:
            all_column_profiles.append(
                profile
            )

    # --------------------------------------------------------
    # Create dataset inventory
    # --------------------------------------------------------

    inventory_df = create_dataset_inventory(
        all_dataset_summaries
    )

    # --------------------------------------------------------
    # Create master column profile
    # --------------------------------------------------------

    master_profile_df = (
        create_master_column_profile(
            all_column_profiles
        )
    )

    # --------------------------------------------------------
    # Create initial column mapping
    # --------------------------------------------------------

    column_mapping_df = (
        create_initial_column_mapping(
            master_profile_df
        )
    )

    # --------------------------------------------------------
    # Create data quality summary
    # --------------------------------------------------------

    quality_df = create_data_quality_summary(
        inventory_df
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print("PHASE 1 PROFILING COMPLETE")
    print("=" * 80)

    print(
        f"\nSuccessfully profiled: "
        f"{len(all_dataset_summaries)} "
        f"out of {len(csv_files)} datasets"
    )

    print("\nFILES CREATED:")

    print(
        "\n1. Individual Dataset Profiles"
    )

    print(
        "2. dataset_inventory.csv"
    )

    print(
        "3. master_column_profile.csv"
    )

    print(
        "4. column_mapping_initial.csv"
    )

    print(
        "5. data_quality_summary.csv"
    )

    print(
        "\nRaw data was NOT modified."
    )


# ============================================================
# 12. RUN PROGRAM
# ============================================================

if __name__ == "__main__":
    main()