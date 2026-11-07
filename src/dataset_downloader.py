"""Malayalam Wikipedia Dump Downloader.

Downloads the official Malayalam Wikipedia XML article dump from Wikimedia:
https://dumps.wikimedia.org/mlwiki/latest/mlwiki-latest-pages-articles.xml.bz2

Features:
- Free disk space check prior to download.
- Content-Length verification and resume/skip if already complete.
- Streaming chunk download with progress visualization.
- Collection metadata recording (source, date, size).
"""

import json
import os
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config


class DatasetDownloader:
    """Manages acquisition and verification of the Malayalam Wikipedia dump."""

    def __init__(
        self,
        dump_url: str = config.WIKIPEDIA_DUMP_URL,
        target_path: Path = config.DUMP_PATH,
        metadata_path: Path = config.COLLECTION_METADATA_FILE,
    ) -> None:
        self.dump_url = dump_url
        self.target_path = Path(target_path)
        self.metadata_path = Path(metadata_path)
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def check_disk_space(self, required_bytes: int = 1024 * 1024 * 500) -> bool:
        """Verify that sufficient disk space exists in target drive (at least 500 MB).

        Args:
            required_bytes: Minimum bytes required (default 500 MB).

        Returns:
            True if sufficient space exists.
        """
        stat = shutil.disk_usage(self.target_path.parent)
        return stat.free >= required_bytes

    def get_remote_file_size(self) -> int:
        """Fetch remote file size via HTTP HEAD request.

        Returns:
            File size in bytes, or 0 if indeterminate.
        """
        headers = {"User-Agent": "MalayalamPositionalIndexer/1.0 (IR Assignment; Academic Use)"}
        req = urllib.request.Request(self.dump_url, headers=headers, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                length = resp.headers.get("Content-Length")
                return int(length) if length else 0
        except Exception as e:
            print(f"[WARNING] Could not determine remote file size: {e}")
            return 0

    def download(self, force: bool = False) -> Path:
        """Download the Malayalam Wikipedia dump file.

        Args:
            force: If True, re-download even if target file already exists.

        Returns:
            Path to the downloaded file.
        """
        remote_size = self.get_remote_file_size()
        remote_size_mb = remote_size / (1024 * 1024) if remote_size else 0

        # Check existing file
        if self.target_path.exists() and not force:
            local_size = self.target_path.stat().st_size
            local_size_mb = local_size / (1024 * 1024)
            if remote_size > 0 and local_size == remote_size:
                print(
                    f"[INFO] Malayalam Wikipedia dump already downloaded: {self.target_path} "
                    f"({local_size_mb:.2f} MB). Skipping download."
                )
                self._save_metadata(remote_size, local_size, already_exists=True)
                return self.target_path
            elif remote_size == 0 and local_size > 50 * 1024 * 1024:
                print(
                    f"[INFO] Existing dump found: {self.target_path} ({local_size_mb:.2f} MB)."
                )
                self._save_metadata(remote_size, local_size, already_exists=True)
                return self.target_path

        # Disk space check
        needed_space = max(remote_size, 300 * 1024 * 1024)
        if not self.check_disk_space(needed_space):
            stat = shutil.disk_usage(self.target_path.parent)
            raise OSError(
                f"Insufficient disk space. Free: {stat.free / (1024*1024):.2f} MB, "
                f"Required: {needed_space / (1024*1024):.2f} MB"
            )

        print(f"[INFO] Starting download of Malayalam Wikipedia dump...")
        print(f"[INFO] Source URL: {self.dump_url}")
        print(f"[INFO] Expected size: {remote_size_mb:.2f} MB")
        print(f"[INFO] Destination: {self.target_path}")

        temp_target = self.target_path.with_suffix(".tmp")
        headers = {"User-Agent": "MalayalamPositionalIndexer/1.0 (IR Assignment; Academic Use)"}
        req = urllib.request.Request(self.dump_url, headers=headers)

        start_time = time.time()
        chunk_size = 1024 * 256  # 256 KB
        downloaded = 0

        with urllib.request.urlopen(req, timeout=30) as resp, open(temp_target, "wb") as f_out:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f_out.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                speed_mb = (downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                pct = (downloaded / remote_size * 100) if remote_size > 0 else 0
                sys.stdout.write(
                    f"\r[DOWNLOAD] {downloaded / (1024 * 1024):.2f} MB / "
                    f"{remote_size_mb:.2f} MB [{pct:.1f}%] - {speed_mb:.2f} MB/s"
                )
                sys.stdout.flush()

        print()
        if temp_target.exists():
            temp_target.replace(self.target_path)

        final_size = self.target_path.stat().st_size
        elapsed = time.time() - start_time
        print(
            f"[SUCCESS] Download completed in {elapsed:.1f}s ({final_size / (1024*1024):.2f} MB)."
        )

        self._save_metadata(remote_size, final_size, already_exists=False)
        return self.target_path

    def _save_metadata(
        self, expected_size: int, actual_size: int, already_exists: bool
    ) -> None:
        """Record dataset provenance, timestamp, and size to JSON file."""
        metadata: Dict[str, Any] = {
            "source_url": self.dump_url,
            "filename": self.target_path.name,
            "local_path": f"data/{self.target_path.name}",
            "file_size_bytes": actual_size,
            "file_size_mb": round(actual_size / (1024 * 1024), 2),
            "expected_size_bytes": expected_size,
            "recorded_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ready",
            "already_existed": already_exists,
        }
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Dataset metadata saved to {self.metadata_path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    downloader = DatasetDownloader()
    downloader.download()
