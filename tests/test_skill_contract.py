from __future__ import annotations

import unittest
from pathlib import Path

from scripts.run_skill_contract_check import check_skill


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_requires_title_research_sticker_and_no_vision_contracts(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        missing_title = skill.replace("keyword_report.json", "")
        missing_sticker = skill.replace("[외부]", "")
        missing_no_vision = skill.replace("view_image", "")

        self.assertTrue(any("keyword_report" in error for error in check_skill(missing_title)))
        self.assertTrue(any("[외부]" in error for error in check_skill(missing_sticker)))
        self.assertTrue(any("view_image" in error for error in check_skill(missing_no_vision)))
