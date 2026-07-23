#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# ─── How to run ───
# uv run scripts/check_docs_consistency.py README.md README.ko.md docs/superpowers/specs/2026-07-12-daonlog-skill-redesign.md

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final


REQUIRED_TERMS: Final[tuple[str, ...]] = (
    "restaurant", "cafe", "accommodation", "experience", "beauty", "retail",
    "model-draft", "publish-safe", "memo-only",
    "not_run", "complete", "partial", "empty", "error", "stale",
    "run.json", "source_pack.json", "image_index.json", "post.md", "titles.json", "post.html",
    "사진 001", "001", "002", "003",
    "--metadata", "--source-pack", "--image-index", "--disclosure",
    "sponsored", "self-paid", "제목 또는 도입", "최종 고지 구역",
    "검증기는 기존 줄바꿈 검사를 마지막에 실행", "not_run 상태는 완료된 리서치가 아니다",
    "수동으로 발행", "내보내기",
)
FORBIDDEN_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    ("AUTO_PUBLISH", r"자동\s*발행|auto[- ]?publish"),
    ("PUBLIC_API", r"공개\s*API|public API"),
    ("GLOBAL_RESTAURANT_OUTLINE", r"모든\s*(?:글|게시물).*밑반찬과 기본 상차림"),
    ("NOT_RUN_COMPLETE", r"not_run[^\n]{0,100}(?:research complete|리서치 완료)"),
    ("PROMPT_INJECTION", r"ignore previous instructions|system prompt"),
    ("SECRET", r"(?:cookie|token|api[_ -]?key|authorization)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{8,}"),
)


def check_document(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return [f"{path}: unreadable ({error.strerror})"]
    errors = [f"{path}: missing {term}" for term in REQUIRED_TERMS if term not in text]
    for label, pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            errors.append(f"{path}: forbidden {label}")
    return errors


def main(arguments: list[str]) -> int:
    if arguments == ["--help"]:
        print("usage: check_docs_consistency.py README.md README.ko.md redesign-spec.md")
        return 0
    if len(arguments) != 3:
        print("expected exactly three documentation paths", file=sys.stderr)
        return 2
    errors: list[str] = []
    for raw_path in arguments:
        errors.extend(check_document(Path(raw_path)))
    for error in errors:
        print(error, file=sys.stderr)
    print(f"checked={len(arguments)} errors={len(errors)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
