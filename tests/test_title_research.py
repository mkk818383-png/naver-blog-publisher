from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "title_research.py"


class TitleResearchTests(unittest.TestCase):
    def test_cli_writes_keyword_report_and_ten_titles_from_five_ranked_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "raw.json"
            post = root / "post.md"
            output = root / "report.json"
            research.write_text(
                json.dumps(
                    [
                        {
                            "search_rank": rank,
                            "rank_status": "observed",
                            "title": f"가덕도 대형카페 그랜드하브 오션뷰 {rank}",
                            "source_url": f"https://example.test/{rank}",
                            "paragraphs": ["스카이워크와 오션뷰를 함께 본 후기, 베이커리 주차 드라이브"],
                        }
                        for rank in range(1, 6)
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            post.write_text(
                "# 가덕도 카페 그랜드하브\n\n오렌지 아메리카노와 하브슈페너를 주문했어요.\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--primary-keyword",
                    "가덕도 대형카페",
                    "--venue",
                    "그랜드하브",
                    "--research",
                    str(research),
                    "--post",
                    str(post),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["source_count"], 5)
            self.assertEqual(report["research_status"], "complete")
            self.assertEqual(len(report["secondary_keywords"]), 6)
            self.assertNotIn("카페", [item["keyword"] for item in report["secondary_keywords"]])
            self.assertEqual(len(report["titles"]), 10)
            self.assertEqual([item["rank"] for item in report["titles"]], list(range(1, 11)))
            self.assertTrue(all("가덕도 대형카페" in item["title"] for item in report["titles"]))
            self.assertTrue(all(item["title"].count("그랜드하브") <= 1 for item in report["titles"]))
            self.assertTrue(all(item["reason"].startswith(("KW-", "TG-")) for item in report["titles"]))

    def test_cli_blocks_fewer_than_five_ranked_sources_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research = root / "raw.json"
            post = root / "post.md"
            output = root / "report.json"
            research.write_text(
                json.dumps(
                    [{"title": "부분 결과", "source_url": "https://example.test/1", "paragraphs": ["본문"]}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            post.write_text("# 제목\n\n본문\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--primary-keyword",
                    "명지 카페",
                    "--venue",
                    "쿠지",
                    "--research",
                    str(research),
                    "--post",
                    str(post),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("RESEARCH_PARTIAL", result.stderr)
            self.assertFalse(output.exists())
