from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTS = tuple(p for p in (ROOT / "posts" / "grand-habor", ROOT / "posts" / "sancheongri56", ROOT / "posts" / "카페쿠지") if p.exists())


class PostMetadataTests(unittest.TestCase):
    def test_each_post_and_html_expose_title_and_keyword_block(self) -> None:
        for folder in POSTS:
            with self.subTest(folder=folder.name):
                markdown = (folder / "post.md").read_text(encoding="utf-8")
                html = (folder / "post.html").read_text(encoding="utf-8")
                title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
                self.assertIsNotNone(title_match)
                title = title_match.group(1) if title_match else ""
                self.assertIn("[제목 및 키워드]", markdown)
                self.assertIn("메인 키워드:", markdown)
                self.assertIn("서브 키워드:", markdown)
                self.assertIn(f"<title>{title}</title>", html)
                self.assertIn("메인 키워드:", html)
                self.assertIn("서브 키워드:", html)
