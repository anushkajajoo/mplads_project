from pathlib import Path
import pandas as pd
import json
from datetime import datetime
import sys


# ============================================================
# MPLADS INSIGHT AI
# PHASE 1B - SCHEMA VALIDATION
# WINDOWS-SAFE VERSION
# ============================================================

print("\n" + "#" * 70)
print("MPLADS INSIGHT AI")
print("PHASE 1B - SCHEMA VALIDATION")
print("#" * 70)


# ============================================================
# 1. FORCE UTF-8 OUTPUT
# ============================================================

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================
# 2. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

MAPPING_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "reports"
    / "column_mapping_initial.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "schema"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 3. CHECK FILES
# ============================================================

if not RAW_DATA_DIR.exists():

    raise FileNotFoundError(
        f"Raw data folder not found: {RAW_DATA_DIR}"
    )


if not MAPPING_FILE.exists():

    raise FileNotFoundError(
        f"Column mapping file not found: {MAPPING_FILE}"
    )


# ============================================================
# 4. READ MAPPING FILE
# ============================================================

try:

    mapping_df = pd.read_csv(
        MAPPING_FILE,
        encoding="utf-8-sig",
        low_memory=False
    )

except UnicodeDecodeError:

    mapping_df = pd.read_csv(
        MAPPING_FILE,
        encoding="cp1252",
        low_memory=False
    )


# ============================================================
# 5. CHECK MAPPING COLUMNS
# ============================================================

required_mapping_columns = [
    "dataset",
    "original_column_name",
    "suggested_standard_name"
]

missing_columns = [
    column
    for column in required_mapping_columns
    if column not in mapping_df.columns
]

if missing_columns:

    raise ValueError(
        "Missing columns in column_mapping_initial.csv: "
        + ", ".join(missing_columns)
    )


# ============================================================
# 6. DATASET-SPECIFIC SCHEMA
# ============================================================

DATASET_SCHEMA = {

    "Allocated_Limit.csv": {

        "required": [
            "state",
            "honble_members_of_parliaments",
            "constituency",
            "allocated_amount"
        ],

        "optional": [
            "sr_no"
        ]
    },


    "Completed_On-going_Works.csv": {

        "required": [
            "work_id",
            "state",
            "work",
            "ida",
            "fund_disbursed_amount"
        ],

        "optional": [
            "sr_no",
            "honble_members_of_parliament",
            "constituency",
            "expenditure_date",
            "vendor_name",
            "payment_status"
        ]
    },


    "consented_Calamity.csv": {

        "required": [
            "calamity_type",
            "calamity_name",
            "honble_members_of_parliament",
            "date_of_consent",
            "consent_amount"
        ],

        "optional": [
            "sr_no"
        ]
    },


    "Works Completed.csv": {

        "required": [
            "work",
            "state",
            "ida",
            "work_description",
            "completion_date",
            "amount_disbursed"
        ],

        "optional": [
            "sr_no",
            "work_category",
            "honble_members_of_parliament",
            "constituency",
            "image"
        ]
    },


    "Works Sanctioned.csv": {

        "required": [
            "work",
            "state",
            "ida",
            "work_description",
            "recommended_date",
            "sanction_date",
            "sanction_amount",
            "work_status"
        ],

        "optional": [
            "sr_no",
            "work_category",
            "honble_members_of_parliament",
            "constituency"
        ]
    },


    "Works_Recommended.csv": {

        "required": [
            "work",
            "state",
            "ida",
            "work_description",
            "recommended_date",
            "recommended_amount"
        ],

        "optional": [
            "sr_no",
            "work_category",
            "honble_members_of_parliament",
            "elected_nominated",
            "sanction_date"
        ]
    }
}


# ============================================================
# 7. NORMALIZE NAME
# ============================================================

def normalize_name(value):

    if pd.isna(value):

        return ""

    return str(value).strip().lower()


# ============================================================
# 8. BUILD MAPPING LOOKUP
# ============================================================

mapping_lookup = {}


for _, row in mapping_df.iterrows():

    dataset = str(
        row["dataset"]
    ).strip()

    original_column = str(
        row["original_column_name"]
    ).strip()

    standard_name = str(
        row["suggested_standard_name"]
    ).strip()


    if dataset not in mapping_lookup:

        mapping_lookup[dataset] = {}


    normalized_standard = normalize_name(
        standard_name
    )


    mapping_lookup[dataset][
        normalized_standard
    ] = original_column


# ============================================================
# 9. FIND DATASETS
# ============================================================

datasets = sorted(
    RAW_DATA_DIR.glob("*.csv")
)

print(
    f"\nDatasets found: {len(datasets)}"
)


# ============================================================
# 10. RESULTS
# ============================================================

availability_map = {}

passed = 0
failed = 0


# ============================================================
# 11. VALIDATE EACH DATASET
# ============================================================

for file_path in datasets:

    dataset_name = file_path.name


    print("\n" + "=" * 70)
    print(
        f"Checking: {dataset_name}"
    )
    print("=" * 70)


    # --------------------------------------------------------
    # Check schema definition
    # --------------------------------------------------------

    if dataset_name not in DATASET_SCHEMA:

        print(
            "WARNING: No schema definition found."
        )

        availability_map[dataset_name] = {

            "schema_status":
                "NO_SCHEMA_DEFINITION",

            "required_fields": {},

            "optional_fields": {},

            "source_columns": []

        }

        continue


    # --------------------------------------------------------
    # Read raw CSV
    # --------------------------------------------------------

    try:

        try:

            df = pd.read_csv(
                file_path,
                encoding="utf-8-sig",
                low_memory=False
            )

        except UnicodeDecodeError:

            df = pd.read_csv(
                file_path,
                encoding="cp1252",
                low_memory=False
            )

    except Exception as e:

        print(
            f"ERROR: Could not read dataset: {e}"
        )

        availability_map[dataset_name] = {

            "schema_status":
                "READ_ERROR",

            "required_fields": {},

            "optional_fields": {},

            "source_columns": [],

            "error": str(e)

        }

        failed += 1

        continue


    schema = DATASET_SCHEMA[
        dataset_name
    ]


    required_results = {}

    optional_results = {}

    missing_required = []


    dataset_mapping = mapping_lookup.get(
        dataset_name,
        {}
    )


    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    for field in schema["required"]:

        normalized_field = normalize_name(
            field
        )

        source_column = dataset_mapping.get(
            normalized_field
        )


        if source_column is not None:

            if source_column in df.columns:

                required_results[field] = {

                    "status":
                        "AVAILABLE",

                    "source_column":
                        source_column

                }

                print(
                    f"REQUIRED: {field} -> AVAILABLE"
                )

            else:

                required_results[field] = {

                    "status":
                        "MAPPING_FOUND_BUT_SOURCE_MISSING",

                    "source_column":
                        source_column

                }

                missing_required.append(
                    field
                )

                print(
                    f"REQUIRED: {field} -> "
                    f"SOURCE COLUMN NOT FOUND"
                )

        else:

            required_results[field] = {

                "status":
                    "NOT_AVAILABLE",

                "source_column":
                    None

            }

            missing_required.append(
                field
            )

            print(
                f"REQUIRED: {field} -> MISSING"
            )


    # ========================================================
    # OPTIONAL FIELDS
    # ========================================================

    for field in schema["optional"]:

        normalized_field = normalize_name(
            field
        )

        source_column = dataset_mapping.get(
            normalized_field
        )


        if source_column is not None:

            if source_column in df.columns:

                optional_results[field] = {

                    "status":
                        "AVAILABLE",

                    "source_column":
                        source_column

                }

                print(
                    f"OPTIONAL: {field} -> AVAILABLE"
                )

            else:

                optional_results[field] = {

                    "status":
                        "MAPPING_FOUND_BUT_SOURCE_MISSING",

                    "source_column":
                        source_column

                }

                print(
                    f"OPTIONAL: {field} -> "
                    f"SOURCE COLUMN NOT FOUND"
                )

        else:

            optional_results[field] = {

                "status":
                    "NOT_AVAILABLE",

                "source_column":
                    None

            }

            print(
                f"OPTIONAL: {field} -> NOT AVAILABLE"
            )


    # ========================================================
    # SCHEMA STATUS
    # ========================================================

    if len(missing_required) == 0:

        schema_status = "PASSED"

        passed += 1

        print(
            "\nSCHEMA STATUS: PASSED"
        )

    else:

        schema_status = "FAILED"

        failed += 1

        print(
            "\nSCHEMA STATUS: FAILED"
        )

        print(
            "Missing required fields:"
        )

        for field in missing_required:

            print(
                f"- {field}"
            )


    # ========================================================
    # SAVE RESULT
    # ========================================================

    availability_map[dataset_name] = {

        "schema_status":
            schema_status,

        "file":
            dataset_name,

        "rows":
            int(len(df)),

        "columns":
            int(len(df.columns)),

        "source_columns": [
            str(column)
            for column in df.columns
        ],

        "required_fields":
            required_results,

        "optional_fields":
            optional_results,

        "missing_required_fields":
            missing_required

    }


# ============================================================
# 12. SAVE JSON
# ============================================================

output_file = (
    OUTPUT_DIR
    / "field_availability_map.json"
)


output_data = {

    "generated_at":
        datetime.now().isoformat(),

    "phase":
        "Phase 1B - Schema Validation",

    "mapping_source":
        str(MAPPING_FILE),

    "total_datasets":
        len(datasets),

    "passed":
        passed,

    "failed":
        failed,

    "datasets":
        availability_map
}


with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output_data,
        f,
        indent=4,
        ensure_ascii=False
    )


# ============================================================
# 13. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)

print(
    "PHASE 1B SCHEMA VALIDATION COMPLETE"
)

print("=" * 70)

print(
    f"\nTotal datasets: {len(datasets)}"
)

print(
    f"Passed: {passed}"
)

print(
    f"Failed: {failed}"
)

print(
    "\nField availability map:"
)

print(
    output_file
)

print("\n" + "=" * 70)


