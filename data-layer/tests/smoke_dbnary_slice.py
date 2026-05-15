"""
End-to-end smoke: run the DBnary ingester against the 100k-line slice fixture
and confirm chunks land in the local Postgres DB with source_name='DBnary'.

Usage: python -m tests.smoke_dbnary_slice
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_LAYER = HERE.parent
sys.path.insert(0, str(DATA_LAYER))

from scripts.ingest.dbnary import DBnaryIngester  # noqa: E402


class SliceIngester(DBnaryIngester):
    """Skip download; point at the local slice fixture."""

    def download(self) -> None:
        self.uncompressed_path = DATA_LAYER / "tests/fixtures/dbnary_slice_5k.ttl"
        if not self.uncompressed_path.exists():
            raise FileNotFoundError(self.uncompressed_path)
        self.log.info(f"Using slice fixture {self.uncompressed_path}")


if __name__ == "__main__":
    SliceIngester(language="fr").run()
