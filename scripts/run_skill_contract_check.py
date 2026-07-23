#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/run_skill_contract_check.py SKILL.md
# 3. Or make executable and run:
#      chmod +x scripts/run_skill_contract_check.py && ./scripts/run_skill_contract_check.py SKILL.md
# ──────────────────

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

CONTENT_TYPES: Final = (
    "restaurant",
    "cafe",
    "accommodation",
    "experience",
    "beauty",
    "retail",
)
MODES: Final = ("model-draft", "publish-safe", "memo-only")
NON_COMPLETE_STATUSES: Final = ("not_run", "partial", "empty", "error", "stale")
REQUIRED_TEXT: Final = (
    "[업종]",
    "run.json",
    "source_pack.json",
    "image_index.json",
    "MODEL-DRAFT",
    "신뢰하지 않는 데이터",
    "프롬프트 인젝션",
    "원문 HTML",
    "validate_post.py",
    "compile.py",
    "수동 발행",
    "keyword_report.json",
    "search_rank",
    "rank_status",
    "[외부]",
    "[제목 및 키워드]",
    "스티커용 짧은 소제목",
    "view_image",
)
RESTAURANT_ONLY_HEADINGS: Final = ("밑반찬과 기본 상차림", "메인 메뉴와 먹는 방법")


@dataclass(frozen=True, slots=True)
class CheckResult:
    errors: tuple[str, ...]
    modes: tuple[str, ...]
    types: tuple[str, ...]

    def as_json(self) -> str:
        return json.dumps(
            {
                "errors": list(self.errors),
                "modes": list(self.modes),
                "ok": not self.errors,
                "types": list(self.types),
            },
            ensure_ascii=False,
            sort_keys=True,
        )


def parse_metadata(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("metadata must be a JSON object")
    metadata: dict[str, str] = {}
    for key in ("content_type", "research_status"):
        value = raw.get(key)
        if not isinstance(value, str):
            raise ValueError(f"metadata missing string {key}")
        metadata[key] = value
    return metadata


def check_skill(skill: str) -> list[str]:
    errors = [f"skill: missing {item}" for item in REQUIRED_TEXT if item not in skill]
    errors.extend(f"skill: missing content type {item}" for item in CONTENT_TYPES if item not in skill)
    errors.extend(f"skill: missing mode {item}" for item in MODES if item not in skill)
    for status in NON_COMPLETE_STATUSES:
        if status not in skill:
            errors.append(f"skill: missing fail-closed status {status}")
    for phrase in ("Source Pack", "이미지 인덱스", "검증", "내보내기"):
        if phrase not in skill:
            errors.append(f"skill: missing workflow gate {phrase}")
    if "자동 발행" in skill:
        errors.append("skill: automated publishing is forbidden")
    return errors


def check_precompile_gate(metadata: dict[str, str], post: str) -> list[str]:
    errors: list[str] = []
    content_type = metadata["content_type"]
    research_status = metadata["research_status"]
    if content_type not in CONTENT_TYPES:
        errors.append(f"metadata: unknown content_type {content_type}")
    if research_status != "complete":
        errors.append(f"metadata: research_status {research_status} blocks writing and compilation")
    if content_type == "cafe":
        for heading in RESTAURANT_ONLY_HEADINGS:
            if re.search(rf"^##\s+{re.escape(heading)}\s*$", post, re.MULTILINE):
                errors.append(f"post: cafe forbids restaurant-only heading {heading}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the v2 SKILL workflow contract before compilation.")
    parser.add_argument("skill", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--post", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        skill = args.skill.read_text(encoding="utf-8")
    except OSError as error:
        errors.append(f"input: cannot read skill: {error}")
        skill = ""
    errors.extend(check_skill(skill))

    match args.metadata, args.post:
        case None, None:
            pass
        case Path() as metadata_path, Path() as post_path:
            try:
                metadata = parse_metadata(metadata_path)
                post = post_path.read_text(encoding="utf-8")
            except (OSError, ValueError, json.JSONDecodeError) as error:
                errors.append(f"input: invalid precompile probe: {error}")
            else:
                errors.extend(check_precompile_gate(metadata, post))
        case _:
            errors.append("input: --metadata and --post must be supplied together")

    result = CheckResult(errors=tuple(errors), modes=MODES, types=CONTENT_TYPES)
    print(result.as_json())
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
