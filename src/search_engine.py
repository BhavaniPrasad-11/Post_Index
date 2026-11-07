"""Malayalam Positional Search Engine.

Supports:
1. Single Term Search (with CF, DF, and on-disk positional postings retrieval).
2. Exact Phrase Search (multi-word positional intersection using token offsets).
3. Rare Terms Identification and detailed positional inspection.

Demonstrates the core IR concept: The vocabulary resides in RAM for O(1) term
lookup, while postings lists are retrieved on-demand from secondary storage.
"""

import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
try:
    from src.dictionary import InvertedIndexDictionary, TermEntry
    from src.storage_manager import StorageManager
    from src.tokenizer import MalayalamTokenizer
except ImportError:
    from dictionary import InvertedIndexDictionary, TermEntry
    from storage_manager import StorageManager
    from tokenizer import MalayalamTokenizer


class SearchResult:
    """Encapsulates the result of a single-term or phrase search."""

    def __init__(
        self,
        query: str,
        query_type: str,
        cf: Optional[int] = None,
        df: Optional[int] = None,
        matches: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.query = query
        self.query_type = query_type
        self.cf = cf
        self.df = df
        self.matches = matches or []

    def __repr__(self) -> str:
        return f"<SearchResult query={self.query!r} matches={len(self.matches)}>"


class MalayalamSearchEngine:
    """Search engine utilizing in-memory vocabulary and disk-based positional postings."""

    def __init__(
        self,
        db_path: Path = config.POSTINGS_DB_PATH,
        dict_path: Path = config.DICTIONARY_FILE_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.dict_path = Path(dict_path)
        self.storage_manager = StorageManager(self.db_path)
        self.dictionary = InvertedIndexDictionary()
        self.tokenizer = MalayalamTokenizer()
        self._is_initialized = False

    def initialize(self) -> None:
        """Load in-memory vocabulary from secondary storage into RAM."""
        if not self._is_initialized:
            print("[INFO] Initializing Search Engine...")
            self.dictionary.load_from_json(self.dict_path)
            self._is_initialized = True
            print(
                f"[INFO] Search Engine ready. In-memory vocabulary: "
                f"{self.dictionary.size():,} unique terms."
            )

    def search_term(self, raw_term: str) -> SearchResult:
        """Search for a single Malayalam term.

        Step 1: Normalize query term.
        Step 2: Check term in in-memory vocabulary (O(1) in RAM).
        Step 3: If found, fetch CF & DF from RAM, then retrieve postings from disk (SQLite).
        Step 4: Fetch document titles from database and return results.

        Args:
            raw_term: Input query word in Malayalam.

        Returns:
            SearchResult containing CF, DF, and positional postings.
        """
        if not self._is_initialized:
            self.initialize()

        # Normalize term: NFC and lowercase
        term = unicodedata.normalize("NFC", raw_term.strip().lower())
        tokens = self.tokenizer.tokenize(term)
        if not tokens:
            return SearchResult(query=raw_term, query_type="term", cf=0, df=0, matches=[])
        term = tokens[0]

        # Check in-memory vocabulary
        entry: Optional[TermEntry] = self.dictionary.get(term)
        if entry is None:
            return SearchResult(query=term, query_type="term", cf=0, df=0, matches=[])

        # Term exists: retrieve complete positional postings list from disk
        postings = self.storage_manager.get_postings(term)

        # Batch fetch document titles
        doc_ids = [doc_id for doc_id, _ in postings]
        docs_meta = self.storage_manager.get_documents_batch(doc_ids)

        matches: List[Dict[str, Any]] = []
        for doc_id, positions in postings:
            meta = docs_meta.get(doc_id, {})
            matches.append(
                {
                    "doc_id": doc_id,
                    "title": meta.get("title", f"Document #{doc_id}"),
                    "url": meta.get("url", ""),
                    "positions": positions,
                    "frequency_in_doc": len(positions),
                }
            )

        return SearchResult(
            query=term,
            query_type="term",
            cf=entry.cf,
            df=entry.df,
            matches=matches,
        )

    def search_phrase(self, raw_phrase: str) -> SearchResult:
        """Search for an exact Malayalam phrase using positional intersection.

        Uses token positions to verify that all phrase terms appear consecutively
        in the exact order specified:
            pos(term_{i+1}) == pos(term_i) + 1

        Args:
            raw_phrase: Malayalam multi-word phrase query.

        Returns:
            SearchResult containing matching documents and phrase starting positions.
        """
        if not self._is_initialized:
            self.initialize()

        # Tokenize phrase
        tokens = self.tokenizer.tokenize(raw_phrase)
        if not tokens:
            return SearchResult(query=raw_phrase, query_type="phrase", matches=[])

        if len(tokens) == 1:
            return self.search_term(tokens[0])

        # Step 1: Verify all tokens exist in the in-memory vocabulary
        for token in tokens:
            if not self.dictionary.contains(token):
                # If any token is missing from vocabulary, phrase match is impossible
                return SearchResult(query=raw_phrase, query_type="phrase", matches=[])

        # Step 2: Retrieve postings lists for all terms from disk (secondary storage)
        term_postings: List[Dict[int, List[int]]] = []
        for token in tokens:
            raw_posts = self.storage_manager.get_postings(token)
            # Map doc_id -> sorted positions list
            term_postings.append({doc_id: positions for doc_id, positions in raw_posts})

        # Step 3: Find common documents containing all terms
        common_doc_ids = set(term_postings[0].keys())
        for doc_map in term_postings[1:]:
            common_doc_ids.intersection_update(doc_map.keys())

        if not common_doc_ids:
            return SearchResult(query=raw_phrase, query_type="phrase", matches=[])

        # Step 4: Positional Intersection Algorithm
        # For each common document, check if positions satisfy consecutive sequence:
        # pos(token_k) == pos(token_0) + k
        matches: List[Dict[str, Any]] = []
        sorted_doc_ids = sorted(common_doc_ids)
        docs_meta = self.storage_manager.get_documents_batch(sorted_doc_ids)

        for doc_id in sorted_doc_ids:
            # Positions of first term
            p0_positions = term_postings[0][doc_id]
            phrase_start_positions: List[int] = []

            # Create position lookup sets for subsequent terms in this doc
            subsequent_pos_sets = [
                set(term_postings[k][doc_id]) for k in range(1, len(tokens))
            ]

            for p0 in p0_positions:
                match = True
                for offset, pos_set in enumerate(subsequent_pos_sets, start=1):
                    if (p0 + offset) not in pos_set:
                        match = False
                        break
                if match:
                    phrase_start_positions.append(p0)

            if phrase_start_positions:
                meta = docs_meta.get(doc_id, {})
                matches.append(
                    {
                        "doc_id": doc_id,
                        "title": meta.get("title", f"Document #{doc_id}"),
                        "url": meta.get("url", ""),
                        "start_positions": phrase_start_positions,
                        "match_count": len(phrase_start_positions),
                    }
                )

        return SearchResult(
            query=" ".join(tokens),
            query_type="phrase",
            df=len(matches),
            cf=sum(m["match_count"] for m in matches),
            matches=matches,
        )

    def get_rare_terms(self, limit: int = 10, max_df: int = 1) -> List[Dict[str, Any]]:
        """Identify rare terms based on low Document Frequency and retrieve disk postings.

        Args:
            limit: Number of rare terms to retrieve (default 10).
            max_df: Maximum DF threshold (default 1).

        Returns:
            List of dictionaries containing term, CF, DF, and postings with titles.
        """
        if not self._is_initialized:
            self.initialize()

        rare_term_entries = self.dictionary.get_rare_terms(limit=limit, max_df=max_df)
        results: List[Dict[str, Any]] = []

        for term, entry in rare_term_entries:
            postings = self.storage_manager.get_postings(term)
            doc_ids = [doc_id for doc_id, _ in postings]
            docs_meta = self.storage_manager.get_documents_batch(doc_ids)

            postings_formatted: List[Dict[str, Any]] = []
            for doc_id, positions in postings:
                meta = docs_meta.get(doc_id, {})
                postings_formatted.append(
                    {
                        "doc_id": doc_id,
                        "title": meta.get("title", f"Document #{doc_id}"),
                        "url": meta.get("url", ""),
                        "positions": positions,
                    }
                )

            results.append(
                {
                    "term": term,
                    "cf": entry.cf,
                    "df": entry.df,
                    "postings": postings_formatted,
                }
            )

        return results
