from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import fetch_competitors


VALID_URL = "https://blog.naver.com/daonlog/123456"
SMARTEDITOR_HTML = (
    '<meta property="og:title" content="테스트 글">\n'
    '<div class="se-main-container">\n'
    '  <div class="se-module se-module-text">첫 번째 문단입니다</div>\n'
    "</div>\n"
)


class FetchCompetitorsTests(unittest.TestCase):
    def test_run_skips_empty_fetch_and_does_not_create_research_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw_crawled.json"
            with patch.object(fetch_competitors, "fetch_blog_html", return_value=None):
                result = fetch_competitors.run(urls=[VALID_URL], output=str(output))

            self.assertEqual(result, [])
            self.assertFalse(output.exists())

    def test_run_removes_stale_research_output_when_no_usable_posts_remain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw_crawled.json"
            output.write_text('[{"stale": true}]', encoding="utf-8")
            with patch.object(fetch_competitors, "fetch_blog_html", return_value=None):
                result = fetch_competitors.run(urls=[VALID_URL], output=str(output))

            self.assertEqual(result, [])
            self.assertFalse(output.exists())

    def test_run_persists_only_usable_posts_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw_crawled.json"
            with patch.object(fetch_competitors, "fetch_blog_html", return_value=SMARTEDITOR_HTML):
                result = fetch_competitors.run(query="테스트 업체", urls=[VALID_URL], output=str(output))

            self.assertEqual(len(result), 1)
            self.assertTrue(output.exists())
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["source_url"], VALID_URL)
            self.assertEqual(saved[0]["search_rank"], 1)
            self.assertEqual(saved[0]["rank_status"], "observed")
            self.assertEqual(saved[0]["parser_used"], "smarteditor")
            self.assertEqual(saved[0]["query"], "테스트 업체")
            self.assertRegex(saved[0]["retrieved_at"], r"^\d{4}-\d{2}-\d{2}T")
            self.assertEqual(len(saved[0]["content_sha256"]), 64)

    def test_run_preserves_last_complete_output_when_refresh_cannot_start(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw_crawled.json"
            output.write_text('[{"previous": true}]', encoding="utf-8")
            with (
                patch.object(fetch_competitors, "fetch_blog_html", return_value=SMARTEDITOR_HTML),
                patch.object(fetch_competitors.tempfile, "mkstemp", side_effect=OSError("disk full")),
            ):
                with self.assertRaises(OSError):
                    fetch_competitors.run(urls=[VALID_URL], output=str(output))

            self.assertEqual(output.read_text(encoding="utf-8"), '[{"previous": true}]')

    def test_cli_exits_nonzero_when_no_usable_posts_are_collected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "raw_crawled.json")
            argv = ["fetch_competitors.py", "--urls", VALID_URL, "--output", output]
            with patch.object(fetch_competitors, "run", return_value=[]), patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit) as raised:
                    fetch_competitors.main()

            self.assertEqual(raised.exception.code, 1)

    def test_cli_uses_distinct_exit_code_for_output_errors(self) -> None:
        argv = ["fetch_competitors.py", "--urls", VALID_URL, "--output", "raw_crawled.json"]
        with patch.object(fetch_competitors, "run", side_effect=OSError("disk full")), patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as raised:
                fetch_competitors.main()

        self.assertEqual(raised.exception.code, 2)
