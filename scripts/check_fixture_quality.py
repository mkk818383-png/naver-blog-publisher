#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final


CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"restaurant", "cafe", "accommodation", "experience", "beauty", "retail"}
)
REQUIRED_RUN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "run_id",
        "content_type",
        "draft_mode",
        "disclosure",
        "research_status",
        "source_pack",
        "image_index",
        "expected_h2",
    }
)
TYPE_MARKERS: Final[dict[str, str]] = {
    "restaurant": "밑반찬과 기본 상차림",
    "cafe": "음료와 디저트 고르기",
    "accommodation": "체크인과 객실",
    "experience": "진행 순서",
    "beauty": "시술 과정",
    "retail": "상품 둘러보기",
}
CAFE_NEGATIVES: Final[frozenset[str]] = frozenset(
    {
        "run_not_run.json",
        "run_memo_only.json",
        "run_sponsored.json",
        "run_missing_motive.json",
        "run_placeholder.json",
        "run_short_review.json",
        "post_memo_only.md",
        "post_sponsored_missing_opening.md",
        "post_missing_motive.md",
        "post_placeholder.md",
        "post_short_review.md",
        "image_duplicate.json",
        "image_gap.json",
        "image_extra.json",
        "image_missing.json",
    }
)


def read_json(path: Path, errors: list[str]) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{path}: unreadable JSON ({error})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path}: expected a JSON object")
        return None
    return value


def headings(post: Path) -> list[str]:
    return [line[3:].strip() for line in post.read_text(encoding="utf-8").splitlines() if line.startswith("## ")]


def check_run(folder: Path, run_name: str, errors: list[str]) -> dict[str, object] | None:
    run = read_json(folder / run_name, errors)
    if run is None:
        return None
    missing = sorted(REQUIRED_RUN_FIELDS - run.keys())
    if missing:
        errors.append(f"{folder / run_name}: missing required fields: {', '.join(missing)}")
        return run
    content_type = run["content_type"]
    expected_h2 = run["expected_h2"]
    if content_type not in CONTENT_TYPES:
        errors.append(f"{folder / run_name}: unsupported content_type {content_type!r}")
        return run
    if not isinstance(expected_h2, list) or not all(isinstance(item, str) and item.strip() for item in expected_h2):
        errors.append(f"{folder / run_name}: expected_h2 must be a nonempty list of headings")
        return run
    expected = [item.strip() for item in expected_h2]
    if len(expected) < 7 or len(expected) != len(set(expected)):
        errors.append(f"{folder / run_name}: expected_h2 must contain at least seven unique headings")
    if any(item in {"...", "TODO", "TBD", "expected_h2"} for item in expected):
        errors.append(f"{folder / run_name}: expected_h2 contains a placeholder")
    marker = TYPE_MARKERS[content_type]
    if marker not in expected:
        errors.append(f"{folder / run_name}: expected_h2 lacks its type-specific marker {marker!r}")
    return run


def check_type_folder(root: Path, content_type: str, errors: list[str]) -> None:
    folder = root / content_type
    required = {"run.json", "post.md", "post_forbidden_module.md", "source_pack.json", "image_index.json"}
    if content_type == "cafe":
        required |= CAFE_NEGATIVES
    missing = sorted(name for name in required if not (folder / name).is_file())
    if missing:
        errors.append(f"{folder}: missing fixtures: {', '.join(missing)}")
        return
    run = check_run(folder, "run.json", errors)
    if run is None:
        return
    expected_h2 = run.get("expected_h2")
    if isinstance(expected_h2, list) and all(isinstance(item, str) for item in expected_h2):
        if headings(folder / "post.md") != expected_h2:
            errors.append(f"{folder / 'post.md'}: headings do not match run.json expected_h2")
    for name in ("source_pack", "image_index"):
        value = run.get(name)
        if not isinstance(value, str) or not value.endswith(".json") or not (folder / value).is_file():
            errors.append(f"{folder / 'run.json'}: {name} must name an existing JSON fixture")
    if content_type == "cafe":
        for name in sorted(item for item in CAFE_NEGATIVES if item.startswith("run_")):
            check_run(folder, name, errors)


def check_root(root: Path) -> list[str]:
    errors: list[str] = []
    actual = {path.name for path in root.iterdir() if path.is_dir()} if root.is_dir() else set()
    if actual != CONTENT_TYPES:
        errors.append(f"{root}: type folders must be exactly {', '.join(sorted(CONTENT_TYPES))}")
        return errors
    for content_type in sorted(CONTENT_TYPES):
        check_type_folder(root, content_type, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check v2 validator fixtures without importing validator behavior.")
    parser.add_argument("fixture_root", type=Path)
    args = parser.parse_args()
    errors = check_root(args.fixture_root)
    if errors:
        print("fixture-quality: failed")
        print("\n".join(errors))
        return 1
    print("fixture-quality: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
