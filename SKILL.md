---
name: naver-blog-publisher
description: >
  Use when the user wants to publish a Naver Blog post, write experience reviews,
  or generate styled promotional blog content. Now includes automatic competitor
  research: given a shop name, the agent reads 5–10 real Naver blog posts about
  that place and writes a new post in the daonlog style.
---

# Naver Blog Publisher

## Overview

This skill writes styled Naver Blog experience-group posts (체험단 포스팅) in Markdown
and compiles them to copy-pasteable HTML.

**Two research modes are supported — use whichever the user provides:**

| Mode | Trigger | What the agent does |
|------|---------|---------------------|
| **Auto-search** | User provides shop name only | Agent searches Naver Blog, reads 5–10 posts, distills key facts |
| **Manual input** | User provides visit notes | Skip crawl; use supplied notes directly |
| **Hybrid** | Both provided | Crawl first, then enrich with user's personal visit notes |

---

## Step 0 — Gather Inputs

Ask the user for **as many of the following as they can provide**. Nothing is strictly required except a way to identify the place.

```
[업체명]: (예: 큰바다도매횟집)               ← 이것만 있으면 자동 리서치 가능
[블로그 URL 목록]: (선택) 직접 참고할 URL들
[키워드]: (선택) 제목에 넣을 타깃 키워드
[방문 메모]: (선택) 직접 다녀온 경우 메모
[광고주 가이드라인]: (선택) 필수 키워드, 지도 첨부 여부 등
[사진 체크리스트]: (선택) 업로드할 사진 목록
```

If `[방문 메모]` is rich and detailed, the agent MAY skip crawling. Otherwise always run Phase 1.

---

## Phase 1 — Competitor Blog Research (automatic)

> **Skip this phase only if the user explicitly says "방문 메모만 써줘" or equivalent.**

### 1-A  Find blog posts

**Option A — shop name search (default)**

Run the bundled script via terminal:

```bash
# SKILL_DIR = path to this skill's folder (where SKILL.md lives)
python3 {SKILL_DIR}/scripts/fetch_competitors.py \
  --query "{업체명}" \
  --count 7 \
  --output posts/{shop_name}/raw_crawled.json
```

**Option B — user-supplied URL list**

```bash
python3 {SKILL_DIR}/scripts/fetch_competitors.py \
  --urls {URL1} {URL2} ... \
  --output posts/{shop_name}/raw_crawled.json
```

`{SKILL_DIR}` is the absolute path to the directory containing this SKILL.md.
`{shop_name}` is derived from `[업체명]` or the first URL's blog title.

The script will:
- Search `search.naver.com?where=post&query={업체명}` using Chrome UA + Naver Referer
- Convert each `blog.naver.com/{id}/{no}` URL → `m.blog.naver.com/PostView.naver?blogId=…&logNo=…`
- Fetch with iPhone UA + `m.naver.com` Referer to bypass WAF (insane-search strategy)
- Parse SmartEditor ONE (`se-module-text`) and legacy editor (`postViewArea`) blocks
- Save results to `raw_crawled.json`

### 1-B  Distill into context.md

Read `raw_crawled.json` and write `posts/{shop_name}/context.md` with these sections:

```markdown
# {업체명} — 리서치 컨텍스트

## 기본 정보
- 위치:
- 영업시간:
- 전화번호:
- 주차:

## 메뉴 & 가격
| 메뉴 | 가격 | 언급 횟수 |
|------|------|----------|
| … | … | … |

## 대표 맛·분위기 키워드
(여러 글에서 반복 등장한 표현들, 볼드 처리)

## 꿀팁 & 특이사항
- (현금 결제 혜택, 서비스 메뉴, 웨이팅, 주차 팁 등)

## 부정적 언급 (있을 경우)
- …

## 참고 URL 목록
- …
```

---

## Phase 2 — Strategy Setting

Using `context.md` + `[방문 메모]` (if any) + `[광고주 가이드라인]`, decide:
- **Angle**: 어떤 독자를 위한 글인가? (예: 명지 주민, 주말 나들이객)
- **H2 소제목 5–7개** outline (must satisfy all guideline requirements)

---

## Phase 3 — Content Generation (daonlog-style)

Write the full blog post in Markdown. **Strict formatting rules:**

### Typography Rules
- **H1 제목**: 공백 제외 **20자 이하** (무조건)
- **본문 각 줄**: 공백 제외 **20자 이하** — 자연스러운 단어 단위로 줄 바꿈
- **문단**: 1–3줄 후 빈 줄로 구분

### Tone & Voice (다온로그 스타일)
- 종결어미: `~요`, `~네요`, `~요!`, `~랍니다`, `~더라고요`, `~했어요`
- 감성 어미: `~지 뭐예요 ㅋㅋㅋ`, `~얌!`, `~했어용 ㅎㅎ`
- 이모지: 😌 ✨ 🥹 😆 🤍 🥰 ☺️ 🫶 😌👍
- 텍스트 이모티콘: `:)` `( ˶'ᵕ'˶)` `(„• ᴗ •„)`
- **금지 단어**: `결론적으로` `주목할 만한` `이러한` `이를 통해` `살펴보겠습니다` `알아보겠습니다`

### Image Placeholders
- 사진 체크리스트의 각 항목 → `![[사진 N: 한 줄 설명]]` 으로 삽입
- 사진 없이 쓸 경우: 단락 전환 자연스러운 지점에 자동 배치

### Info Block
반드시 포함:
```
📍 주소: …
⏰ 영업시간: …
🚘 주차: …
```
그리고 `[지도: {업체명}]` 태그 (가이드라인에 지도 첨부가 필요한 경우)

---

## Phase 4 — SEO & Guideline Verification

Check all of the following before proceeding:

- [ ] H1 제목 공백 제외 20자 이하
- [ ] 본문 각 줄 공백 제외 20자 이하
- [ ] 가이드라인 필수 키워드 제목에 포함
- [ ] 가이드라인 본문 키워드 3회 이상 등장
- [ ] 사진 체크리스트 항목이 모두 `![[사진 N: …]]`에 매핑됨
- [ ] 금지 단어 없음

Fail → fix inline and re-check.

---

## Phase 5 — HTML Compilation

Save `posts/{shop_name}/post.md`, then compile:

```bash
python3 {SKILL_DIR}/scripts/compile.py \
  posts/{shop_name}/post.md \
  {SKILL_DIR}/templates/post_template.html \
  posts/{shop_name}/post.html
```

Verify `post.html` was created successfully.

---

## Output Files

```
posts/{shop_name}/
  raw_crawled.json   ← Phase 1-A: 크롤링 원본
  context.md         ← Phase 1-B: 핵심 정보 보고서
  post.md            ← Phase 3: 다온로그 마크다운 초안
  post.html          ← Phase 5: 발행용 HTML (복붙용)
```

---

## How to Publish

1. `post.html` 열기 → 전체 선택(Cmd+A) → 복사(Cmd+C)
2. 네이버 블로그 → 글쓰기 → 스마트에디터 ONE → **[HTML]** 탭 클릭
3. 붙여넣기(Cmd+V)
4. **[편집기]** 탭으로 돌아와 회색 점선 플레이스홀더 → 실제 사진으로 교체
5. 최종 검토 후 **발행**

---

## Common Mistakes

- H1 제목 글자수 계산 시 공백 포함하여 계산하는 실수 → 공백 **제외** 기준
- `raw_crawled.json` 없이 글 쓰는 것 → 업체명이 있으면 반드시 Phase 1 먼저
- `{SKILL_DIR}` 경로 하드코딩 → 항상 이 SKILL.md가 위치한 디렉터리 기준으로 계산
- HTML 컴파일 후 경로 미확인 → `Success:` 메시지 반드시 확인
