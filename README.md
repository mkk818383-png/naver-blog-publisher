# naver-blog-publisher

> **네이버 블로그 체험단 반자동 발행 스킬** for AI coding agents (Antigravity / Claude Code)

A skill that automatically researches a place by reading real Naver blog posts, then writes a new post in your personal writing style — ready to copy-paste into Naver SmartEditor ONE.

---

## Features

- 🔍 **Auto-research**: Given a shop name, searches Naver Blog and reads 5–10 real posts
- 📝 **daonlog-style writing**: Matching tone, 20-char line wrap, emojis, no AI filler words
- 🛡️ **WAF bypass**: Uses insane-search techniques (mobile URL + iPhone UA) to read Naver Blog
- 📋 **context.md**: Distills crawled posts into a structured reference (menu, price, tips)
- 🖥️ **HTML output**: Compiles to copy-pasteable HTML for Naver SmartEditor ONE

---

## How It Works

```
업체명 입력
    │
    ▼
Phase 1: fetch 5–10 Naver blog posts about the place
    │  (search.naver.com → m.blog.naver.com, iPhone UA bypass)
    ▼
Phase 1-B: Distill → context.md (menu, price, vibe, tips)
    │
    ▼
Phase 2-3: Write daonlog-style post using context.md + your notes
    │
    ▼
Phase 4: SEO & guideline check
    │
    ▼
Phase 5: Compile → post.html (copy-paste ready)
```

---

## Installation

### Option A — Install via skills marketplace

```bash
npx skills add https://github.com/mkk818383-png/naver-blog-publisher -g -y
```

### Option B — Clone manually

```bash
git clone https://github.com/mkk818383-png/naver-blog-publisher \
  ~/.agents/skills/naver-blog-publisher
```

---

## Usage

Invoke the skill from your AI agent:

```
/naver-blog-publisher
```

Then provide any of the following (only `[업체명]` is required for auto-research):

```
[업체명]: 큰바다도매횟집
[키워드]: 명지 횟집 (optional)
[방문 메모]: 불금 6시 30분 만석, 모둠회 소 49000원 ... (optional)
[광고주 가이드라인]: 제목에 '명지 횟집' 필수, 본문 '가성비' 3회 이상 (optional)
[사진 체크리스트]: 1. 외관 2. 메뉴판 3. 밑반찬 ... (optional)
```

**Three modes:**
| Mode | What to provide |
|------|----------------|
| **Auto** | `[업체명]` only — agent searches & reads Naver Blog automatically |
| **Manual** | `[방문 메모]` — agent skips crawl, writes from your notes |
| **Hybrid** | Both — crawl for facts + enrich with your personal experience |

---

## Output

```
posts/{shop_name}/
  raw_crawled.json   ← crawled Naver blog posts (raw)
  context.md         ← distilled reference: menu, price, tips, vibe
  post.md            ← daonlog-style Markdown draft
  post.html          ← copy-paste ready HTML for Naver SmartEditor ONE
```

---

## Naver Blog Fetch Strategy (insane-search based)

| Step | Method |
|------|--------|
| Search | `search.naver.com?where=post&query=…` + Chrome UA + Naver Referer |
| Fetch | `blog.naver.com/{id}/{no}` → `m.blog.naver.com/PostView.naver?blogId=…&logNo=…` + iPhone UA |
| Parse | SmartEditor ONE `se-module-text` → fallback to legacy `postViewArea` |

Based on the [insane-search](https://github.com/fivetaku/insane-search) `references/naver.md` strategy.

---

## Writing Style Rules (daonlog-style)

- **H1 title**: max 20 chars excluding spaces
- **Every body line**: max 20 chars excluding spaces (mobile-first)
- **Endings**: ~요, ~네요, ~더라고요, ~했어요, ~얌!, ~했어용 ㅎㅎ
- **Emojis**: 😌 ✨ 🥹 😆 🤍 🥰 ☺️ 🫶
- **Banned words**: 결론적으로, 주목할 만한, 이러한, 이를 통해

---

## License

MIT
