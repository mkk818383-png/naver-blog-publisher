from __future__ import annotations

import json
import re
from typing import Final


CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"restaurant", "cafe", "accommodation", "experience", "beauty", "retail"}
)
DRAFT_MODES: Final[frozenset[str]] = frozenset({"model-draft", "publish-safe", "memo-only"})
FORBIDDEN_MODULES: Final[dict[str, frozenset[str]]] = {
    "restaurant": frozenset({"쇼케이스와 디저트", "체크인과 객실", "시술 과정", "상품 둘러보기"}),
    "cafe": frozenset({"밑반찬과 기본 상차림", "메인 메뉴와 먹는 방법", "서빙 순서"}),
    "accommodation": frozenset({"메뉴판 소개", "밑반찬과 기본 상차림", "시술 과정"}),
    "experience": frozenset({"밑반찬과 기본 상차림", "메인 메뉴와 먹는 방법", "체크인과 객실"}),
    "beauty": frozenset({"밑반찬과 기본 상차림", "메인 메뉴와 먹는 방법", "상품 피팅"}),
    "retail": frozenset({"밑반찬과 기본 상차림", "시술 과정", "체크인과 객실"}),
}
MEDIA_PATTERN: Final[re.Pattern[str]] = re.compile(r"!\[\[(?:사진|동영상)\s+(\d{3})(?::([^\]]*))?\]\]")
FIRST_PERSON_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:저는|제가|나는|우리는|우리[는가]?)")
EXPERIENCE_LINK_PATTERN: Final[re.Pattern[str]] = re.compile(r"\bEXP-\d+\b")


def validate_v2(
    text: str,
    disclosure: str,
    metadata_text: str | None,
    source_pack_text: str | None,
    image_index_text: str | None,
) -> tuple[tuple[str, int | None, str], ...]:
    if metadata_text is None and source_pack_text is None and image_index_text is None:
        return ()
    if metadata_text is None or source_pack_text is None or image_index_text is None:
        return (("V2_INPUT_REQUIRED", None, "metadata, source pack, and image index are required together"),)
    metadata = _json_object(metadata_text, "METADATA_JSON")
    source_pack = _json_object(source_pack_text, "SOURCE_PACK_JSON")
    image_index = _json_object(image_index_text, "IMAGE_INDEX_JSON")
    if not isinstance(metadata, dict) or not isinstance(source_pack, dict) or not isinstance(image_index, dict):
        return tuple(item for item in (metadata, source_pack, image_index) if isinstance(item, tuple))
    return _artifact_diagnostics(text, disclosure, metadata, source_pack, image_index)


def _json_object(text: str, rule_id: str) -> dict[str, object] | tuple[str, None, str] | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return (rule_id, None, "artifact must be valid JSON")
    if not isinstance(value, dict):
        return (rule_id, None, "artifact must be a JSON object")
    return value


def _artifact_diagnostics(
    text: str,
    disclosure: str,
    metadata: dict[str, object],
    source_pack: dict[str, object],
    image_index: dict[str, object],
) -> tuple[tuple[str, int | None, str], ...]:
    diagnostics: list[tuple[str, int | None, str]] = []
    content_type = metadata.get("content_type")
    draft_mode = metadata.get("draft_mode")
    if not isinstance(content_type, str):
        diagnostics.append(("CONTENT_TYPE_REQUIRED", None, "content_type is required"))
    elif content_type not in CONTENT_TYPES:
        diagnostics.append(("CONTENT_TYPE_UNKNOWN", None, f"unknown content_type: {content_type}"))
    if not isinstance(draft_mode, str) or draft_mode not in DRAFT_MODES:
        diagnostics.append(("DRAFT_MODE_REQUIRED", None, "draft_mode must be explicit and known"))
    elif draft_mode == "memo-only":
        diagnostics.append(("DRAFT_MODE_MEMO_ONLY", None, "memo-only posts cannot be compiled"))
    elif draft_mode == "model-draft" and "MODEL-DRAFT" not in text:
        diagnostics.append(("DRAFT_MODE_MARKER", None, "model-draft posts need a MODEL-DRAFT marker"))
    if metadata.get("disclosure") != disclosure:
        diagnostics.append(("DISCLOSURE_METADATA_MISMATCH", None, "--disclosure must match metadata disclosure"))
    headings = _headings(text)
    if isinstance(content_type, str) and content_type in CONTENT_TYPES:
        expected = metadata.get("expected_h2")
        if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
            diagnostics.append(("CONTENT_TYPE_MODULE_ORDER", None, "expected_h2 must be an explicit heading list"))
        elif headings != expected:
            diagnostics.append(("CONTENT_TYPE_MODULE_ORDER", _first_heading_difference(text, headings, expected), "H2 modules do not match metadata order"))
        forbidden = FORBIDDEN_MODULES[content_type]
        for line, heading in _heading_lines(text):
            if heading in forbidden:
                diagnostics.append(("CONTENT_TYPE_FORBIDDEN_MODULE", line, f"forbidden {content_type} module: {heading}"))
    diagnostics.extend(_source_pack_diagnostics(metadata, source_pack))
    diagnostics.extend(_image_diagnostics(text, image_index))
    diagnostics.extend(_narrative_diagnostics(text, draft_mode, source_pack))
    opening = _section_text(text, "도입")
    if disclosure == "sponsored" and not any(marker in opening for marker in ("제공받아 작성한", "협찬으로 작성", "원고료를 받고")):
        diagnostics.append(("DISCLOSURE_SPONSORED_OPENING", None, "sponsored disclosure is required in the opening"))
    return tuple(diagnostics)


def _source_pack_diagnostics(metadata: dict[str, object], source_pack: dict[str, object]) -> list[tuple[str, int | None, str]]:
    diagnostics: list[tuple[str, int | None, str]] = []
    metadata_status = metadata.get("research_status")
    pack_status = source_pack.get("research_status")
    freshness = source_pack.get("freshness")
    sources = source_pack.get("sources")
    claims = source_pack.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        diagnostics.append(("SOURCE_PACK_SCHEMA", None, "source pack needs sources and claims lists"))
    if _contains_unsafe(source_pack):
        diagnostics.append(("SOURCE_PACK_UNSAFE", None, "source pack contains raw HTML or prompt injection text"))
    if metadata_status != "complete" or pack_status != "complete":
        diagnostics.append(("SOURCE_PACK_STATUS", None, "only complete source packs are valid for posts"))
    if isinstance(freshness, dict) and freshness.get("stale") is True:
        diagnostics.append(("SOURCE_PACK_STALE", None, "source pack is stale"))
    return diagnostics


def _contains_unsafe(value) -> bool:
    match value:
        case str() as text:
            normalized = text.casefold()
            return "<" in text or "ignore previous instruction" in normalized or "system prompt" in normalized
        case list() as items:
            return any(_contains_unsafe(item) for item in items)
        case dict() as mapping:
            return any(_contains_unsafe(item) for item in mapping.values())
        case _:
            return False


def _image_diagnostics(text: str, image_index: dict[str, object]) -> list[tuple[str, int | None, str]]:
    items = image_index.get("items")
    if not isinstance(items, list):
        return [("IMAGE_INDEX_SCHEMA", None, "image index items must be a list")]
    identifiers: list[str] = []
    captions: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            return [("IMAGE_INDEX_SCHEMA", None, "image index items must be objects")]
        identifier = item.get("id")
        caption = item.get("caption")
        evidence = item.get("evidence")
        if not isinstance(identifier, str) or not re.fullmatch(r"\d{3}", identifier):
            return [("IMAGE_INDEX_IDS", None, "image ids must be three digits")]
        if not isinstance(caption, str) or not caption or evidence not in {"visible", "source-pack"}:
            return [("IMAGE_INDEX_EVIDENCE", None, "each image needs caption and valid evidence")]
        identifiers.append(identifier)
        captions[identifier] = caption
    expected = [f"{number:03d}" for number in range(1, len(identifiers) + 1)]
    if sorted(identifiers) != expected:
        return [("IMAGE_INDEX_IDS", None, "image ids must be unique and contiguous from 001")]
    media = MEDIA_PATTERN.findall(text)
    body_ids = {identifier for identifier, _ in media}
    if body_ids != set(identifiers):
        return [("IMAGE_INDEX_BODY_SET", None, "post media IDs must exactly match image index IDs")]
    diagnostics: list[tuple[str, int | None, str]] = []
    for identifier, caption in media:
        if caption.strip() != captions[identifier]:
            diagnostics.append(("IMAGE_INDEX_CAPTION", None, f"media caption must match index evidence for {identifier}"))
    return diagnostics


def _narrative_diagnostics(text: str, draft_mode: object, source_pack: dict[str, object]) -> list[tuple[str, int | None, str]]:
    diagnostics: list[tuple[str, int | None, str]] = []
    visible = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    introduction = _section_text(text, "도입")
    review = _section_text(text, "총평")
    if not any(marker in introduction for marker in ("방문", "위해", "려고", "싶")):
        diagnostics.append(("NARRATIVE_VISIT_MOTIVE", None, "introduction needs a visit motive"))
    if "맛본 뒤 주문" in visible or "이용한 뒤 예약" in visible:
        diagnostics.append(("NARRATIVE_CHRONOLOGY", None, "use flow is not chronological"))
    if not any(marker in review for marker in ("하지만", "아쉬", "대기", "다만", "반면")):
        diagnostics.append(("NARRATIVE_BALANCE", None, "overall review needs a balanced limitation"))
    for placeholder in ("정보가 필요해요", "확인이 필요해요"):
        if placeholder in visible:
            diagnostics.append(("PLACEHOLDER_UNSUPPORTED", None, f"unsupported placeholder: {placeholder}"))
    experience_links = set(EXPERIENCE_LINK_PATTERN.findall(visible))
    claim_ids = _experience_claim_ids(source_pack)
    if draft_mode == "publish-safe" and FIRST_PERSON_PATTERN.search(visible) and (not experience_links or not experience_links <= claim_ids):
        diagnostics.append(("PUBLISH_SAFE_EXP_LINK", None, "first-person claims require a source-pack EXP-* link"))
    return diagnostics


def _experience_claim_ids(source_pack: dict[str, object]) -> set[str]:
    claims = source_pack.get("claims")
    if not isinstance(claims, list):
        return set()
    return {
        identifier
        for claim in claims
        if isinstance(claim, dict)
        for identifier in (claim.get("id"), claim.get("claim_id"))
        if isinstance(identifier, str) and identifier.startswith("EXP-")
    }


def _headings(text: str) -> list[str]:
    return [heading for _, heading in _heading_lines(text)]


def _heading_lines(text: str) -> list[tuple[int, str]]:
    return [(number, line[3:].strip()) for number, line in enumerate(text.splitlines(), 1) if line.startswith("## ")]


def _first_heading_difference(text: str, actual: list[str], expected: list[object]) -> int | None:
    for index, (_, heading) in enumerate(_heading_lines(text)):
        if index >= len(expected) or heading != expected[index]:
            return _heading_lines(text)[index][0]
    return _heading_lines(text)[-1][0] if actual else None


def _section_text(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = next((index + 1 for index, line in enumerate(lines) if line == f"## {heading}"), len(lines))
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])
