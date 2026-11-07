"""Packaging and Submission Assembler for University Information Retrieval Assignment.

Student Roll Number: S20240010254

Creates:
1. S20240010254-src.zip (Clean source code, tests, documentation, outputs, small sample data; excludes raw dump & large db)
2. S20240010254-index-artifacts.zip (Actual persistent index artifacts: dictionary.json and postings.sqlite3)
3. S20240010254-IR-Submission/ directory matching the requested submission structure
4. S20240010254-final-submission.zip (Complete combined archive of S20240010254-IR-Submission/)
"""

import shutil
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_submission_packages(roll_number: str = "S20240010254") -> None:
    """Generate all required submission artifacts and directory structures."""
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 70)
    print(f" PACKAGING SUBMISSION ARTIFACTS FOR ROLL NO: {roll_number}")
    print("=" * 70)

    # Output directory for the final submission
    submission_dir = PROJECT_ROOT.parent / f"{roll_number}-IR-Submission"
    submission_dir.mkdir(parents=True, exist_ok=True)

    # Subdirectories
    sub_index_dir = submission_dir / "index"
    sub_output_dir = submission_dir / "output"
    sub_doc_dir = submission_dir / "documentation"
    sub_index_dir.mkdir(parents=True, exist_ok=True)
    sub_output_dir.mkdir(parents=True, exist_ok=True)
    sub_doc_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 1. CREATE S20240010254-src.zip
    # -------------------------------------------------------------
    src_zip_path = PROJECT_ROOT / f"{roll_number}-src.zip"
    print(f"\n[1/4] Building clean source archive: {src_zip_path.name}...")

    src_includes = [
        "README.md",
        "requirements.txt",
        "main.py",
        "config.py",
        "src",
        "tests",
        "scripts",
        "output",
        "documentation",
        "data/collection_info.json",
    ]

    with zipfile.ZipFile(src_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in src_includes:
            item_path = PROJECT_ROOT / item
            if not item_path.exists():
                print(f"  [WARNING] Skipping missing: {item}")
                continue
            if item_path.is_file():
                zipf.write(item_path, item)
                print(f"  Added file: {item}")
            elif item_path.is_dir():
                for subfile in item_path.rglob("*"):
                    if subfile.is_file():
                        if "__pycache__" in subfile.parts or subfile.suffix in [".pyc", ".pyo"]:
                            continue
                        arcname = str(subfile.relative_to(PROJECT_ROOT))
                        zipf.write(subfile, arcname)
                        print(f"  Added: {arcname}")

    src_size_kb = src_zip_path.stat().st_size / 1024
    print(f"[SUCCESS] Created {src_zip_path.name} ({src_size_kb:.1f} KB)")

    # -------------------------------------------------------------
    # 2. CREATE S20240010254-index-artifacts.zip
    # -------------------------------------------------------------
    idx_zip_path = PROJECT_ROOT / f"{roll_number}-index-artifacts.zip"
    print(f"\n[2/4] Building index artifacts archive: {idx_zip_path.name}...")

    dict_path = PROJECT_ROOT / "index" / "dictionary.json"
    post_path = PROJECT_ROOT / "index" / "postings.sqlite3"

    assert dict_path.exists(), f"Missing {dict_path}"
    assert post_path.exists(), f"Missing {post_path}"

    with zipfile.ZipFile(idx_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        print(f"  Compressing dictionary.json ({dict_path.stat().st_size / (1024*1024):.2f} MB)...")
        zipf.write(dict_path, "index/dictionary.json")
        print(f"  Compressing postings.sqlite3 ({post_path.stat().st_size / (1024*1024):.2f} MB)...")
        zipf.write(post_path, "index/postings.sqlite3")

    idx_size_mb = idx_zip_path.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Created {idx_zip_path.name} ({idx_size_mb:.2f} MB)")

    # -------------------------------------------------------------
    # 3. ASSEMBLE S20240010254-IR-Submission/ DIRECTORY
    # -------------------------------------------------------------
    print(f"\n[3/4] Assembling submission directory: {submission_dir.name}...")

    # Copy README.md
    shutil.copy2(PROJECT_ROOT / "README.md", submission_dir / "README.md")

    # Copy S20240010254-src.zip
    shutil.copy2(src_zip_path, submission_dir / src_zip_path.name)

    # Copy index artifacts
    shutil.copy2(dict_path, sub_index_dir / "dictionary.json")
    shutil.copy2(post_path, sub_index_dir / "postings.sqlite3")

    # Copy output reports
    output_files = [
        "collection_statistics.txt",
        "rare_terms.txt",
        "test_results.txt",
        "query_examples.txt",
        "sample_positional_index.txt",
        "index_validation.txt",
    ]
    for out_name in output_files:
        src_out = PROJECT_ROOT / "output" / out_name
        if src_out.exists():
            shutil.copy2(src_out, sub_output_dir / out_name)
            print(f"  Copied output: {out_name}")
        else:
            print(f"  [WARNING] Output file missing: {out_name}")

    # Copy documentation
    shutil.copy2(
        PROJECT_ROOT / "documentation" / "execution_instructions.txt",
        sub_doc_dir / "execution_instructions.txt",
    )

    print(f"[SUCCESS] Directory assembled at {submission_dir}")

    # -------------------------------------------------------------
    # 4. CREATE S20240010254-final-submission.zip
    # -------------------------------------------------------------
    combined_zip_path = PROJECT_ROOT.parent / f"{roll_number}-final-submission.zip"
    print(f"\n[4/4] Building combined final submission archive: {combined_zip_path.name}...")

    with zipfile.ZipFile(combined_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in submission_dir.rglob("*"):
            if item.is_file():
                arcname = str(item.relative_to(submission_dir.parent))
                zipf.write(item, arcname)

    comb_size_mb = combined_zip_path.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Combined archive created: {combined_zip_path} ({comb_size_mb:.2f} MB)")

    print("\n" + "=" * 70)
    print(" ALL SUBMISSION DELIVERABLES PACKAGED SUCCESSFULLY!")
    print("=" * 70)
    print(f" 1. Source Archive:         {src_zip_path}")
    print(f" 2. Index Artifacts:        {idx_zip_path}")
    print(f" 3. Submission Directory:   {submission_dir}")
    print(f" 4. Combined Archive:       {combined_zip_path}")
    print("=" * 70)


if __name__ == "__main__":
    roll = sys.argv[1] if len(sys.argv) > 1 else "S20240010254"
    create_submission_packages(roll)
