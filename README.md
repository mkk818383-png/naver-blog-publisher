# naver-blog-publisher

> **네이버 블로그 체험단 작성·내보내기 스킬** — AI 에이전트(Antigravity / Claude Code) 전용

업체명 하나만 입력하면 실제 네이버 블로그 후기 5~10개를 자동으로 읽고, 나만의 말투(다온로그 스타일)로 새 블로그 글을 써줍니다. 결과물은 네이버 스마트에디터 ONE에 바로 붙여넣기 가능한 HTML로 컴파일됩니다.

---

## 주요 기능

- 🔍 **자동 리서치**: 업체명만 주면 네이버 블로그 탭에서 후기 5~10개 자동 수집
- 📝 **다온로그 스타일**: 고정된 글 구조, 자연스러운 모바일 줄 바꿈, 실제 경험에 근거한 말투
- 🛡️ **WAF 우회**: insane-search 기법 적용 (모바일 URL 변환 + iPhone UA로 네이버 블로그 접근)
- 📋 **context.md**: 수집된 글에서 메뉴·가격·분위기·꿀팁을 정리한 참고 문서 자동 생성
- 🖥️ **HTML 출력**: 나눔고딕·16px·200% 줄간격으로 포맷된 복붙용 HTML 파일 생성

---

## 작동 흐름

```
업체명 입력
    │
    ▼
1단계: 네이버 블로그 5~10개 수집
    │  (search.naver.com → m.blog.naver.com, iPhone UA 우회)
    ▼
2단계: 핵심 정보 정리 → context.md (메뉴·가격·분위기·팁·출처 장부)
    │
    ▼
3단계: 출처 ID 정리 + 고정 구조로 다온로그 글 작성
    │
    ▼
4단계: 제목 후보 10개 생성 + 자동 검수
    │
    ▼
5단계: 검수 통과 후 HTML 컴파일 → 복붙용 post.html
```

---

## 설치 방법

### A — skills 마켓플레이스로 설치

```bash
npx skills add https://github.com/mkk818383-png/naver-blog-publisher -g -y
```

### B — 수동 클론

```bash
git clone https://github.com/mkk818383-png/naver-blog-publisher \
  ~/.agents/skills/naver-blog-publisher
```

---

## 사용 방법

AI 에이전트에서 스킬 호출:

```
/naver-blog-publisher
```

아래 정보를 입력합니다. `[업체명]`, `[업종]`, `[고지 방식]`은 필수입니다.

```
[업체명]: 큰바다도매횟집
[업종]: restaurant | cafe | accommodation | experience | beauty | retail
[키워드]: 명지 횟집                                ← (선택) 제목 키워드
[방문 메모]: 불금 6시 30분 만석, 모둠회 소 49,000원 ← (선택) 직접 다녀온 경우
[광고주 가이드라인]: 제목에 '명지 횟집' 필수 포함   ← (선택) 광고 조건
[사진 체크리스트]: 1. 외관 2. 메뉴판 3. 밑반찬     ← (선택) 사진 목록
[고지 방식]: self-paid | sponsored                  ← (필수) 직접 명시
```

**리서치 입력 경로:**

| 모드 | 입력 | 동작 |
|------|------|------|
| **자동 리서치** | 필수 입력 + `[업체명]` | 네이버 블로그 5~10개 수집·분석 후 작성 |
| **수동 입력** | 필수 입력 + `[방문 메모]` | 크롤링 없이 메모만으로 글 작성 |
| **혼합** | 필수 입력 + 둘 다 | 수집한 사실 + 내 경험을 합쳐서 작성 |

리서치는 네이버 블로그 공개 페이지에서 5~10건까지만 수집합니다. 계정 로그인,
게시물 작성, 발행 동작은 수행하지 않으며 수집한 원문은 사실 확인용 평문으로만
사용합니다.

## v2 운영 계약

- `run.json`에는 `content_type`, `draft_mode`, `disclosure`, `research_status`,
  `source_pack`, `image_index`, `expected_h2`를 명시합니다. 업종은
  `restaurant`, `cafe`, `accommodation`, `experience`, `beauty`, `retail` 중 하나이며
  각 업종의 모듈 순서를 사용합니다. 식당의 구역을 다른 업종의 기본 구조로 쓰지 않습니다.
- `source_pack.json`의 상태는 `not_run`, `complete`, `partial`, `empty`, `error`,
  `stale`뿐입니다. `not_run 상태는 완료된 리서치가 아니다`; `complete`만 초안 및
  내보내기 후보의 리서치 게이트를 통과합니다.
- `image_index.json`은 원본을 바꾸지 않고 `사진 001`, `사진 002`, `사진 003`처럼
  `001`부터 연속된 세 자리 ID와 근거 있는 캡션을 연결합니다. 본문 플레이스홀더는
  `![[사진 001: 캡션]]` 형식이며 인덱스와 정확히 일치해야 합니다.
- 세 가지 초안 모드는 `model-draft`, `publish-safe`, `memo-only`입니다.
  `model-draft`에는 `MODEL-DRAFT` 표시가 필요하고, `publish-safe`의 1인칭 경험은
  `EXP-*` 근거에 연결하며, `memo-only`는 컴파일하거나 내보낼 수 없습니다.
- 고지 방식은 `self-paid` 또는 `sponsored`입니다. `sponsored`는 **제목 또는 도입**과
  **최종 고지 구역** 모두에 표시합니다.

---

## 결과물 파일 구조

```
posts/{가게이름}/
  run.json           ← 업종·초안 모드·고지·리서치 상태
  raw_crawled.json   ← 크롤링 원본 데이터
  source_pack.json   ← 검토한 출처·주장·충돌·신선도 기록
  image_index.json   ← 원본 파일과 사진 ID·캡션·근거의 불변 인덱스
  context.md         ← 핵심 정보 분석 보고서 (메뉴·가격·분위기·팁)
  post.md            ← 다온로그 마크다운 초안
  titles.json        ← 1~10위 제목 후보와 각 선정 이유
  post.html          ← 복붙용 HTML (네이버 스마트에디터 전용)
```

---

## 네이버 블로그 수집 전략

[insane-search](https://github.com/fivetaku/insane-search)의 `references/naver.md` 전략을 기반으로 합니다.

| 단계 | 방법 |
|------|------|
| 검색 | `search.naver.com?where=post&query={업체명}` + Chrome UA + Naver Referer |
| 다운로드 | `blog.naver.com/{id}/{no}` → `m.blog.naver.com/PostView.naver?blogId=…&logNo=…` + iPhone UA |
| 파싱 | SmartEditor ONE `se-module-text` → 구 에디터 `postViewArea` 폴백 |

### 수집 신뢰성 기준

- 본문 단락이 있는 글만 `raw_crawled.json`에 저장합니다. 확보한 글이 하나도 없으면 종료 코드 `1`로 실패하고 이전 수집본도 삭제되며, 빈 자료로 초안을 만들지 않습니다. 종료 코드 `2`는 파일 저장 오류입니다.
- 각 기록에는 검색어, 수집 시각, 사용 파서, 원문 해시를 남깁니다.
- 블로그 후기는 반복 키워드를 찾는 참고 자료입니다. 메뉴·가격·운영 정보는 플레이스·업체 안내·메뉴판으로 재확인하고, 작성자 개인 경험은 내 경험처럼 쓰지 않습니다.

---

## 내보내기와 수동 발행

1. 생성된 `post.html` 파일 열기
2. 전체 선택(Cmd+A) → 복사(Cmd+C)
3. 네이버 블로그 → 글쓰기 → 스마트에디터 ONE → **[HTML]** 탭 클릭
4. 붙여넣기(Cmd+V)
5. **[편집기]** 탭으로 돌아와 회색 점선 플레이스홀더 → 실제 사진으로 교체
6. 사람이 최종 검토한 뒤 네이버 편집기에서 수동으로 발행

검수와 컴파일은 `post.html` 내보내기까지만 합니다. 서비스에 글을 쓰거나 발행하는
기능은 없습니다.

---

## 다온로그 스타일 규칙

- **H1 제목**: 공백 제외 25~30자 범위. 핵심 키워드는 한 번만 자연스럽게 문장에 녹이며, 키워드 연속 나열을 피합니다.
- **본문 구조**: `run.json`의 `content_type`에 맞는 필수·선택·금지 모듈과
  `expected_h2` 순서를 사용합니다. 업종이 없거나 알 수 없으면 실패합니다.
- **본문 줄바꿈**: 문장을 먼저 완성한 뒤 의미 단위로 나눕니다. 공백 제외 13자를 목표로 하며, 검사 대상 줄의 80% 이상은 10~16자, 모든 대상 줄은 20자 이하이고 9자 이하 대상 줄이 연속되면 안 됩니다.
- **출처 원칙**: 장소 사실은 `FACT-*`, 사용자의 일정·동행·주문·감정은 `EXP-*`로 추적합니다. 확인되지 않은 정보와 경험은 추정하지 않고 생략합니다.
- **고지 방식**: `self-paid` 또는 `sponsored`를 입력에서 명시하며 본문만 보고 추정하지 않습니다.
- **제목 후보**: 본문 완성 후 NotebookLM에서 한 번 검증해 로컬에 고정한 제목 가이드로 정확히 10개를 순위와 이유까지 작성합니다. 실행 중 NotebookLM 연결은 필요하지 않습니다.
- **종결어미**: ~요, ~네요, ~더라고요, ~했어요, ~얌 !, ~했어용 ㅎㅎ
- **이모지**: 😌 ✨ 🥹 😆 🤍 🥰 ☺️ 🫶
- **금지 단어**: 결론적으로, 주목할 만한, 이러한, 이를 통해, 살펴보겠습니다, 알아보겠습니다, 예랑, 예비신랑

HTML은 아래 검사가 성공한 뒤에만 컴파일합니다. 실패하면 표시된 항목을 고치고 같은 검사를 다시 실행합니다.

v2 검증기는 메타데이터·Source Pack·이미지 인덱스, 업종별 모듈, 초안 모드, 고지,
사진 ID와 캡션, 방문 흐름을 먼저 검사합니다. **검증기는 기존 줄바꿈 검사를 마지막에 실행**합니다.

```bash
python3 scripts/validate_post.py posts/{가게이름}/post.md \
  --disclosure self-paid \
  --metadata posts/{가게이름}/run.json \
  --source-pack posts/{가게이름}/source_pack.json \
  --image-index posts/{가게이름}/image_index.json \
  --titles posts/{가게이름}/titles.json
```

---

## 라이선스

MIT
