"""Configuration settings for Malayalam Positional Inverted Index.

This module centralizes filesystem paths, Wikimedia dump URLs,
database schemas, and indexing hyperparameters.
Supports execution both from the project root and from within src/.
"""

import sys
from pathlib import Path

# Determine project root dynamically
_CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _CURRENT_DIR.parent if _CURRENT_DIR.name == "src" else _CURRENT_DIR

BASE_DIR = PROJECT_ROOT
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
INDEX_DIR = PROJECT_ROOT / "index"
OUTPUT_DIR = PROJECT_ROOT / "output"
TESTS_DIR = SRC_DIR / "tests" if (SRC_DIR / "tests").exists() else PROJECT_ROOT / "tests"
SCRIPTS_DIR = SRC_DIR / "scripts" if (SRC_DIR / "scripts").exists() else PROJECT_ROOT / "scripts"

# Dataset settings
WIKIPEDIA_DUMP_URL = "https://dumps.wikimedia.org/mlwiki/latest/mlwiki-latest-pages-articles.xml.bz2"
DUMP_FILENAME = "mlwiki-latest-pages-articles.xml.bz2"
DUMP_PATH = DATA_DIR / DUMP_FILENAME
COLLECTION_METADATA_FILE = DATA_DIR / "collection_info.json"

# Storage paths
POSTINGS_DB_PATH = INDEX_DIR / "postings.sqlite3"
DICTIONARY_FILE_PATH = INDEX_DIR / "dictionary.json"

# Output report paths
STATS_REPORT_PATH = OUTPUT_DIR / "collection_statistics.txt"
RARE_TERMS_REPORT_PATH = OUTPUT_DIR / "rare_terms.txt"
TEST_RESULTS_REPORT_PATH = OUTPUT_DIR / "test_results.txt"
QUERY_EXAMPLES_REPORT_PATH = OUTPUT_DIR / "query_examples.txt"
SAMPLE_INDEX_REPORT_PATH = OUTPUT_DIR / "sample_positional_index.txt"
INDEX_VALIDATION_REPORT_PATH = OUTPUT_DIR / "index_validation.txt"

# Indexing hyperparameters
# Commit postings to SQLite in batches of documents to bound RAM usage
BATCH_SIZE = 500

# Default limit of articles to index. Set to None to index the entire dump.
DEFAULT_MAX_DOCS = None

# Unicode and Normalization configuration
MALAYALAM_UNICODE_RANGE = (0x0D00, 0x0D7F)
ZWNJ = "\u200C"
ZWJ = "\u200D"

# Wikipedia base URL for Malayalam
WIKI_BASE_URL = "https://ml.wikipedia.org/wiki/"
