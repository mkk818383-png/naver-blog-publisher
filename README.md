# naver-blog-publisher

> **네이버 블로그 체험단 반자동 발행 스킬** — AI 에이전트(Antigravity / Claude Code) 전용

업체명 하나만 입력하면 실제 네이버 블로그 후기 5~10개를 자동으로 읽고, 나만의 말투(다온로그 스타일)로 새 블로그 글을 써줍니다. 결과물은 네이버 스마트에디터 ONE에 바로 붙여넣기 가능한 HTML로 컴파일됩니다.

---

## 주요 기능

- 🔍 **자동 리서치**: 업체명만 주면 네이버 블로그 탭에서 후기 5~10개 자동 수집
- 📝 **다온로그 스타일**: 공백 제외 20자 줄 바꿈, 감성 이모지, AI 금지어 없는 실제 말투
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
2단계: 핵심 정보 정리 → context.md (메뉴·가격·분위기·팁)
    │
    ▼
3단계: context.md + 방문 메모 → 다온로그 스타일 글 작성
    │
    ▼
4단계: SEO & 가이드라인 검수
    │
    ▼
5단계: HTML 컴파일 → 복붙용 post.html
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

아래 중 원하는 정보를 입력합니다. `[업체명]`만 있어도 자동 리서치가 실행됩니다.

```
[업체명]: 큰바다도매횟집
[키워드]: 명지 횟집                                ← (선택) 제목 키워드
[방문 메모]: 불금 6시 30분 만석, 모둠회 소 49,000원 ← (선택) 직접 다녀온 경우
[광고주 가이드라인]: 제목에 '명지 횟집' 필수 포함   ← (선택) 광고 조건
[사진 체크리스트]: 1. 외관 2. 메뉴판 3. 밑반찬     ← (선택) 사진 목록
```

**세 가지 모드:**

| 모드 | 입력 | 동작 |
|------|------|------|
| **자동 리서치** | `[업체명]`만 | 네이버 블로그 5~10개 자동 수집·분석 후 작성 |
| **수동 입력** | `[방문 메모]` 상세 입력 | 크롤링 없이 메모만으로 글 작성 |
| **혼합** | 둘 다 입력 | 크롤링 팩트 + 내 경험 합쳐서 작성 |

---

## 결과물 파일 구조

```
posts/{가게이름}/
  raw_crawled.json   ← 크롤링 원본 데이터
  context.md         ← 핵심 정보 분석 보고서 (메뉴·가격·분위기·팁)
  post.md            ← 다온로그 마크다운 초안
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

---

## 발행 방법

1. 생성된 `post.html` 파일 열기
2. 전체 선택(Cmd+A) → 복사(Cmd+C)
3. 네이버 블로그 → 글쓰기 → 스마트에디터 ONE → **[HTML]** 탭 클릭
4. 붙여넣기(Cmd+V)
5. **[편집기]** 탭으로 돌아와 회색 점선 플레이스홀더 → 실제 사진으로 교체
6. 최종 검토 후 **발행** 클릭

---

## 다온로그 스타일 규칙

- **H1 제목**: 공백 제외 최대 20자
- **본문 각 줄**: 공백 제외 최대 20자 (모바일 최적화)
- **종결어미**: ~요, ~네요, ~더라고요, ~했어요, ~얌!, ~했어용 ㅎㅎ
- **이모지**: 😌 ✨ 🥹 😆 🤍 🥰 ☺️ 🫶
- **금지 단어**: 결론적으로, 주목할 만한, 이러한, 이를 통해

---

## 라이선스

MIT
