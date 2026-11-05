from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PipelineTest(unittest.TestCase):
    def test_pipeline_builds_valid_star_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            test_root = Path(temporary) / "project"
            copytree(
                PROJECT_ROOT,
                test_root,
                ignore=lambda directory, files: {
                    item
                    for item in files
                    if item.endswith(".db")
                    or item == "__pycache__"
                },
            )
            subprocess.run(
                [sys.executable, str(test_root / "pipeline" / "run_pipeline.py"), "--root", str(test_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, str(test_root / "pipeline" / "run_pipeline.py"), "--root", str(test_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            database = sqlite3.connect(test_root / "data" / "warehouse" / "aurora_retail.db")
            try:
                fact_count = database.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
                month_count = database.execute("SELECT COUNT(*) FROM dim_month").fetchone()[0]
                orphan_count = database.execute(
                    """
                    SELECT COUNT(*)
                    FROM fact_sales f
                    LEFT JOIN dim_customer c ON c.customer_key = f.customer_key
                    WHERE c.customer_key IS NULL
                    """
                ).fetchone()[0]
                self.assertGreater(fact_count, 50_000)
                self.assertEqual(month_count, 22)
                self.assertEqual(orphan_count, 0)
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
