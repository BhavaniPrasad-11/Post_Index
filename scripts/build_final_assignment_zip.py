"""Build the exact university submission ZIP: S20240010254-A1-PostIndex-IR-M2026.zip.

Strictly packages exactly the THREE required components:
1. README.txt
2. src/ (all source code, config, requirements, and tests)
3. output/ (all 6 required reports)

Excludes:
- No raw Wikipedia XML dumps
- No large SQLite postings database or JSON dictionary (hosted externally per instructions)
- No nested ZIP files
- No temp or cache artifacts (__pycache__, *.pyc)
"""

import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_final_zip() -> Path:
    sys.stdout.reconfigure(encoding="utf-8")
    zip_name = "S20240010254-A1-PostIndex-IR-M2026.zip"
    zip_path = PROJECT_ROOT / zip_name

    print("=" * 70)
    print(f" BUILDING FINAL SUBMISSION ZIP: {zip_name}")
    print("=" * 70)

    # 1. Verify README.txt
    readme_path = PROJECT_ROOT / "README.txt"
    assert readme_path.exists(), f"Missing {readme_path}"

    # 2. Verify output files
    output_dir = PROJECT_ROOT / "output"
    expected_outputs = [
        "test_results.txt",
        "rare_terms.txt",
        "query_examples.txt",
        "collection_statistics.txt",
        "sample_positional_index.txt",
        "index_validation.txt",
    ]
    for out_f in expected_outputs:
        f_path = output_dir / out_f
        assert f_path.exists() and f_path.stat().st_size > 0, f"Missing output: {out_f}"

    # 3. Verify src files
    src_dir = PROJECT_ROOT / "src"
    assert src_dir.exists(), f"Missing {src_dir}"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        # A. Add README.txt at root
        z.write(readme_path, "README.txt")
        print(f"Added [Root File]: README.txt ({readme_path.stat().st_size} bytes)")

        # B. Add src/ files and subdirectories
        print("\nAdding [src/] files:")
        for item in src_dir.rglob("*"):
            if item.is_file():
                # Filter out cache files and nested zip archives
                if "__pycache__" in item.parts or item.suffix in [".pyc", ".pyo", ".zip"]:
                    continue
                rel_path = item.relative_to(src_dir)
                arcname = f"src/{rel_path.as_posix()}"
                z.write(item, arcname)
                print(f"  {arcname}")

        # C. Add output/ files
        print("\nAdding [output/] reports:")
        for out_f in expected_outputs:
            item = output_dir / out_f
            arcname = f"output/{out_f}"
            z.write(item, arcname)
            print(f"  {arcname}")

    zip_size_kb = zip_path.stat().st_size / 1024
    print("\n" + "=" * 70)
    print(f" [SUCCESS] Archive created: {zip_path.name}")
    print(f" Location: {zip_path}")
    print(f" File Size: {zip_size_kb:.2f} KB ({zip_path.stat().st_size:,} bytes)")
    print("=" * 70)
    return zip_path


if __name__ == "__main__":
    build_final_zip()
