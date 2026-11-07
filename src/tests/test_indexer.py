"""Automated Unit Tests for Malayalam Positional Inverted Index.

Covers the five required test cases:
- Test 1: Malayalam Unicode tokenization.
- Test 2: Correct positional indexing of repeated terms within a document.
- Test 3: Correct Collection Frequency (CF) and Document Frequency (DF).
- Test 4: Correct retrieval of positional postings from disk.
- Test 5: Correct phrase searching using positional information.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root in sys.path
THIS_DIR = Path(__file__).resolve().parent
for p in (THIS_DIR, THIS_DIR.parent, THIS_DIR.parent.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from src.dictionary import InvertedIndexDictionary
    from src.search_engine import MalayalamSearchEngine
    from src.storage_manager import StorageManager
    from src.tokenizer import MalayalamTokenizer
except ImportError:
    from dictionary import InvertedIndexDictionary
    from search_engine import MalayalamSearchEngine
    from storage_manager import StorageManager
    from tokenizer import MalayalamTokenizer


class TestMalayalamPositionalIndexer(unittest.TestCase):
    """Five required verification test cases for the Malayalam Positional Index."""

    def setUp(self) -> None:
        """Create a temporary test workspace and synthetic Malayalam test documents."""
        self.test_dir = tempfile.mkdtemp(prefix="ml_ir_test_")
        self.db_path = Path(self.test_dir) / "test_postings.sqlite3"
        self.dict_path = Path(self.test_dir) / "test_dictionary.json"

        self.tokenizer = MalayalamTokenizer()
        self.storage = StorageManager(self.db_path)
        self.storage.initialize_schema(drop_existing=True)
        self.dictionary = InvertedIndexDictionary()

        # Manually verified synthetic Malayalam test corpus:
        # Doc 1: "കേരളം ഇന്ത്യയുടെ മനോഹരമായ സംസ്ഥാനമാണ് കേരളം"
        # Doc 2: "മലയാളം കേരളത്തിന്റെ മാതൃഭാഷയാണ് കേരളം സുന്ദരമാണ്"
        # Doc 3: "ഇന്ത്യയുടെ തെക്കുപടിഞ്ഞാറൻ സംസ്ഥാനമാണ് കേരളം മലയാളം സംസാരിക്കുന്ന ജനങ്ങൾ ഇവിടെ താമസിക്കുന്നു"
        self.synthetic_corpus = [
            (
                1,
                101,
                "കേരളം സംസ്ഥാനം",
                "https://ml.wikipedia.org/wiki/kerala",
                "കേരളം ഇന്ത്യയുടെ മനോഹരമായ സംസ്ഥാനമാണ് കേരളം",
            ),
            (
                2,
                102,
                "മലയാള ഭാഷ",
                "https://ml.wikipedia.org/wiki/malayalam",
                "മലയാളം കേരളത്തിന്റെ മാതൃഭാഷയാണ് കേരളം സുന്ദരമാണ്",
            ),
            (
                3,
                103,
                "ദക്ഷിണേന്ത്യ",
                "https://ml.wikipedia.org/wiki/south_india",
                "ഇന്ത്യയുടെ തെക്കുപടിഞ്ഞാറൻ സംസ്ഥാനമാണ് കേരളം മലയാളം സംസാരിക്കുന്ന ജനങ്ങൾ ഇവിടെ താമസിക്കുന്നു",
            ),
        ]

        # Index the synthetic corpus
        doc_rows = []
        postings_rows = []
        for doc_id, wiki_id, title, url, text in self.synthetic_corpus:
            tok_pos = self.tokenizer.tokenize_with_positions(text)
            doc_rows.append((doc_id, wiki_id, title, url, len(tok_pos)))

            term_map = {}
            for term, pos in tok_pos:
                term_map.setdefault(term, []).append(pos)

            for term, positions in term_map.items():
                self.dictionary.add_term_doc_stats(term, len(positions))
                postings_rows.append((term, doc_id, json.dumps(positions)))

        self.storage.save_documents_batch(doc_rows)
        self.storage.save_postings_batch(postings_rows)
        self.storage.create_indices()
        self.dictionary.save_to_json(self.dict_path)

        # Initialize search engine on this test index
        self.search_engine = MalayalamSearchEngine(
            db_path=self.db_path, dict_path=self.dict_path
        )
        self.search_engine.initialize()

    def tearDown(self) -> None:
        """Clean up temporary test workspace."""
        self.storage.close()
        self.search_engine.storage_manager.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_1_unicode_tokenization(self) -> None:
        """Test 1: Malayalam Unicode tokenization.

        Verifies NFC normalization, Malayalam chillu letters, vowel signs,
        chandrakkala, stripping of punctuation, and 1-based sequential position assignment.
        """
        sample_text = "കേരളം ഇന്ത്യയുടെ മനോഹരമായ സംസ്ഥാനമാണ്"
        tokens_with_pos = self.tokenizer.tokenize_with_positions(sample_text)

        expected_tokens = ["കേരളം", "ഇന്ത്യയുടെ", "മനോഹരമായ", "സംസ്ഥാനമാണ്"]
        actual_tokens = [tok for tok, _ in tokens_with_pos]
        actual_positions = [pos for _, pos in tokens_with_pos]

        # Verify exact token sequence
        self.assertEqual(actual_tokens, expected_tokens)
        # Verify 1-based sequential positions: [1, 2, 3, 4]
        self.assertEqual(actual_positions, [1, 2, 3, 4])

        # Test chillu letters and punctuation handling
        complex_text = "‘കേരളത്തിൽ’, 2026-ൽ മലയാളം സംസാരിക്കുന്നു!"
        complex_tokens = self.tokenizer.tokenize(complex_text)
        self.assertIn("കേരളത്തിൽ", complex_tokens)
        self.assertIn("2026", complex_tokens)
        self.assertIn("ൽ", complex_tokens)
        self.assertIn("മലയാളം", complex_tokens)
        self.assertIn("സംസാരിക്കുന്നു", complex_tokens)

    def test_2_positional_indexing_of_repeated_terms(self) -> None:
        """Test 2: Correct positional indexing of repeated terms within a document.

        In Document 1: "കേരളം ഇന്ത്യയുടെ മനോഹരമായ സംസ്ഥാനമാണ് കേരളം"
        Tokens:
        1: കേരളം
        2: ഇന്ത്യയുടെ
        3: മനോഹരമായ
        4: സംസ്ഥാനമാണ്
        5: കേരളം
        The term 'കേരളം' appears at positions 1 and 5.
        """
        postings = self.storage.get_postings("കേരളം")
        doc1_posting = next((pos for doc_id, pos in postings if doc_id == 1), None)

        self.assertIsNotNone(doc1_posting, "Posting for DocID 1 must exist for 'കേരളം'")
        self.assertEqual(
            doc1_posting,
            [1, 5],
            f"Expected positions [1, 5] for repeated term 'കേരളം' in Doc 1, got {doc1_posting}",
        )
        # Verify positions are in strictly ascending order
        self.assertEqual(doc1_posting, sorted(doc1_posting))

    def test_3_collection_and_document_frequency(self) -> None:
        """Test 3: Correct Collection Frequency (CF) and Document Frequency (DF).

        Expected manually calculated stats across the 3 synthetic documents:
        - Term 'കേരളം':
          Doc 1: [1, 5] (count 2)
          Doc 2: [4]    (count 1)
          Doc 3: [4]    (count 1)
          -> CF = 4, DF = 3
        - Term 'സംസ്ഥാനമാണ്':
          Doc 1: [4]    (count 1)
          Doc 3: [3]    (count 1)
          -> CF = 2, DF = 2
        """
        entry_kerala = self.dictionary.get("കേരളം")
        self.assertIsNotNone(entry_kerala, "Term 'കേരളം' must be in dictionary")
        self.assertEqual(entry_kerala.cf, 4, f"Expected CF=4 for 'കേരളം', got {entry_kerala.cf}")
        self.assertEqual(entry_kerala.df, 3, f"Expected DF=3 for 'കേരളം', got {entry_kerala.df}")

        entry_state = self.dictionary.get("സംസ്ഥാനമാണ്")
        self.assertIsNotNone(entry_state, "Term 'സംസ്ഥാനമാണ്' must be in dictionary")
        self.assertEqual(entry_state.cf, 2, f"Expected CF=2 for 'സംസ്ഥാനമാണ്', got {entry_state.cf}")
        self.assertEqual(entry_state.df, 2, f"Expected DF=2 for 'സംസ്ഥാനമാണ്', got {entry_state.df}")

    def test_4_disk_retrieval_of_positional_postings(self) -> None:
        """Test 4: Correct retrieval of positional postings from secondary storage.

        Verifies that postings are fetched from SQLite on disk, in sorted DocID order,
        and match ground-truth positions.
        """
        postings = self.storage.get_postings("കേരളം")
        # Postings must be sorted by DocID: DocID 1, DocID 2, DocID 3
        expected_postings = [(1, [1, 5]), (2, [4]), (3, [4])]
        self.assertEqual(postings, expected_postings)

        # Check DocID ordering
        doc_ids = [doc_id for doc_id, _ in postings]
        self.assertEqual(doc_ids, sorted(doc_ids))

        # Check search engine integration (which queries disk)
        res = self.search_engine.search_term("കേരളം")
        self.assertEqual(res.cf, 4)
        self.assertEqual(res.df, 3)
        self.assertEqual(len(res.matches), 3)
        self.assertEqual(res.matches[0]["doc_id"], 1)
        self.assertEqual(res.matches[0]["positions"], [1, 5])

    def test_5_phrase_search_using_positional_information(self) -> None:
        """Test 5: Correct phrase searching using positional information.

        Tests positional intersection:
        - Query: "ഇന്ത്യയുടെ തെക്കുപടിഞ്ഞാറൻ സംസ്ഥാനമാണ്"
          In Doc 3, tokens appear at positions [1, 2, 3] consecutively -> Match!
          In Doc 1, "ഇന്ത്യയുടെ" is at 2 and "സംസ്ഥാനമാണ്" is at 4, but "തെക്കുപടിഞ്ഞാറൻ"
          is absent -> No Match!

        - Query: "മനോഹരമായ സംസ്ഥാനമാണ്"
          In Doc 1, tokens appear at [3, 4] consecutively -> Match!
          In Doc 3, "സംസ്ഥാനമാണ്" is at 3, but "മനോഹരമായ" is absent -> No Match!
        """
        # Exact 3-word phrase matching Doc 3
        phrase_query_1 = "ഇന്ത്യയുടെ തെക്കുപടിഞ്ഞാറൻ സംസ്ഥാനമാണ്"
        res1 = self.search_engine.search_phrase(phrase_query_1)
        self.assertEqual(len(res1.matches), 1, "Phrase should match exactly 1 document")
        self.assertEqual(res1.matches[0]["doc_id"], 3)
        self.assertEqual(res1.matches[0]["start_positions"], [1])

        # Exact 2-word phrase matching Doc 1
        phrase_query_2 = "മനോഹരമായ സംസ്ഥാനമാണ്"
        res2 = self.search_engine.search_phrase(phrase_query_2)
        self.assertEqual(len(res2.matches), 1, "Phrase should match exactly 1 document")
        self.assertEqual(res2.matches[0]["doc_id"], 1)
        self.assertEqual(res2.matches[0]["start_positions"], [3])

        # Non-consecutive words should NOT match
        # "ഇന്ത്യയുടെ സംസ്ഥാനമാണ്" in Doc 1 appears at pos 2 and 4 (gap of 1 token)
        non_consecutive = "ഇന്ത്യയുടെ സംസ്ഥാനമാണ്"
        res3 = self.search_engine.search_phrase(non_consecutive)
        self.assertEqual(
            len(res3.matches), 0, "Non-consecutive words must not match as exact phrase"
        )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    unittest.main()
