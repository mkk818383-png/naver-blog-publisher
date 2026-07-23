from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.compile import convert_md_to_html


ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "scripts" / "compile.py"
TEMPLATE = ROOT / "templates" / "post_template.html"


class CompileTests(unittest.TestCase):
    def test_markdown_line_breaks_become_independent_blocks_for_editor_paste(self) -> None:
        markdown = "# 제목\n\n첫 줄\n둘째 줄\n\n셋째 문단\n넷째 줄\n"

        html = convert_md_to_html(markdown)

        self.assertIn("<div>첫 줄</div>", html, "each Markdown line must be a paste-preserving block")
        self.assertIn("<div>둘째 줄</div>", html, "each Markdown line must be a paste-preserving block")
        self.assertNotIn("<p>첫 줄<br>둘째 줄</p>", html, "embedded br tags are flattened by SmartEditor paste")

    def test_markdown_blank_lines_become_explicit_paste_spacing(self) -> None:
        markdown = "# 제목\n\n첫 문단\n\n둘째 문단\n"

        html = convert_md_to_html(markdown)

        self.assertIn(
            "<div>첫 문단</div>\n\n<div>&nbsp;</div>\n\n<div>&nbsp;</div>\n\n<div>둘째 문단</div>",
            html,
        )

    def test_three_digit_media_placeholders_render_one_figure_and_caption_each(self) -> None:
        markdown = (
            "# 제목\n\n"
            "## 본문\n\n"
            "![[사진 001: 첫 사진]]\n\n"
            "![[동영상 002: 둘째 영상]]\n\n"
            "- 하나\n"
            "- 둘\n"
        )

        html = convert_md_to_html(markdown)

        self.assertEqual(html.count("<figure>"), 2)
        self.assertIn("📷 [사진 001] 첫 사진", html)
        self.assertIn("🎥 [동영상 002] 둘째 영상", html)
        self.assertEqual(html.count("<figcaption>"), 2)
        self.assertIn("<h1>제목</h1>", html)
        self.assertIn("<h2>본문</h2>", html)
        self.assertIn("<ul>\n    <li>하나</li>\n    <li>둘</li>\n</ul>", html)

    def test_cli_writes_template_output_and_reports_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "post.html"
            result = subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    str(ROOT / "tests" / "fixtures" / "valid_9_sections.md"),
                    str(TEMPLATE),
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Success: Compiled {output}", result.stdout)
            self.assertIn("<!DOCTYPE html>", output.read_text(encoding="utf-8"))

    def test_cli_uses_markdown_title_in_html_title_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            markdown = root / "post.md"
            output = root / "post.html"
            markdown.write_text("# 가덕도 대형카페 그랜드하브\n\n메인 키워드: 가덕도 대형카페\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(COMPILER), str(markdown), str(TEMPLATE), str(output)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertIn("<title>가덕도 대형카페 그랜드하브</title>", html)
            self.assertIn("메인 키워드: 가덕도 대형카페", html)

    def test_cli_rejects_missing_markdown_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing.html"
            result = subprocess.run(
                [sys.executable, str(COMPILER), str(Path(directory) / "missing.md"), str(TEMPLATE), str(output)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stderr)
            self.assertFalse(output.exists())

    def test_cli_rejects_missing_template_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing-template.html"
            result = subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    str(ROOT / "tests" / "fixtures" / "valid_9_sections.md"),
                    str(Path(directory) / "missing-template.html"),
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Error:", result.stderr)
            self.assertFalse(output.exists())
