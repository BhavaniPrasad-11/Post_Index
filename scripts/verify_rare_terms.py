"""Verify the ten rare Malayalam terms directly against the SQLite database."""

import json
import re
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config


def verify_rare_terms() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    conn = sqlite3.connect(str(config.POSTINGS_DB_PATH))
    cur = conn.cursor()

    with open(config.DICTIONARY_FILE_PATH, "r", encoding="utf-8") as f:
        dict_data = json.load(f)

    with open(config.RARE_TERMS_REPORT_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    terms = re.findall(r"TERM:\s*(\S+)", text)
    print(f"Checking {len(terms)} rare terms from {config.RARE_TERMS_REPORT_PATH.name}...")

    assert len(terms) == 10, f"Expected 10 terms, found {len(terms)}"

    for idx, t in enumerate(terms, start=1):
        dict_entry = dict_data.get(t)
        assert dict_entry is not None, f"Term '{t}' not in dictionary.json!"

        cur.execute("SELECT doc_id, positions FROM postings WHERE term = ?", (t,))
        rows = cur.fetchall()
        assert len(rows) == 1, f"Expected exactly 1 posting row for rare term '{t}', got {len(rows)}"

        doc_id, pos_json = rows[0]
        cur.execute("SELECT title, url FROM documents WHERE doc_id = ?", (doc_id,))
        doc_row = cur.fetchone()
        assert doc_row is not None, f"Document #{doc_id} not in documents table!"
        doc_title, doc_url = doc_row

        positions = json.loads(pos_json)

        # Assertions
        assert dict_entry["df"] == 1, f"Term '{t}' DF must be 1, got {dict_entry['df']}"
        assert dict_entry["cf"] == len(positions), f"Term '{t}' CF must match positions count"
        assert len(positions) >= 1, f"Term '{t}' must have at least 1 position"
        assert positions == sorted(positions), f"Positions must be sorted ascending"
        assert all(p >= 1 for p in positions), f"Positions must be 1-based (>= 1)"

        print(
            f"[{idx}] Term: {t:<26} | CF: {dict_entry['cf']} | DF: {dict_entry['df']} | "
            f"DocID: {doc_id:<4} | Title: {doc_title:<22} | Positions: {positions}"
        )

    print("\n[SUCCESS] All 10 rare terms completely verified against SQLite secondary storage!")


if __name__ == "__main__":
    verify_rare_terms()
