"""Verify all ten query demonstration examples directly against the search engine."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.search_engine import MalayalamSearchEngine


def verify_query_examples() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    engine = MalayalamSearchEngine()
    engine.initialize()

    examples = [
        {"id": 1, "query": "കേരളം", "is_phrase": False, "min_cf": 300, "min_df": 150},
        {"id": 2, "query": "മലയാളം", "is_phrase": False, "min_cf": 800, "min_df": 400},
        {"id": 3, "query": "ഇന്ത്യ", "is_phrase": False, "min_cf": 800, "min_df": 400},
        {"id": 4, "query": "ചരിത്രം", "is_phrase": False, "min_cf": 1000, "min_df": 800},
        {"id": 5, "query": "സാഹിത്യം", "is_phrase": False, "min_cf": 150, "min_df": 100},
        {"id": 6, "query": "കേരള സാഹിത്യ അക്കാദമി", "is_phrase": True, "min_cf": 100, "min_df": 50},
        {"id": 7, "query": "ഇന്ത്യൻ സംസ്ഥാനമായ", "is_phrase": True, "min_cf": 5, "min_df": 5},
        {"id": 8, "query": "പ്രധാന നഗരം", "is_phrase": True, "min_cf": 2, "min_df": 2},
        {"id": 9, "query": "സമൂഹ്യതിന്മകൾക്കെതിരെയും", "is_phrase": False, "exact_cf": 1, "exact_df": 1},
        {"id": 10, "query": "അക്ഷരമാലയെ", "is_phrase": False, "exact_cf": 1, "exact_df": 1},
    ]

    print(f"Executing and verifying all {len(examples)} demonstration queries against index...")

    for ex in examples:
        q = ex["query"]
        if ex["is_phrase"]:
            res = engine.search_phrase(q)
            print(f"[EXAMPLE #{ex['id']}] PHRASE: \"{q}\" -> Matches: {res.df} docs, {res.cf} total occurrences.")
            assert res.df >= ex.get("min_df", 1), f"Phrase '{q}' DF {res.df} < expected {ex['min_df']}"
            assert res.cf >= ex.get("min_cf", 1), f"Phrase '{q}' CF {res.cf} < expected {ex['min_cf']}"
            # Check positions
            for m in res.matches[:3]:
                assert len(m["start_positions"]) >= 1, "Must have valid start positions"
                assert all(p >= 1 for p in m["start_positions"]), "Start positions must be 1-based"
        else:
            res = engine.search_term(q)
            print(f"[EXAMPLE #{ex['id']}] TERM: '{q}' -> CF: {res.cf}, DF: {res.df}.")
            if "exact_cf" in ex:
                assert res.cf == ex["exact_cf"], f"Term '{q}' CF {res.cf} != expected {ex['exact_cf']}"
                assert res.df == ex["exact_df"], f"Term '{q}' DF {res.df} != expected {ex['exact_df']}"
            else:
                assert res.cf >= ex.get("min_cf", 1), f"Term '{q}' CF {res.cf} < expected {ex['min_cf']}"
                assert res.df >= ex.get("min_df", 1), f"Term '{q}' DF {res.df} < expected {ex['min_df']}"
            for m in res.matches[:3]:
                assert len(m["positions"]) >= 1, "Must have valid positions"
                assert all(p >= 1 for p in m["positions"]), "Positions must be 1-based"

    print("\n[SUCCESS] All 10 query demonstration examples successfully executed and verified against live index!")


if __name__ == "__main__":
    verify_query_examples()
