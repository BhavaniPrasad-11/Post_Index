"""Malayalam Positional Inverted Index Construction Engine.

Coordinates the end-to-end indexing pipeline:
1. Streaming extraction of Wikipedia articles (excluding redirects & non-article namespaces).
2. Malayalam Unicode NFC normalization and cleaning.
3. Unicode-aware tokenization with 1-based sequential position assignment.
4. Construction of positional postings lists: Term -> [(DocID, [pos1, pos2, ...])].
5. Collection Frequency (CF) and Document Frequency (DF) computation.
6. Persistent storage of postings lists in secondary storage (SQLite) via batched writes.
7. Maintenance of the vocabulary / dictionary in main memory (RAM) and serialization to JSON.
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
try:
    from src.dictionary import InvertedIndexDictionary
    from src.storage_manager import StorageManager
    from src.tokenizer import MalayalamTokenizer
    from src.xml_parser import WikipediaXMLParser
except ImportError:
    from dictionary import InvertedIndexDictionary
    from storage_manager import StorageManager
    from tokenizer import MalayalamTokenizer
    from xml_parser import WikipediaXMLParser


class PositionalIndexer:
    """Core engine for building the Malayalam Positional Inverted Index."""

    def __init__(
        self,
        dump_path: Path = config.DUMP_PATH,
        db_path: Path = config.POSTINGS_DB_PATH,
        dict_path: Path = config.DICTIONARY_FILE_PATH,
        batch_size: int = config.BATCH_SIZE,
    ) -> None:
        self.dump_path = Path(dump_path)
        self.db_path = Path(db_path)
        self.dict_path = Path(dict_path)
        self.batch_size = batch_size

        self.tokenizer = MalayalamTokenizer()
        self.storage_manager = StorageManager(self.db_path)
        self.dictionary = InvertedIndexDictionary()
        self.xml_parser = WikipediaXMLParser(self.dump_path)

    def build_index(
        self,
        max_docs: Optional[int] = config.DEFAULT_MAX_DOCS,
        drop_existing: bool = True,
    ) -> Dict[str, Any]:
        """Construct the positional inverted index from the Wikipedia XML dump.

        Args:
            max_docs: Maximum number of articles to process (None for complete dump).
            drop_existing: Whether to clear existing index tables before indexing.

        Returns:
            Dictionary containing build metrics and collection statistics.
        """
        start_time = time.time()
        print(f"[INFO] Initializing Positional Inverted Index construction...")
        print(f"[INFO] Dataset path: {self.dump_path}")
        print(f"[INFO] Postings DB: {self.db_path}")
        print(f"[INFO] Dictionary JSON: {self.dict_path}")
        print(f"[INFO] Document batch size: {self.batch_size}")
        if max_docs is not None:
            print(f"[INFO] Max documents limit: {max_docs}")
        else:
            print(f"[INFO] Max documents: ALL available articles in dump")

        # Initialize SQLite database schema
        self.storage_manager.initialize_schema(drop_existing=drop_existing)

        # Buffers for batched disk writes
        doc_batch: List[Tuple[int, int, str, str, int]] = []
        postings_batch: List[Tuple[str, int, str]] = []

        total_docs = 0
        total_tokens = 0
        processed_postings = 0

        print("[INFO] Starting streaming article processing...")

        for article in self.xml_parser.stream_articles(max_docs=max_docs):
            total_docs += 1

            # Tokenize cleaned text and obtain 1-based sequential token positions
            token_positions = self.tokenizer.tokenize_with_positions(article.cleaned_text)
            doc_token_count = len(token_positions)
            total_tokens += doc_token_count

            # Record document metadata
            doc_batch.append(
                (
                    article.doc_id,
                    article.wiki_id,
                    article.title,
                    article.url,
                    doc_token_count,
                )
            )

            # Map term -> list of positions in this document
            # Positions are naturally ascending because tokens are processed in sequence
            doc_term_positions: Dict[str, List[int]] = defaultdict(list)
            for term, pos in token_positions:
                doc_term_positions[term].append(pos)

            # Update in-memory dictionary & stage postings for disk write
            for term, positions in doc_term_positions.items():
                # In-memory vocabulary update (CF and DF)
                self.dictionary.add_term_doc_stats(term, len(positions))

                # Stage posting row: (term, doc_id, JSON string of positions)
                # Store positions in ascending order
                postings_batch.append((term, article.doc_id, json.dumps(positions)))
                processed_postings += 1

            # Batched flush to secondary storage (SQLite)
            if len(doc_batch) >= self.batch_size:
                self.storage_manager.save_documents_batch(doc_batch)
                self.storage_manager.save_postings_batch(postings_batch)
                doc_batch.clear()
                postings_batch.clear()

                elapsed_so_far = time.time() - start_time
                docs_per_sec = total_docs / elapsed_so_far if elapsed_so_far > 0 else 0
                print(
                    f"[PROGRESS] Indexed {total_docs:,} documents | "
                    f"{total_tokens:,} tokens | "
                    f"{self.dictionary.size():,} unique terms | "
                    f"{docs_per_sec:.1f} docs/sec"
                )

        # Flush any remaining items in batches
        if doc_batch:
            self.storage_manager.save_documents_batch(doc_batch)
            doc_batch.clear()
        if postings_batch:
            self.storage_manager.save_postings_batch(postings_batch)
            postings_batch.clear()

        # Build B-tree indices on SQLite postings table for fast disk retrieval
        self.storage_manager.create_indices()

        # Persist in-memory vocabulary to JSON file on secondary storage
        self.dictionary.save_to_json(self.dict_path)

        # Save metadata to database
        indexing_time = round(time.time() - start_time, 2)
        self.storage_manager.set_metadata("total_documents", str(total_docs))
        self.storage_manager.set_metadata("total_tokens", str(total_tokens))
        self.storage_manager.set_metadata("vocabulary_size", str(self.dictionary.size()))
        self.storage_manager.set_metadata("total_postings", str(processed_postings))
        self.storage_manager.set_metadata("indexing_time_seconds", str(indexing_time))

        db_size_bytes = self.storage_manager.get_database_size_bytes()
        dict_size_bytes = self.dict_path.stat().st_size if self.dict_path.exists() else 0

        summary = {
            "total_documents": total_docs,
            "total_tokens": total_tokens,
            "vocabulary_size": self.dictionary.size(),
            "total_postings": processed_postings,
            "database_size_bytes": db_size_bytes,
            "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "dictionary_size_bytes": dict_size_bytes,
            "dictionary_size_mb": round(dict_size_bytes / (1024 * 1024), 2),
            "indexing_time_seconds": indexing_time,
        }

        print("\n" + "=" * 60)
        print(" Malayalam Positional Inverted Index Build Completed")
        print("=" * 60)
        print(f" Total Documents Indexed: {total_docs:,}")
        print(f" Total Tokens Processed:  {total_tokens:,}")
        print(f" Unique Terms in RAM:     {self.dictionary.size():,}")
        print(f" Total Postings on Disk:  {processed_postings:,}")
        print(f" Postings DB Size:        {summary['database_size_mb']} MB")
        print(f" Dictionary Size:         {summary['dictionary_size_mb']} MB")
        print(f" Total Indexing Time:     {indexing_time} seconds")
        print("=" * 60)

        return summary
