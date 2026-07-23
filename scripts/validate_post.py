#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

if __package__:
    from .validate_post_v2 import validate_v2
else:
    from validate_post_v2 import validate_v2


REQUIRED_H2: Final[tuple[str, ...]] = (
    "도입",
    "장소 정보",
    "주차와 찾아가는 길",
    "메뉴판 소개",
    "우리가 고른 메뉴",
    "밑반찬과 기본 상차림",
    "가게 내부와 공간 이야기",
    "메인 메뉴와 먹는 방법",
    "총평",
)
OPTIONAL_H2: Final = "식사 후 일정"
FORBIDDEN_TERMS: Final[tuple[str, ...]] = (
    "결론적으로",
    "주목할 만한",
    "이러한",
    "이를 통해",
    "살펴보겠습니다",
    "알아보겠습니다",
    "예랑",
    "예비신랑",
)
H1_PATTERN: Final = re.compile(r"^#(?!#)\s+(.+?)\s*$")
H2_PATTERN: Final = re.compile(r"^##(?!#)\s+(.+?)\s*$")
LIST_PATTERN: Final = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
INFO_PATTERN: Final = re.compile(r"^(?:📍|⏰|🚘|☎️?|주소\s*:|영업시간\s*:|전화번호\s*:|주차\s*:)")
RAW_HTML_PATTERN: Final = re.compile(r"</?[A-Za-z][^>]*>")
STICKER_ANCHOR_PATTERN: Final = re.compile(r"^\[[가-힣A-Za-z0-9·& ]{1,12}\]$")
DISCLOSURES: Final[dict[str, tuple[str, ...]]] = {
    "self-paid": ("내돈내산",),
    "sponsored": ("제공받아", "협찬", "원고료"),
}


@dataclass(frozen=True, slots=True)
class Diagnostic:
    rule_id: str
    line: int | None
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class ParsedLine:
    number: int
    text: str
    heading_level: int | None
    heading: str | None
    eligible: bool
    ignored: bool
    compiler_visible: bool


def validate_post(
    text: str,
    disclosure: str,
    titles_text: str | None = None,
    metadata_text: str | None = None,
    source_pack_text: str | None = None,
    image_index_text: str | None = None,
) -> ValidationResult:
    parsed = _parse_lines(text)
    diagnostics = [Diagnostic(rule_id, line, message) for rule_id, line, message in validate_v2(text, disclosure, metadata_text, source_pack_text, image_index_text)]
    uses_v2_artifacts = metadata_text is not None and source_pack_text is not None and image_index_text is not None
    h1_lines = [line for line in parsed if line.heading_level == 1]
    if len(h1_lines) != 1:
        diagnostics.append(Diagnostic("STRUCTURE_H1_COUNT", h1_lines[1].number if len(h1_lines) > 1 else None, f"expected exactly one H1, found {len(h1_lines)}"))

    h2_lines = [line for line in parsed if line.heading_level == 2]
    actual_h2 = tuple(line.heading or "" for line in h2_lines)
    expected_nine = REQUIRED_H2
    expected_ten = REQUIRED_H2[:-1] + (OPTIONAL_H2, REQUIRED_H2[-1])
    if not uses_v2_artifacts and actual_h2 not in (expected_nine, expected_ten):
        diagnostics.append(Diagnostic("STRUCTURE_H2_ORDER", _first_h2_difference_line(h2_lines, expected_nine, expected_ten), "H2 names or order do not match the canonical outline"))

    diagnostics.extend(_empty_section_diagnostics(parsed, h2_lines))
    eligible = [line for line in parsed if line.eligible]
    if not eligible:
        diagnostics.append(Diagnostic("LINE_EMPTY", None, "no eligible prose lines found"))
    else:
        lengths = [(line, _length_without_whitespace(line.text)) for line in eligible]
        in_range = sum(10 <= length <= 16 for _, length in lengths)
        if in_range * 100 < len(lengths) * 80:
            diagnostics.append(Diagnostic("LINE_RATIO", None, f"{in_range}/{len(lengths)} eligible lines are 10-16 characters"))
        for line, length in lengths:
            if length > 20:
                diagnostics.append(Diagnostic("LINE_MAX", line.number, f"eligible line has {length} characters"))
        diagnostics.extend(_adjacent_short_diagnostics(parsed))

    for line in parsed:
        if not line.ignored and line.heading_level is None and not _is_excluded(line.text):
            for term in FORBIDDEN_TERMS:
                if term in line.text:
                    diagnostics.append(Diagnostic("FORBIDDEN_TERM", line.number, f"forbidden term: {term}"))

        if RAW_HTML_PATTERN.search(line.text):
            diagnostics.append(Diagnostic("HTML_RAW_TAG", line.number, "raw HTML tags are not allowed"))

    expected_markers = DISCLOSURES[disclosure]
    other_mode = "sponsored" if disclosure == "self-paid" else "self-paid"
    expected_text = "\n".join(line.text for line in parsed if _is_disclosure_content(line))
    visible_text = "\n".join(line.text for line in parsed if line.compiler_visible)
    has_expected = any(marker in expected_text for marker in expected_markers)
    has_other = any(marker in visible_text for marker in DISCLOSURES[other_mode])
    if not has_expected or has_other:
        diagnostics.append(Diagnostic("DISCLOSURE_MISMATCH", None, f"disclosure does not match {disclosure}"))

    if titles_text is not None and not _valid_titles(titles_text):
        diagnostics.append(Diagnostic("TITLES_CONTRACT", None, "titles must contain ranks 1-10 with nonempty titles and reasons"))

    ordered = tuple(sorted(diagnostics, key=lambda item: (item.line is None, item.line or 0, item.rule_id, item.message)))
    return ValidationResult(valid=not ordered, diagnostics=ordered)


def _parse_lines(text: str) -> tuple[ParsedLine, ...]:
    result: list[ParsedLine] = []
    in_fence = False
    in_comment = False
    for number, raw in enumerate(text.splitlines(), start=1):
        visible, in_comment, had_comment = _strip_html_comments(raw, in_comment)
        stripped = visible.strip()
        if not stripped and had_comment:
            result.append(ParsedLine(number, visible, None, None, False, True, False))
            continue
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            result.append(ParsedLine(number, visible, None, None, False, True, True))
            continue
        if in_fence or stripped.startswith(">"):
            result.append(ParsedLine(number, visible, None, None, False, True, True))
            continue
        h1 = H1_PATTERN.match(visible)
        h2 = H2_PATTERN.match(visible)
        heading_level = 1 if h1 else 2 if h2 else None
        heading = h1.group(1) if h1 else h2.group(1) if h2 else None
        eligible = bool(stripped and heading_level is None and not _is_excluded(stripped))
        result.append(ParsedLine(number, visible, heading_level, heading, eligible, False, True))
    return tuple(result)


def _strip_html_comments(text: str, in_comment: bool) -> tuple[str, bool, bool]:
    visible: list[str] = []
    cursor = 0
    had_comment = in_comment
    while True:
        delimiter = "-->" if in_comment else "<!--"
        boundary = text.find(delimiter, cursor)
        if boundary < 0:
            return "".join(visible if in_comment else [*visible, text[cursor:]]), in_comment, had_comment
        if not in_comment:
            visible.append(text[cursor:boundary])
        cursor = boundary + len(delimiter)
        in_comment = not in_comment
        had_comment = True


def _is_excluded(text: str) -> bool:
    stripped = text.strip()
    return bool(
        not stripped
        or LIST_PATTERN.match(stripped)
        or STICKER_ANCHOR_PATTERN.match(stripped)
        or stripped.startswith(("|", "![[", "![", "[지도:", "<", "*내돈내산", "*본 포스팅"))
        or INFO_PATTERN.match(stripped)
        or any(marker in stripped for markers in DISCLOSURES.values() for marker in markers)
    )


def _length_without_whitespace(text: str) -> int:
    return len("".join(text.split()))


def _first_h2_difference_line(lines: list[ParsedLine], *expected_options: tuple[str, ...]) -> int | None:
    for index, line in enumerate(lines):
        if not any(index < len(expected) and line.heading == expected[index] for expected in expected_options):
            return line.number
    return lines[-1].number if lines else None


def _empty_section_diagnostics(parsed: tuple[ParsedLine, ...], headings: list[ParsedLine]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    indexes = {line.number: index for index, line in enumerate(parsed)}
    for position, heading in enumerate(headings):
        end = indexes[headings[position + 1].number] if position + 1 < len(headings) else len(parsed)
        start = indexes[heading.number] + 1
        content = [line for line in parsed[start:end] if _is_section_content(line)]
        if not content:
            diagnostics.append(Diagnostic("STRUCTURE_EMPTY_SECTION", heading.number, f"empty section: {heading.heading}"))
    return diagnostics


def _is_section_content(line: ParsedLine) -> bool:
    stripped = line.text.strip()
    return not line.ignored and (line.eligible or stripped.startswith(("![[", "![", "[지도:")))


def _is_disclosure_content(line: ParsedLine) -> bool:
    stripped = line.text.strip()
    return bool(
        not line.ignored
        and line.heading_level is None
        and not LIST_PATTERN.match(stripped)
        and not stripped.startswith(("![[", "![", "[지도:"))
        and not INFO_PATTERN.match(stripped)
    )


def _adjacent_short_diagnostics(parsed: tuple[ParsedLine, ...]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    previous: ParsedLine | None = None
    for line in parsed:
        if line.eligible:
            if previous is not None and _length_without_whitespace(previous.text) <= 9 and _length_without_whitespace(line.text) <= 9:
                diagnostics.append(Diagnostic("LINE_ADJACENT_SHORT", line.number, "adjacent eligible lines are 9 characters or fewer"))
            previous = line
        else:
            previous = None
    return diagnostics


def _valid_titles(text: str) -> bool:
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
    except ValueError:
        return False
    if not isinstance(value, list) or len(value) != 10:
        return False
    normalized_titles: set[str] = set()
    for index, item in enumerate(value, start=1):
        rank = item.get("rank") if isinstance(item, dict) else None
        if type(rank) is not int or rank != index:
            return False
        title = item.get("title")
        reason = item.get("reason")
        if not isinstance(title, str) or not title.strip() or not isinstance(reason, str) or not reason.strip():
            return False
        normalized_title = "".join(title.split()).casefold()
        if normalized_title in normalized_titles:
            return False
        normalized_titles.add(normalized_title)
    return True


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(key)
        result[key] = value
    return result


def _json_output(result: ValidationResult) -> str:
    payload = {
        "diagnostics": [{"line": item.line, "message": item.message, "rule_id": item.rule_id} for item in result.diagnostics],
        "valid": result.valid,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Daonlog Markdown post")
    parser.add_argument("post", type=Path)
    parser.add_argument("--disclosure", choices=tuple(DISCLOSURES), required=True)
    parser.add_argument("--titles", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--source-pack", type=Path)
    parser.add_argument("--image-index", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        text = args.post.read_text(encoding="utf-8")
        titles_text = args.titles.read_text(encoding="utf-8") if args.titles else None
        metadata_text = args.metadata.read_text(encoding="utf-8") if args.metadata else None
        source_pack_text = args.source_pack.read_text(encoding="utf-8") if args.source_pack else None
        image_index_text = args.image_index.read_text(encoding="utf-8") if args.image_index else None
    except (OSError, UnicodeError) as error:
        print(f"read error: {error}", file=sys.stderr)
        return 2
    result = validate_post(text, args.disclosure, titles_text, metadata_text, source_pack_text, image_index_text)
    if args.json:
        sys.stdout.write(_json_output(result))
    else:
        for item in result.diagnostics:
            location = f"line {item.line}: " if item.line is not None else ""
            print(f"{item.rule_id}: {location}{item.message}")
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
