# ============================================================
# MPLADS INSIGHT AI
# PHASE 0 - DATA INGESTION
# ============================================================

from pathlib import Path
from datetime import datetime
import hashlib
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

# Current file:
# mplads_project/src/ingestion/01_ingestion.py

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

INGESTION_OUTPUT_DIR = (
    PROJECT_ROOT / "outputs" / "ingestion"
)

INGESTION_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. CALCULATE FILE HASH
# ============================================================

def calculate_file_hash(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:

            data = file.read(1024 * 1024)

            if not data:
                break

            sha256.update(data)

    return sha256.hexdigest()


# ============================================================
# 3. READ CSV SAFELY
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

            return df, encoding

        except Exception as error:

            last_error = error

    raise ValueError(
        f"Unable to read file. "
        f"Last error: {last_error}"
    )


# ============================================================
# 4. PROCESS ONE FILE
# ============================================================

def process_file(file_path, source_id):

    print("\n" + "=" * 70)

    print(
        f"Processing: {file_path.name}"
    )

    print("=" * 70)

    ingestion_time = datetime.now().isoformat(
        timespec="seconds"
    )

    # --------------------------------------------------------
    # Basic file information
    # --------------------------------------------------------

    file_size = file_path.stat().st_size

    # --------------------------------------------------------
    # Check empty file
    # --------------------------------------------------------

    if file_size == 0:

        print("STATUS: EMPTY FILE")

        return {
            "source_id": source_id,
            "source_file": file_path.name,
            "file_path": str(file_path),
            "file_hash": None,
            "file_size_bytes": 0,
            "row_count": 0,
            "column_count": 0,
            "encoding": None,
            "status": "FAILED_EMPTY_FILE",
            "error_message": "File is empty",
            "ingested_at": ingestion_time
        }

    # --------------------------------------------------------
    # Calculate SHA-256 hash
    # --------------------------------------------------------

    try:

        file_hash = calculate_file_hash(
            file_path
        )

    except Exception as error:

        print(
            f"STATUS: HASH ERROR - {error}"
        )

        return {
            "source_id": source_id,
            "source_file": file_path.name,
            "file_path": str(file_path),
            "file_hash": None,
            "file_size_bytes": file_size,
            "row_count": None,
            "column_count": None,
            "encoding": None,
            "status": "FAILED_HASH",
            "error_message": str(error),
            "ingested_at": ingestion_time
        }

    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    try:

        df, encoding = read_csv_safely(
            file_path
        )

    except Exception as error:

        print(
            f"STATUS: UNREADABLE FILE - {error}"
        )

        return {
            "source_id": source_id,
            "source_file": file_path.name,
            "file_path": str(file_path),
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "row_count": None,
            "column_count": None,
            "encoding": None,
            "status": "FAILED_UNREADABLE",
            "error_message": str(error),
            "ingested_at": ingestion_time
        }

    # --------------------------------------------------------
    # Count rows and columns
    # --------------------------------------------------------

    row_count = len(df)

    column_count = len(df.columns)

    # --------------------------------------------------------
    # Check empty dataset
    # --------------------------------------------------------

    if row_count == 0:

        print("STATUS: EMPTY DATASET")

        return {
            "source_id": source_id,
            "source_file": file_path.name,
            "file_path": str(file_path),
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "row_count": 0,
            "column_count": column_count,
            "encoding": encoding,
            "status": "FAILED_EMPTY_DATASET",
            "error_message": "CSV contains zero rows",
            "ingested_at": ingestion_time
        }

    # --------------------------------------------------------
    # Successful ingestion
    # --------------------------------------------------------

    print(
        f"Rows: {row_count}"
    )

    print(
        f"Columns: {column_count}"
    )

    print(
        f"Encoding: {encoding}"
    )

    print(
        f"SHA-256: {file_hash}"
    )

    print(
        "STATUS: SUCCESS"
    )

    return {
        "source_id": source_id,
        "source_file": file_path.name,
        "file_path": str(file_path),
        "file_hash": file_hash,
        "file_size_bytes": file_size,
        "row_count": row_count,
        "column_count": column_count,
        "encoding": encoding,
        "status": "SUCCESS",
        "error_message": None,
        "ingested_at": ingestion_time
    }


# ============================================================
# 5. MAIN INGESTION PROCESS
# ============================================================

def main():

    print("\n" + "#" * 70)

    print(
        "MPLADS INSIGHT AI"
    )

    print(
        "PHASE 0 - DATA INGESTION"
    )

    print("#" * 70)

    print(
        f"\nRaw data directory:"
    )

    print(
        RAW_DATA_DIR
    )

    # --------------------------------------------------------
    # Check raw directory
    # --------------------------------------------------------

    if not RAW_DATA_DIR.exists():

        print(
            "\nERROR: Raw data directory does not exist."
        )

        return

    # --------------------------------------------------------
    # Find CSV files
    # --------------------------------------------------------

    csv_files = sorted(
        RAW_DATA_DIR.glob("*.csv")
    )

    print(
        f"\nCSV files found: {len(csv_files)}"
    )

    # --------------------------------------------------------
    # No files
    # --------------------------------------------------------

    if len(csv_files) == 0:

        print(
            "\nERROR: No CSV files found."
        )

        return

    # --------------------------------------------------------
    # Process files
    # --------------------------------------------------------

    results = []

    for index, file_path in enumerate(
        csv_files,
        start=1
    ):

        source_id = f"SRC{index:03d}"

        result = process_file(
            file_path,
            source_id
        )

        results.append(result)

    # --------------------------------------------------------
    # Create manifest
    # --------------------------------------------------------

    manifest_df = pd.DataFrame(
        results
    )

    manifest_file = (
        INGESTION_OUTPUT_DIR /
        "ingestion_manifest.csv"
    )

    manifest_df.to_csv(
        manifest_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Create validation report
    # --------------------------------------------------------

    validation_df = manifest_df[
        [
            "source_id",
            "source_file",
            "row_count",
            "column_count",
            "status",
            "error_message"
        ]
    ].copy()

    validation_file = (
        INGESTION_OUTPUT_DIR /
        "ingestion_validation.csv"
    )

    validation_df.to_csv(
        validation_file,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    successful = sum(
        manifest_df["status"] == "SUCCESS"
    )

    failed = len(manifest_df) - successful

    print("\n" + "=" * 70)

    print(
        "PHASE 0 INGESTION COMPLETE"
    )

    print("=" * 70)

    print(
        f"\nTotal files: {len(manifest_df)}"
    )

    print(
        f"Successful: {successful}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"\nManifest:"
    )

    print(
        manifest_file
    )

    print(
        f"\nValidation report:"
    )

    print(
        validation_file
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "Raw files were NOT modified."
    )


# ============================================================
# 6. RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    main()