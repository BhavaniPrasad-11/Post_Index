"""Disk-Based Storage Manager for Malayalam Positional Postings.

Provides persistent SQLite-backed secondary storage for document metadata and
complete positional postings lists.

Architecture:
- In-Memory: Vocabulary (Dictionary) containing Term -> (CF, DF).
- Secondary Storage (Disk): SQLite database with 'postings' and 'documents' tables.
- Postings are stored in sorted DocID order with positions in strictly ascending order.
- Postings are fetched on-demand from disk during queries, never held entirely in RAM.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config


class StorageManager:
    """Manages SQLite persistent secondary storage for the positional index."""

    def __init__(self, db_path: Path = config.POSTINGS_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        """Get or initialize the persistent SQLite connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
            self._conn.execute("PRAGMA temp_store = MEMORY;")
            self._conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def initialize_schema(self, drop_existing: bool = False) -> None:
        """Initialize tables for documents, postings, and index metadata."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if drop_existing:
            cursor.execute("DROP TABLE IF EXISTS postings;")
            cursor.execute("DROP TABLE IF EXISTS documents;")
            cursor.execute("DROP TABLE IF EXISTS metadata;")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id INTEGER PRIMARY KEY,
                wiki_id INTEGER,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                token_count INTEGER NOT NULL
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS postings (
                term TEXT NOT NULL,
                doc_id INTEGER NOT NULL,
                positions TEXT NOT NULL
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        conn.commit()

    def create_indices(self) -> None:
        """Create B-tree indices on postings table.

        Crucial for fast disk retrieval: ensures postings for any given term
        are retrieved in sorted DocID order in O(log N) lookup time.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        print("[INFO] Creating database B-tree index on postings(term, doc_id ASC)...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_postings_term_doc ON postings(term, doc_id ASC);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_docs_wiki_id ON documents(wiki_id);"
        )
        conn.commit()
        print("[INFO] Database indexing complete.")

    def save_documents_batch(
        self, docs: List[Tuple[int, int, str, str, int]]
    ) -> None:
        """Save a batch of document records: (doc_id, wiki_id, title, url, token_count)."""
        if not docs:
            return
        conn = self.get_connection()
        conn.executemany(
            """
            INSERT OR REPLACE INTO documents (doc_id, wiki_id, title, url, token_count)
            VALUES (?, ?, ?, ?, ?);
            """,
            docs,
        )
        conn.commit()

    def save_postings_batch(
        self, postings_batch: List[Tuple[str, int, str]]
    ) -> None:
        """Save a batch of positional postings to disk.

        Args:
            postings_batch: List of (term, doc_id, positions_json_string).
        """
        if not postings_batch:
            return
        conn = self.get_connection()
        conn.executemany(
            """
            INSERT INTO postings (term, doc_id, positions)
            VALUES (?, ?, ?);
            """,
            postings_batch,
        )
        conn.commit()

    def get_postings(self, term: str) -> List[Tuple[int, List[int]]]:
        """Retrieve complete positional postings for a term from disk.

        Postings are returned in sorted DocID order with positions in ascending order.
        This queries secondary storage directly, ensuring postings are not kept in RAM.

        Args:
            term: Malayalam term.

        Returns:
            List of (doc_id, [pos1, pos2, ...]) tuples.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT doc_id, positions
            FROM postings
            WHERE term = ?
            ORDER BY doc_id ASC;
            """,
            (term,),
        )
        rows = cursor.fetchall()

        results: List[Tuple[int, List[int]]] = []
        for doc_id, pos_json in rows:
            positions = json.loads(pos_json)
            results.append((doc_id, positions))

        return results

    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata by doc_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT doc_id, wiki_id, title, url, token_count FROM documents WHERE doc_id = ?;",
            (doc_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "doc_id": row[0],
            "wiki_id": row[1],
            "title": row[2],
            "url": row[3],
            "token_count": row[4],
        }

    def get_documents_batch(self, doc_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Retrieve document metadata for a set of doc_ids efficiently."""
        if not doc_ids:
            return {}
        conn = self.get_connection()
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in doc_ids)
        query = f"SELECT doc_id, wiki_id, title, url, token_count FROM documents WHERE doc_id IN ({placeholders});"
        cursor.execute(query, doc_ids)
        results: Dict[int, Dict[str, Any]] = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                "doc_id": row[0],
                "wiki_id": row[1],
                "title": row[2],
                "url": row[3],
                "token_count": row[4],
            }
        return results

    def set_metadata(self, key: str, value: str) -> None:
        """Store metadata key-value pair."""
        conn = self.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?);",
            (key, value),
        )
        conn.commit()

    def get_metadata(self, key: str) -> Optional[str]:
        """Fetch metadata value for a key."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = ?;", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_database_size_bytes(self) -> int:
        """Get file size of the SQLite postings database on disk."""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def get_total_documents_count(self) -> int:
        """Get total number of documents in database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents;")
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_total_postings_count(self) -> int:
        """Get total number of postings entries in database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM postings;")
        row = cursor.fetchone()
        return row[0] if row else 0
