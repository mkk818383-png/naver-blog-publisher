from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Final, TypedDict


RUN_KEYS: Final = frozenset(
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
FETCHER_FIELDS: Final = (
    "source_url",
    "mobile_url",
    "query",
    "retrieved_at",
    "parser_used",
    "content_sha256",
)
BLOCKED_TEXT: Final = re.compile(
    r"<[^>]+>|ignore (?:all )?previous instructions|system prompt|you are chatgpt",
    re.IGNORECASE,
)
CONFLICT_FIELDS: Final = ("hours", "address", "phone")
APPROVED_INPUTS: Final = (
    ("user", "approved-user"),
    ("place", "approved-place"),
    ("image", "approved-image"),
)


class SourcePackError(Exception):
    def __init__(self, diagnostic: str) -> None:
        self.diagnostic = diagnostic
        super().__init__(diagnostic)


class FetchRecord(TypedDict):
    source_url: str
    mobile_url: str
    query: str | None
    retrieved_at: str
    parser_used: str
    content_sha256: str


class ApprovedRecord(TypedDict):
    source_id: str
    kind: str
    text: str


def read_json(path: Path) -> dict[str, object] | list[object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SourcePackError(f"SOURCE_PACK_INPUT: missing {path}") from error
    except json.JSONDecodeError as error:
        raise SourcePackError(f"SOURCE_PACK_INPUT: invalid JSON in {path}") from error
    if not isinstance(value, (dict, list)):
        raise SourcePackError(f"SOURCE_PACK_INPUT: expected object or list in {path}")
    return value


def parse_run(metadata: dict[str, object]) -> tuple[str, str]:
    if set(metadata) != RUN_KEYS:
        raise SourcePackError("SOURCE_PACK_METADATA: top-level schema mismatch")
    run_id = metadata.get("run_id")
    status = metadata.get("research_status")
    if not isinstance(run_id, str) or not run_id:
        raise SourcePackError("SOURCE_PACK_METADATA: run_id is required")
    if not isinstance(status, str):
        raise SourcePackError("SOURCE_PACK_STATUS: research_status is required")
    match status:
        case "complete":
            return run_id, status
        case "not_run" | "partial" | "empty" | "error" | "stale":
            raise SourcePackError(f"SOURCE_PACK_STATUS: {status} is not publishable")
        case _:
            raise SourcePackError(f"SOURCE_PACK_STATUS: unknown status {status}")


def raw_items(raw: dict[str, object] | list[object]) -> list[object]:
    if isinstance(raw, list):
        return raw
    query = raw.get("query")
    if query is not None:
        if not isinstance(query, str):
            raise SourcePackError("SOURCE_PACK_INPUT: top-level query must be text")
        if BLOCKED_TEXT.search(query):
            raise SourcePackError("SOURCE_PACK_UNSAFE: raw HTML or injection text rejected")
    items = raw.get("items")
    if isinstance(items, list):
        return items
    return []


def parse_records(raw: dict[str, object] | list[object]) -> list[FetchRecord]:
    items = raw_items(raw)
    if not isinstance(items, list) or not items:
        raise SourcePackError("SOURCE_PACK_EMPTY: raw research has no usable sources")
    records: list[FetchRecord] = []
    for item in items:
        if not isinstance(item, dict):
            raise SourcePackError("SOURCE_PACK_INPUT: raw item must be an object")
        values: dict[str, str | None] = {}
        for field in FETCHER_FIELDS:
            value = item.get(field)
            if field == "query" and value is None:
                values[field] = None
                continue
            if not isinstance(value, str) or not value:
                raise SourcePackError(f"SOURCE_PACK_INPUT: missing fetcher field {field}")
            if BLOCKED_TEXT.search(value):
                raise SourcePackError("SOURCE_PACK_UNSAFE: raw HTML or injection text rejected")
            values[field] = value
        records.append(
            FetchRecord(
                source_url=str(values["source_url"]),
                mobile_url=str(values["mobile_url"]),
                query=values["query"],
                retrieved_at=str(values["retrieved_at"]),
                parser_used=str(values["parser_used"]),
                content_sha256=str(values["content_sha256"]),
            )
        )
    return records


def find_conflicts(raw_items: list[object]) -> list[dict[str, object]]:
    conflicts: list[dict[str, object]] = []
    for field in CONFLICT_FIELDS:
        values: dict[str, list[str]] = {}
        for index, item in enumerate(raw_items, 1):
            if not isinstance(item, dict):
                continue
            value = item.get(field)
            if isinstance(value, str) and value:
                values.setdefault(value, []).append(f"SRC-{index:03d}")
        if len(values) > 1:
            source_ids = [source_id for group in values.values() for source_id in group]
            conflicts.append(
                {
                    "status": "UNRESOLVED_CONFLICT",
                    "claim": field,
                    "source_ids": source_ids,
                    "reason": "conflicting source values require human review",
                    "outcome": "FAIL_PUBLISH",
                }
            )
    return conflicts


def parse_approved_input(label: str, path: Path, run_id: str) -> list[ApprovedRecord]:
    input_name = f"approved-{label}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: missing {input_name} input") from error
    except json.JSONDecodeError as error:
        raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: invalid JSON in {input_name} input") from error
    if not isinstance(value, dict) or set(value) != {"schema_version", "run_id", "approved", "records"}:
        raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: schema mismatch in {input_name} input")
    if value.get("schema_version") != "v2" or value.get("run_id") != run_id or value.get("approved") is not True:
        raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: unapproved or mismatched {input_name} input")
    records = value.get("records")
    if not isinstance(records, list) or not records:
        raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: empty {input_name} input")
    parsed: list[ApprovedRecord] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"id", "text"}:
            raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: record schema mismatch in {input_name} input")
        identifier = record.get("id")
        text = record.get("text")
        if not isinstance(identifier, str) or not identifier or not isinstance(text, str) or not text:
            raise SourcePackError(f"SOURCE_PACK_APPROVED_INPUT: invalid record in {input_name} input")
        if BLOCKED_TEXT.search(identifier) or BLOCKED_TEXT.search(text):
            raise SourcePackError("SOURCE_PACK_UNSAFE: raw HTML or injection text rejected")
        parsed.append(ApprovedRecord(source_id=identifier, kind=label, text=text))
    return parsed


def build_pack(
    metadata: dict[str, object],
    raw: dict[str, object] | list[object],
    approved_records: list[ApprovedRecord],
) -> dict[str, object]:
    run_id, _ = parse_run(metadata)
    records = parse_records(raw)
    conflicts = find_conflicts(raw_items(raw))
    if conflicts:
        raise SourcePackError("SOURCE_PACK_CONFLICT: UNRESOLVED_CONFLICT FAIL_PUBLISH")
    activity_id = f"ACT-source-pack-{run_id}"
    agent_id = "agent-source-pack-builder"
    sources = [
        {
            "source_id": f"SRC-{index:03d}",
            **record,
            "activity_id": activity_id,
            "agent_id": agent_id,
        }
        for index, record in enumerate(records, 1)
    ]
    claims: list[dict[str, object]] = [
        {
            "claim_id": f"CLM-{index:03d}",
            "text": "Source retrieved for provenance review.",
            "source_ids": [f"SRC-{index:03d}"],
            "activity_id": activity_id,
            "agent_id": agent_id,
        }
        for index in range(1, len(records) + 1)
    ]
    approved_sources = [
        {
            "source_id": record["source_id"],
            "source_type": f"approved-{record['kind']}",
            "activity_id": activity_id,
            "agent_id": agent_id,
        }
        for record in approved_records
    ]
    sources.extend(approved_sources)
    claims.extend(
        {
            "claim_id": f"CLM-{record['source_id']}",
            "text": record["text"],
            "source_ids": [record["source_id"]],
            "activity_id": activity_id,
            "agent_id": agent_id,
        }
        for record in approved_records
    )
    return {
        "schema_version": "v2",
        "run_id": run_id,
        "research_status": "complete",
        "sources": sources,
        "claims": claims,
        "conflicts": [],
        "freshness": {"checked_at": min(record["retrieved_at"] for record in records), "stale": False},
        "provenance": {
            "activity_id": activity_id,
            "agent_id": agent_id,
            "draft_claim_ids": [],
            "approved_inputs": [
                {
                    "kind": record["kind"],
                    "source_id": record["source_id"],
                    "activity_id": activity_id,
                    "agent_id": agent_id,
                }
                for record in approved_records
            ],
        },
    }


def write_json_atomically(output: Path, value: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=output.parent, prefix=".source-pack-", suffix=".tmp", text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic v2 Source Pack.")
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--approved-user")
    parser.add_argument("--approved-place")
    parser.add_argument("--approved-image")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        metadata = read_json(Path(args.metadata))
        if not isinstance(metadata, dict):
            raise SourcePackError("SOURCE_PACK_METADATA: expected object")
        run_id, _ = parse_run(metadata)
        metadata_dir = Path(args.metadata).parent
        paths = (
            Path(args.approved_user) if args.approved_user else metadata_dir / "approved_user.json",
            Path(args.approved_place) if args.approved_place else metadata_dir / "approved_place.json",
            Path(args.approved_image) if args.approved_image else metadata_dir / "approved_image.json",
        )
        raw = read_json(Path(args.raw))
        build_pack(metadata, raw, [])
        approved_records = [
            record
            for (kind, _), path in zip(APPROVED_INPUTS, paths, strict=True)
            for record in parse_approved_input(kind, path, run_id)
        ]
        pack = build_pack(metadata, raw, approved_records)
        write_json_atomically(Path(args.output), pack)
    except SourcePackError as error:
        print(error.diagnostic, file=sys.stderr)
        return 1
    except OSError as error:
        print(f"SOURCE_PACK_IO: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
