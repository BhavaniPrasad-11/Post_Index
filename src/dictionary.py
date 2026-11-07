"""In-Memory Vocabulary (Dictionary) for Malayalam Positional Inverted Index.

Maintains the complete term vocabulary, Collection Frequency (CF),
and Document Frequency (DF) in main memory (RAM) during querying and indexing.
Persists to and loads from 'index/dictionary.json'.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config


class TermEntry(NamedTuple):
    """Metadata for a unique term in the in-memory vocabulary."""

    cf: int  # Collection Frequency: total occurrences across all documents
    df: int  # Document Frequency: number of distinct documents containing term


class InvertedIndexDictionary:
    """Manages the in-memory vocabulary and term statistics."""

    def __init__(self) -> None:
        # In-memory dictionary: term -> TermEntry(cf, df)
        self._entries: Dict[str, TermEntry] = {}

    def add_term_doc_stats(self, term: str, term_count_in_doc: int) -> None:
        """Update in-memory dictionary statistics for a term observed in a document.

        Args:
            term: Normalized Malayalam term.
            term_count_in_doc: Number of times term appeared in the current document.
        """
        existing = self._entries.get(term)
        if existing is None:
            self._entries[term] = TermEntry(cf=term_count_in_doc, df=1)
        else:
            self._entries[term] = TermEntry(
                cf=existing.cf + term_count_in_doc,
                df=existing.df + 1,
            )

    def contains(self, term: str) -> bool:
        """Check if term exists in vocabulary."""
        return term in self._entries

    def get(self, term: str) -> Optional[TermEntry]:
        """Look up term metadata (CF, DF) from main memory."""
        return self._entries.get(term)

    def size(self) -> int:
        """Return total number of unique terms in the vocabulary."""
        return len(self._entries)

    def get_all_terms(self) -> Iterator[str]:
        """Iterate over all terms in vocabulary."""
        return iter(self._entries.keys())

    def get_rare_terms(
        self,
        limit: int = 10,
        max_df: int = 1,
        min_char_length: int = 4,
        require_malayalam: bool = True,
    ) -> List[Tuple[str, TermEntry]]:
        """Identify rare terms based on low Document Frequency.

        Filters for authentic Malayalam terms rather than punctuation artifacts
        or noise.

        Args:
            limit: Number of rare terms to return.
            max_df: Maximum DF threshold (default 1).
            min_char_length: Minimum character length.
            require_malayalam: Ensure the word contains Malayalam Unicode characters.

        Returns:
            List of (term, TermEntry) tuples.
        """
        rare: List[Tuple[str, TermEntry]] = []

        for term, entry in self._entries.items():
            if entry.df <= max_df:
                if len(term) < min_char_length:
                    continue
                if require_malayalam:
                    has_ml = any(
                        config.MALAYALAM_UNICODE_RANGE[0]
                        <= ord(ch)
                        <= config.MALAYALAM_UNICODE_RANGE[1]
                        for ch in term
                    )
                    if not has_ml:
                        continue
                rare.append((term, entry))
                if len(rare) >= limit:
                    break

        return rare

    def save_to_json(self, path: Path = config.DICTIONARY_FILE_PATH) -> None:
        """Serialize in-memory vocabulary to JSON file on disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {term: {"cf": entry.cf, "df": entry.df} for term, entry in self._entries.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] In-memory dictionary saved to {path} ({len(self._entries)} terms).")

    def load_from_json(self, path: Path = config.DICTIONARY_FILE_PATH) -> None:
        """Load vocabulary from disk into RAM."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dictionary file not found at {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._entries = {
            term: TermEntry(cf=val["cf"], df=val["df"])
            for term, val in data.items()
        }
        print(
            f"[INFO] Successfully loaded {len(self._entries)} terms into in-memory dictionary."
        )

    def get_memory_footprint_bytes(self) -> int:
        """Estimate in-memory size of dictionary in RAM."""
        import sys
        total_size = sys.getsizeof(self._entries)
        for term, entry in self._entries.items():
            total_size += sys.getsizeof(term) + sys.getsizeof(entry)
        return total_size
