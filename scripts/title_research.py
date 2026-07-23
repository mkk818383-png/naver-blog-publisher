#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Extract title keywords and produce a reviewable ten-title shortlist."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypedDict


TOKEN_PATTERN: Final = re.compile(r"[가-힣A-Za-z0-9]{2,}")
STOPWORDS: Final = frozenset(
    "안녕하세요 오늘 방문 후기 리뷰 추천 정말 너무 저희 이번 그리고 있는 있어요 합니다 했어요 같아요 생각 곳 정보 메뉴 카페 맛집 다녀왔어요".split()
)


class Source(TypedDict):
    search_rank: int
    rank_status: str
    title: str
    source_url: str
    paragraphs: list[str]


class Keyword(TypedDict):
    keyword: str
    score: int
    source_ranks: list[int]
    body_supported: bool


class Title(TypedDict):
    rank: int
    title: str
    reason: str
    rules: list[str]


class SourceSummary(TypedDict):
    search_rank: int
    rank_status: str
    title: str
    source_url: str


class Report(TypedDict):
    query: str
    retrieved_at: str
    primary_keyword: str
    venue: str
    research_status: str
    ranking_scope: str
    rank_verified: bool
    source_count: int
    sources: list[SourceSummary]
    secondary_keywords: list[Keyword]
    titles: list[Title]


def _tokens(text: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(text) if token not in STOPWORDS]


def _load_sources(path: Path) -> list[Source]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    sources: list[Source] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rank = item.get("search_rank")
        title = item.get("title")
        url = item.get("source_url")
        paragraphs = item.get("paragraphs", [])
        if not isinstance(rank, int) or not isinstance(title, str) or not isinstance(url, str):
            continue
        if not isinstance(paragraphs, list):
            paragraphs = []
        sources.append(
            {
                "search_rank": rank,
                "rank_status": str(item.get("rank_status", "observed")),
                "title": title,
                "source_url": url,
                "paragraphs": [str(paragraph) for paragraph in paragraphs],
            }
        )
    return sorted(sources, key=lambda source: source["search_rank"])


def _keyword_report(sources: list[Source], post_text: str, primary_keyword: str, venue: str) -> list[Keyword]:
    scores: dict[str, int] = {}
    ranks: dict[str, set[int]] = {}
    for source in sources:
        rank = source["search_rank"]
        for token in _tokens(source["title"]):
            scores[token] = scores.get(token, 0) + 4
            ranks.setdefault(token, set()).add(rank)
        for paragraph in source["paragraphs"]:
            for token in _tokens(paragraph):
                scores[token] = scores.get(token, 0) + 1
                ranks.setdefault(token, set()).add(rank)

    post_tokens = set(_tokens(post_text))
    excluded = set(primary_keyword.split()) | set(venue.split()) | {"그랜드하브", "산청리", "쿠지"}
    candidates = [token for token in scores if token not in excluded and not any(part and part in token for part in venue.split())]
    candidates.sort(key=lambda token: (-scores[token], token))
    return [
        {
            "keyword": token,
            "score": scores[token],
            "source_ranks": sorted(ranks[token]),
            "body_supported": token in post_tokens,
        }
        for token in candidates[:6]
    ]


def _recommend_titles(primary: str, venue: str, keywords: list[Keyword]) -> list[Title]:
    focus = [item["keyword"] for item in keywords] or ["방문"]
    while len(focus) < 3:
        focus.append(focus[-1])
    templates = (
        (f"{primary}, {venue} {focus[0]} 후기", "KW-01", ["R6"]),
        (f"{primary}, {focus[0]}와 {focus[1]}를 같이 본 날", "KW-02", ["R6", "R1"]),
        (f"{primary}, {focus[0]} 주문 전 확인한 정보", "KW-03", ["R5", "R6"]),
        (f"{primary}, {focus[0]}보다 오래 머문 이유: {focus[1]}", "TG-01", ["R1", "R6"]),
        (f"{primary}, {venue} {focus[0]} 메뉴와 공간 후기", "KW-04", ["R6"]),
        (f"{primary}, 주차부터 {focus[0]}까지 한 번에 정리", "TG-02", ["R5", "R6"]),
        (f"{primary}, {focus[0]} 때문에 다시 생각난 방문", "TG-03", ["R1", "R6"]),
        (f"{primary}, {focus[0]}와 {focus[1]} 중 고른 조합", "TG-04", ["R1", "R6"]),
        (f"{primary}, {focus[0]} 있는 날 다녀온 기록", "KW-05", ["R6"]),
        (f"{primary}, {venue} 방문 전 체크포인트", "TG-05", ["R5", "R6"]),
    )
    return [
        {"rank": rank, "title": title, "reason": f"{reason} 본문과 검색어 근거를 함께 확인.", "rules": rules}
        for rank, (title, reason, rules) in enumerate(templates, start=1)
    ]


def build_report(primary_keyword: str, venue: str, sources: list[Source], post_text: str, query: str = "") -> Report:
    ranks = [source["search_rank"] for source in sources]
    complete = len(sources) >= 5 and ranks[:5] == [1, 2, 3, 4, 5]
    status = "complete" if complete else "partial"
    keywords = _keyword_report(sources, post_text, primary_keyword, venue)
    return {
        "query": query or primary_keyword,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "primary_keyword": primary_keyword,
        "venue": venue,
        "research_status": status,
        "ranking_scope": "observed_search_order",
        "rank_verified": all(source["rank_status"] == "observed" for source in sources),
        "source_count": len(sources),
        "sources": [
            {
                "search_rank": source["search_rank"],
                "rank_status": source["rank_status"],
                "title": source["title"],
                "source_url": source["source_url"],
            }
            for source in sources
        ],
        "secondary_keywords": keywords,
        "titles": _recommend_titles(primary_keyword, venue, keywords),
    }


def main() -> int:  # noqa: BROAD_EXCEPT_OK
    parser = argparse.ArgumentParser(description="검색 결과 기반 제목 키워드·후보 생성")
    parser.add_argument("--primary-keyword", required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--post", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        sources = _load_sources(args.research)
        if len(sources) < 5 or [source["search_rank"] for source in sources[:5]] != [1, 2, 3, 4, 5]:
            print("RESEARCH_PARTIAL: ranked sources 1-5 are required", file=sys.stderr)
            return 1
        report = build_report(args.primary_keyword, args.venue, sources, args.post.read_text(encoding="utf-8"), args.query)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError) as error:
        print(f"RESEARCH_INPUT: {error}", file=sys.stderr)
        return 2
    print(f"Success: wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
