"""Collection Statistics and Analytics for Malayalam Positional Inverted Index.

Calculates and formats collection metrics including:
- Document count
- Total token occurrences
- Vocabulary size (unique terms in RAM)
- Total positional postings stored on secondary storage (disk)
- Database file size (SQLite)
- In-memory dictionary size
- Processing and build times
- Average document length
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
try:
    from src.dictionary import InvertedIndexDictionary
    from src.storage_manager import StorageManager
except ImportError:
    from dictionary import InvertedIndexDictionary
    from storage_manager import StorageManager


class CollectionStatistics:
    """Computes and formats collection-level metrics."""

    def __init__(
        self,
        db_path: Path = config.POSTINGS_DB_PATH,
        dict_path: Path = config.DICTIONARY_FILE_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.dict_path = Path(dict_path)
        self.storage_manager = StorageManager(self.db_path)
        self.dictionary = InvertedIndexDictionary()

    def compute_statistics(self) -> Dict[str, Any]:
        """Compute collection statistics from database and dictionary."""
        # Load dictionary if exists
        vocab_size = 0
        total_cf = 0
        if self.dict_path.exists():
            self.dictionary.load_from_json(self.dict_path)
            vocab_size = self.dictionary.size()
            for term in self.dictionary.get_all_terms():
                entry = self.dictionary.get(term)
                if entry:
                    total_cf += entry.cf

        total_docs = self.storage_manager.get_total_documents_count()
        total_postings = self.storage_manager.get_total_postings_count()
        db_size_bytes = self.storage_manager.get_database_size_bytes()
        dict_size_bytes = self.dict_path.stat().st_size if self.dict_path.exists() else 0

        # Retrieve saved build metadata if available
        indexing_time = self.storage_manager.get_metadata("indexing_time_seconds") or "N/A"
        recorded_tokens = self.storage_manager.get_metadata("total_tokens")
        total_tokens = int(recorded_tokens) if recorded_tokens else total_cf

        avg_doc_len = round(total_tokens / total_docs, 2) if total_docs > 0 else 0
        avg_postings_per_term = round(total_postings / vocab_size, 2) if vocab_size > 0 else 0

        stats = {
            "total_documents": total_docs,
            "total_tokens": total_tokens,
            "vocabulary_size": vocab_size,
            "total_postings": total_postings,
            "database_size_bytes": db_size_bytes,
            "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "dictionary_size_bytes": dict_size_bytes,
            "dictionary_size_mb": round(dict_size_bytes / (1024 * 1024), 2),
            "avg_document_length": avg_doc_len,
            "avg_postings_per_term": avg_postings_per_term,
            "indexing_time_seconds": indexing_time,
        }
        return stats

    def format_report(self) -> str:
        """Generate a formatted statistics report."""
        stats = self.compute_statistics()
        lines = [
            "=" * 70,
            " MALAYALAM POSITIONAL INVERTED INDEX — COLLECTION STATISTICS REPORT",
            "=" * 70,
            f" Dataset Source:             Malayalam Wikipedia (mlwiki-latest)",
            f" Number of Indexed Articles: {stats['total_documents']:,}",
            f" Total Number of Tokens:     {stats['total_tokens']:,}",
            f" Total Unique Terms (RAM):   {stats['vocabulary_size']:,}",
            f" Total Postings on Disk:     {stats['total_postings']:,}",
            f" Postings DB Size (Disk):    {stats['database_size_mb']} MB ({stats['database_size_bytes']:,} bytes)",
            f" Vocabulary Size (RAM/JSON): {stats['dictionary_size_mb']} MB ({stats['dictionary_size_bytes']:,} bytes)",
            f" Average Document Length:    {stats['avg_document_length']} tokens/article",
            f" Average Postings per Term:  {stats['avg_postings_per_term']} documents/term",
            f" Index Construction Time:    {stats['indexing_time_seconds']} seconds",
            "=" * 70,
            " ARCHITECTURAL SUMMARY:",
            " - Vocabulary / Dictionary:  Loaded in Main Memory (RAM) for O(1) lookups.",
            " - Positional Postings:      Persisted on Secondary Storage (SQLite B-tree).",
            " - Token Positions:          1-based sequential indices in original cleaned text.",
            " - Unicode Normalization:    Unicode NFC with full Malayalam character preservation.",
            "=" * 70,
        ]
        return "\n".join(lines)

    def save_report(self, output_path: Path = config.STATS_REPORT_PATH) -> None:
        """Write formatted statistics to output file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_text = self.format_report()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"[INFO] Collection statistics saved to {output_path}")
