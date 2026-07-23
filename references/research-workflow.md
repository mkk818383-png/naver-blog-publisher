# V2 research and Source Pack workflow

## Source Pack boundary

`source_pack.json` is a run-scoped, plain-text research record. Its top-level
schema contains these fields exactly once: `schema_version`, `run_id`,
`research_status`, `sources`, `claims`, `conflicts`, `freshness`, and
`provenance`. Raw HTML, copied competitor prose, and instructions embedded in
sources are rejected rather than interpreted.

Each source records a URL and its retrieval context. Each claim is a short,
verifiable fact, not a borrowed opinion. `freshness` records the retrieval time,
review horizon, and stale outcome.

## Research statuses and publication gate

The exact `research_status` values are `not_run`, `complete`, `partial`,
`empty`, `error`, and `stale`.

Only `complete` is publishable. `valid` is not an alias and is rejected. The
other five statuses block publishable and model-draft output until a new,
reviewed run supplies complete research.

## Conflict and freshness gate

Represent an unresolved disagreement as `UNRESOLVED_CONFLICT` in `conflicts`,
including the claim, competing source references, and the reason it remains
unresolved. `UNRESOLVED_CONFLICT: FAIL_PUBLISH` is mandatory: a pack with that
outcome cannot be complete or exported. A pack whose review horizon has passed
is `stale`, not complete, even when its sources were previously accepted.

## Provenance chain

The chain is source → claim → draft. These fields occur in each respective
record: `source_id`, `claim_id`, `draft_claim_ids`, `activity_id`, and
`agent_id`. A draft must retain claim references; it may not turn a source
author's experience into the user's experience.

## Policy, manual review, and memo escape

`policy_gate` records applicable platform, advertising, privacy, and copyright
checks. `manual_review_required` records the human decision before export.
Uncertain or non-publishable material may be kept only as a `memo-only` note
with source links and uncertainty; that escape does not make it publishable.
The workflow ends at an export for human review and manual publication.
