#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run scripts/check_v2_contracts.py references/content-type-templates.md references/research-workflow.md references/image-caption-guide.md references/draft-modes.md
# 3. Or make executable and run:
#      chmod +x scripts/check_v2_contracts.py && ./scripts/check_v2_contracts.py [FILES]
# ──────────────────

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Final

TYPE_IDS: Final = (
    "restaurant",
    "cafe",
    "accommodation",
    "experience",
    "beauty",
    "retail",
)
STATUSES: Final = ("not_run", "complete", "partial", "empty", "error", "stale")
MODES: Final = ("model-draft", "publish-safe", "memo-only")
EXPECTED_FILENAMES: Final = (
    "content-type-templates.md",
    "research-workflow.md",
    "image-caption-guide.md",
    "draft-modes.md",
)


def section_after(text: str, heading: str) -> str:
    match = re.search(rf"^## `{re.escape(heading)}`\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    return "" if match is None else match.group(1)


def list_after(section: str, heading: str) -> list[str]:
    match = re.search(rf"^### {re.escape(heading)}\s*$([\s\S]*?)(?=^### |\Z)", section, re.MULTILINE)
    if match is None:
        return []
    return re.findall(r"^- (.+\S)\s*$", match.group(1), re.MULTILINE)


def load_contracts(arguments: list[str]) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    contracts: dict[str, str] = {}
    match len(arguments):
        case 4:
            pass
        case _:
            return contracts, ["expected exactly four contract paths"]
    for raw_path in arguments:
        path = Path(raw_path)
        name = path.name
        if name not in EXPECTED_FILENAMES:
            errors.append(f"unexpected contract filename: {name}")
            continue
        if not path.is_file():
            errors.append(f"missing contract: {path}")
            continue
        contracts[name] = path.read_text(encoding="utf-8")
    for name in EXPECTED_FILENAMES:
        if name not in contracts:
            errors.append(f"required contract not supplied: {name}")
    return contracts, errors


def contains_forbidden_source_text(text: str) -> bool:
    return bool(re.search(r"<[A-Za-z][^>]*>", text)) or "IGNORE PREVIOUS INSTRUCTIONS" in text.upper()


def check_templates(text: str) -> list[str]:
    errors: list[str] = []
    if "## Common flow" not in text:
        errors.append("templates: missing common flow")
    for type_id in TYPE_IDS:
        section = section_after(text, type_id)
        if not section:
            errors.append(f"templates: missing type {type_id}")
            continue
        for heading in ("Required modules", "Optional modules", "Forbidden modules"):
            if not list_after(section, heading):
                errors.append(f"templates: {type_id} has empty {heading.lower()}")
        ordered_flow = re.search(r"^### Ordered flow\s*$\n\n(.+→.+)$", section, re.MULTILINE)
        if ordered_flow is None:
            errors.append(f"templates: {type_id} missing ordered flow")
    return errors


def require_all(text: str, labels: tuple[str, ...], prefix: str) -> list[str]:
    return [f"{prefix}: missing {label}" for label in labels if label not in text]


def check_research(text: str) -> list[str]:
    errors = require_all(
        text,
        ("source_pack.json", "schema_version", "run_id", "research_status", "sources", "claims", "conflicts", "freshness", "provenance"),
        "research schema",
    )
    errors.extend(require_all(text, STATUSES, "research statuses"))
    errors.extend(require_all(text, ("Only `complete` is publishable", "`valid` is not an alias"), "research gate"))
    errors.extend(require_all(text, ("UNRESOLVED_CONFLICT", "FAIL_PUBLISH"), "research conflict"))
    errors.extend(
        require_all(
            text,
            ("source → claim → draft", "source_id", "claim_id", "draft_claim_ids", "activity_id", "agent_id", "policy_gate", "manual_review_required", "memo-only"),
            "research provenance",
        )
    )
    return errors


def check_image(text: str) -> list[str]:
    return require_all(
        text,
        ("immutable", "`id`", "`original_file`", "`caption`", "three-digit", "`001`", "`evidence`", "`visible`", "`source-pack`", "`used_in`", "unsupported", "![[사진 001: caption]]"),
        "image contract",
    )


def check_modes(text: str) -> list[str]:
    errors = require_all(text, MODES, "draft modes")
    errors.extend(
        require_all(
            text,
            ("Disclosure matrix", "disclosure_kind", "disclosure_text", "disclosure_placement", "sponsored", "title or opening", "final disclosure area", "manually publishes"),
            "disclosure",
        )
    )
    return errors


def main() -> int:
    contracts, errors = load_contracts(sys.argv[1:])
    combined = "\n".join(contracts.values())
    if contracts and contains_forbidden_source_text(combined):
        errors.append("contracts: raw HTML or prompt-injection canary detected")
    templates = contracts.get("content-type-templates.md")
    if templates is not None:
        errors.extend(check_templates(templates))
    research = contracts.get("research-workflow.md")
    if research is not None:
        errors.extend(check_research(research))
    image = contracts.get("image-caption-guide.md")
    if image is not None:
        errors.extend(check_image(image))
    modes = contracts.get("draft-modes.md")
    if modes is not None:
        errors.extend(check_modes(modes))
    result = {
        "errors": errors,
        "modes": list(MODES),
        "ok": not errors,
        "statuses": list(STATUSES),
        "types": list(TYPE_IDS),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
