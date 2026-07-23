#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_competitors.py
====================
네이버 블로그 경쟁사/참고 글 수집기.

insane-search(github.com/fivetaku/insane-search)의 네이버 전용 전략 적용:
  * 검색: Chrome UA + Naver Referer → search.naver.com (where=post)
  * 블로그 본문: blog.naver.com → m.blog.naver.com 변환 + iPhone UA

Usage:
    # 업체명으로 검색 후 수집
    python3 scripts/fetch_competitors.py --query "큰바다도매횟집" --count 7 --output posts/큰바다횟집/raw_crawled.json

    # URL 목록 직접 지정
    python3 scripts/fetch_competitors.py --urls "https://blog.naver.com/xxx/123" "https://blog.naver.com/yyy/456" --output posts/큰바다횟집/raw_crawled.json
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import List, Optional

# ── User-Agent 전략 (insane-search references/naver.md 기반) ─────────────────
UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
UA_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

# 검색어에 함께 붙여 내돈내산 후기 위주로 걸러내는 키워드
REVIEW_KEYWORDS = ["후기", "내돈내산", "방문기", "추천"]


def _get(url: str, *, ua: str, referer: str, timeout: int = 12) -> Optional[str]:
    """Simple urllib GET with custom UA/Referer. Returns decoded text or None."""
    headers = {
        "User-Agent": ua,
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": referer,
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [WARN] GET failed: {url[:80]} → {e}", file=sys.stderr)
        return None


# ── Phase 0: Naver Search → Blog URL 추출 ────────────────────────────────────

def search_naver_blog(query: str, count: int = 8) -> List[str]:
    """
    네이버 블로그 탭 검색 → blog.naver.com URL 목록 반환.

    insane-search naver.md:
      "블로그 탭: search.naver.com?where=post&query=..."
    """
    seen: set[str] = set()
    urls: list[str] = []

    # 검색어 변형: 업체명 단독 + 업체명 + 리뷰 키워드
    queries = [query] + [f"{query} {kw}" for kw in REVIEW_KEYWORDS]

    for q in queries:
        if len(urls) >= count:
            break
        encoded = urllib.parse.quote(q)
        search_url = f"https://search.naver.com/search.naver?where=post&query={encoded}"
        print(f"[SEARCH] {q}")
        body = _get(search_url, ua=UA_CHROME, referer="https://www.naver.com/")
        if not body:
            continue

        # URL 패턴: https://blog.naver.com/{id}/{no}
        for blog_id, log_no in re.findall(
            r'https://blog\.naver\.com/([a-zA-Z0-9_.-]+)/(\d+)', body
        ):
            u = f"https://blog.naver.com/{blog_id}/{log_no}"
            if u not in seen:
                seen.add(u)
                urls.append(u)
                if len(urls) >= count:
                    break

        time.sleep(0.4)  # politeness

    print(f"[SEARCH] 총 {len(urls)}개 URL 수집")
    return urls[:count]


# ── Phase 1: blog.naver.com → m.blog.naver.com + iPhone UA ──────────────────

def _to_mobile_url(blog_url: str) -> Optional[str]:
    """
    blog.naver.com/{id}/{no} → m.blog.naver.com/PostView.naver?blogId=…&logNo=…

    insane-search naver.md:
      "WebFetch 차단. 모바일 URL 변환 + iPhone UA로 접근."
    """
    m = re.match(r'https://blog\.naver\.com/([a-zA-Z0-9_.-]+)/(\d+)', blog_url)
    if not m:
        return None
    return (
        f"https://m.blog.naver.com/PostView.naver"
        f"?blogId={m.group(1)}&logNo={m.group(2)}"
    )


def fetch_blog_html(blog_url: str) -> Optional[str]:
    mobile_url = _to_mobile_url(blog_url)
    if not mobile_url:
        print(f"  [WARN] URL 변환 실패: {blog_url}", file=sys.stderr)
        return None
    return _get(mobile_url, ua=UA_IPHONE, referer="https://m.naver.com/")


# ── Phase 2: HTML 파싱 → 순수 텍스트 추출 ────────────────────────────────────

def _strip_tags(fragment: str) -> str:
    """Replace block-level tags with newlines, then strip all remaining HTML tags."""
    fragment = re.sub(r'</?(?:p|br|div|li|tr)[^>]*>', '\n', fragment)
    fragment = re.sub(r'<[^>]+>', '', fragment)
    return html.unescape(fragment)


def parse_blog_text(html_content: str) -> dict:
    """
    HTML → { title, url, paragraphs: [str] }

    네이버 SmartEditor ONE 구조:
      <div class="se-main-container">
        <div class="se-module se-module-text">...</div>  ← 본문 텍스트
    """
    if not html_content:
        return {"title": "", "paragraphs": []}

    # 제목 (og:title)
    title_m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_content)
    title = html.unescape(title_m.group(1)) if title_m else ""

    # se-main-container 영역
    container_m = re.search(
        r'<div class="se-main-container">(.*?)(?=<script\b|<!-- SE_DOC_FOOTER|$)',
        html_content,
        re.DOTALL,
    )
    if not container_m:
        return {"title": title, "paragraphs": []}

    container = container_m.group(1)

    # se-module-text 블록 전체 추출
    modules = re.findall(
        r'<div[^>]*class="[^"]*se-module-text[^"]*"[^>]*>(.*?)</div>',
        container,
        re.DOTALL,
    )

    paragraphs: List[str] = []
    for mod in modules:
        raw = _strip_tags(mod)
        for line in raw.split("\n"):
            line = re.sub(r'\s+', ' ', line).strip()
            # 해시태그 라인 및 빈 줄 제거
            if not line or line.startswith("#"):
                continue
            # 공백 문자만 있는 줄 제거
            if line in ("​", "\u200b", ""):
                continue
            paragraphs.append(line)

    return {"title": title, "paragraphs": paragraphs}


def _parse_legacy(html_content: str) -> List[str]:
    """
    구 에디터(SmartEditor 2.0) 또는 se-main-container 파싱 실패 시 폴백.
    postViewArea, postListBody, se-content 등 다양한 컨테이너를 시도.
    """
    candidates = [
        r'<div[^>]*id="[^"]*postViewArea[^"]*"[^>]*>(.*?)</div\s*>',
        r'<div[^>]*class="[^"]*postListBody[^"]*"[^>]*>(.*?)</div\s*>',
        r'<div[^>]*class="[^"]*se-content[^"]*"[^>]*>(.*?)',  # open-ended
    ]
    for pattern in candidates:
        m = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        if m:
            raw = _strip_tags(m.group(1))
            lines = []
            for line in raw.split("\n"):
                line = re.sub(r'\s+', ' ', line).strip()
                if not line or line.startswith("#") or line in ("\u200b",):
                    continue
                lines.append(line)
            if lines:
                return lines
    return []


# ── 통합 파이프라인 ───────────────────────────────────────────────────────────

def run(
    *,
    query: Optional[str] = None,
    urls: Optional[List[str]] = None,
    count: int = 7,
    output: str,
) -> List[dict]:
    """
    수집 파이프라인 실행.

    1. query 또는 urls 중 하나 입력.
    2. 각 URL에서 모바일 HTML 다운로드 + 파싱.
    3. JSON으로 결과 저장.
    """
    if not query and not urls:
        raise ValueError("--query 또는 --urls 중 하나는 필수입니다.")

    # URL 목록 확보
    if urls:
        target_urls = urls[:count]
    else:
        target_urls = search_naver_blog(query, count=count)

    if not target_urls:
        _remove_stale_output(output)
        print("[ERROR] 수집할 URL을 찾지 못했습니다.", file=sys.stderr)
        return []

    results: list[dict] = []
    for i, url in enumerate(target_urls, 1):
        print(f"[FETCH {i}/{len(target_urls)}] {url}")
        html_content = fetch_blog_html(url)
        if not html_content:
            print("  [SKIP] 본문을 가져오지 못했습니다.", file=sys.stderr)
            continue

        parsed = parse_blog_text(html_content)
        parser_used = "smarteditor"
        # 파싱 결과가 비어있으면 구 에디터 폴백 시도
        if not parsed["paragraphs"]:
            parsed["paragraphs"] = _parse_legacy(html_content)
            if parsed["paragraphs"]:
                parser_used = "legacy"
                print("  [INFO] 구 에디터 폴백 파서 사용")
        if not parsed["paragraphs"]:
            print("  [SKIP] 읽을 수 있는 본문이 없습니다.", file=sys.stderr)
            continue

        parsed["source_url"] = url
        parsed["mobile_url"] = _to_mobile_url(url) or url
        parsed["query"] = query
        parsed["search_rank"] = i
        parsed["rank_status"] = "observed"
        parsed["retrieved_at"] = datetime.now(UTC).isoformat()
        parsed["parser_used"] = parser_used
        parsed["content_sha256"] = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
        results.append(parsed)
        print(f"  → 제목: {parsed['title']!r}  / 단락: {len(parsed['paragraphs'])}개")
        time.sleep(0.5)  # politeness

    if not results:
        _remove_stale_output(output)
        print("[ERROR] 읽을 수 있는 참고 글을 확보하지 못했습니다.", file=sys.stderr)
        return []

    # 저장
    output_dir = os.path.dirname(output) or "."
    os.makedirs(output_dir, exist_ok=True)
    file_descriptor, temporary_output = tempfile.mkstemp(
        dir=output_dir,
        prefix=".raw_crawled-",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        os.replace(temporary_output, output)
    finally:
        if os.path.exists(temporary_output):
            os.remove(temporary_output)
    print(f"\n[DONE] {len(results)}개 저장 → {output}")
    return results


def _remove_stale_output(output: str) -> None:
    if os.path.exists(output):
        os.remove(output)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="네이버 블로그 참고 글 수집기 (insane-search 전략 기반)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="업체명 (네이버 블로그 탭 검색)")
    group.add_argument("--urls", nargs="+", help="블로그 URL 직접 지정 (공백 구분)")
    parser.add_argument("--count", type=int, default=7, help="수집할 글 수 (기본: 7)")
    parser.add_argument("--output", required=True, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    try:
        results = run(
            query=args.query,
            urls=args.urls,
            count=args.count,
            output=args.output,
        )
    except OSError as error:
        print(f"[ERROR] 결과 파일 처리 실패: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    if not results:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
