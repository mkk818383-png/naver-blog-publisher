from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


IMAGE_IDS = re.compile(r"!\[\[(?:사진|동영상)\s+(\d{3})(?::[^\]]*)?\]\]")
INDEX_KEYS = frozenset({"schema_version", "run_id", "items"})
ITEM_KEYS = frozenset({"id", "original_file", "caption", "evidence", "used_in"})


class ImageIndexError(Exception):
    def __init__(self, diagnostic: str) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic)


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ImageIndexError(f"IMAGE_INDEX_INPUT: missing {path}") from error
    except json.JSONDecodeError as error:
        raise ImageIndexError(f"IMAGE_INDEX_INPUT: invalid JSON in {path}") from error
    if not isinstance(value, dict):
        raise ImageIndexError(f"IMAGE_INDEX_INPUT: expected object in {path}")
    return value


def validate_index(index: dict[str, object]) -> set[str]:
    if set(index) != INDEX_KEYS:
        raise ImageIndexError("IMAGE_INDEX_SCHEMA: top-level schema mismatch")
    items = index.get("items")
    if not isinstance(items, list):
        raise ImageIndexError("IMAGE_INDEX_SCHEMA: items must be a list")
    identifiers: list[str] = []
    originals: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != ITEM_KEYS:
            raise ImageIndexError("IMAGE_INDEX_SCHEMA: item schema mismatch")
        identifier = item["id"]
        original = item["original_file"]
        caption = item["caption"]
        evidence = item["evidence"]
        used_in = item["used_in"]
        if not isinstance(identifier, str) or not re.fullmatch(r"\d{3}", identifier):
            raise ImageIndexError("IMAGE_INDEX_IDS: ids must be three-digit strings")
        if not isinstance(original, str) or not original or Path(original).name != original:
            raise ImageIndexError("IMAGE_INDEX_ORIGINAL: original_file must retain its filename")
        if original in originals:
            raise ImageIndexError("IMAGE_INDEX_ORIGINAL: original_file must be unique")
        if not isinstance(caption, str) or not caption:
            raise ImageIndexError("IMAGE_INDEX_CAPTION: caption is required")
        if evidence not in {"visible", "source-pack"}:
            raise ImageIndexError("IMAGE_INDEX_EVIDENCE: evidence must be visible or source-pack")
        if not isinstance(used_in, list) or not used_in or not all(isinstance(value, str) and value for value in used_in):
            raise ImageIndexError("IMAGE_INDEX_USED_IN: used_in is required")
        identifiers.append(identifier)
        originals.add(original)
    expected = [f"{number:03d}" for number in range(1, len(identifiers) + 1)]
    if sorted(identifiers) != expected:
        raise ImageIndexError("IMAGE_INDEX_IDS: ids must be unique and contiguous from 001")
    return set(identifiers)


def validate_post(index_ids: set[str], post: Path) -> None:
    try:
        body = post.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ImageIndexError(f"IMAGE_INDEX_INPUT: missing {post}") from error
    body_ids = set(IMAGE_IDS.findall(body))
    if body_ids != index_ids:
        raise ImageIndexError("IMAGE_INDEX_BODY_SET: post media IDs must exactly match index IDs")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a v2 image index against a Markdown post.")
    parser.add_argument("--index", required=True)
    parser.add_argument("--post", required=True)
    args = parser.parse_args()
    try:
        validate_post(validate_index(read_json(Path(args.index))), Path(args.post))
    except ImageIndexError as error:
        print(error.diagnostic, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
