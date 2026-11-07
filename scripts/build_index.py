"""Build Index Script.

Command-line entry point to build the Malayalam Positional Inverted Index
from the Wikipedia XML dump.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root in sys.path
THIS_DIR = Path(__file__).resolve().parent
for p in (THIS_DIR, THIS_DIR.parent, THIS_DIR.parent.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import config
try:
    from src.positional_indexer import PositionalIndexer
    from src.statistics import CollectionStatistics
except ImportError:
    from positional_indexer import PositionalIndexer
    from statistics import CollectionStatistics


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Build Malayalam Positional Inverted Index from Wikipedia XML Dump."
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=None,
        help="Maximum number of Wikipedia articles to index (omit to index all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.BATCH_SIZE,
        help=f"Batch size for database insertions (default: {config.BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dump-path",
        type=str,
        default=str(config.DUMP_PATH),
        help=f"Path to Wikipedia XML/BZ2 dump (default: {config.DUMP_PATH}).",
    )
    args = parser.parse_args()

    indexer = PositionalIndexer(
        dump_path=Path(args.dump_path),
        batch_size=args.batch_size,
    )

    summary = indexer.build_index(max_docs=args.max_docs)

    # Generate and save collection statistics
    stats_engine = CollectionStatistics()
    stats_engine.save_report()

    print("\n[SUCCESS] Index build and statistics generation completed successfully.")


if __name__ == "__main__":
    main()
