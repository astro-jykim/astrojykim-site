# astrojykim.com

UNIST 김재영 연구그룹 웹사이트. Google Sites에서 옮겨온 GitHub Pages 사이트입니다.

- **처음 설정** → [MIGRATION.md](MIGRATION.md) (30분 정도)
- **그림 넣기** → [IMAGES.md](IMAGES.md)
- **원문에서 바뀐 문구 목록** → [CHANGES.md](CHANGES.md)

---

## 어디를 고치면 되나

| 고치고 싶은 것 | 파일 |
|---|---|
| 페이지 글 (Research, Join Us, Contact, 약력, 망원경) | `content/<페이지>.md` |
| Highlights (순서 = 화면 순서) | `data/highlights.yml` |
| 구성원 | `data/members.yml` |
| 메뉴 순서, 사이트 제목, 홈에 보일 하이라이트 개수 | `data/site.yml` |
| 한국어 모집 안내 | `content/ko.md` |
| 색·글꼴 | `assets/css/site.css` |

GitHub 웹에서 파일을 열고 연필 아이콘으로 고친 뒤 **Commit changes**를 누르면
1~2분 뒤 사이트에 반영됩니다. Claude에게 "members.yml에 누구 추가해줘"라고 해도 됩니다.

### 자주 하는 일

**학생이 들어왔을 때** — `data/members.yml`에서 해당 그룹에 한 사람 복사해서 붙이기:

```yaml
  - name: Gildong Hong
    detail: 홍길동, UNIST
    period: since Mar 2027
    topic: What the student works on
```

화면에는 원래 사이트와 똑같이 `Gildong Hong (홍길동, UNIST), since Mar 2027`로 나옵니다.

**졸업했을 때** — 그 항목을 잘라서 `Alumni` 그룹에 붙이고 `detail`, `period`만 고치기.

**논문이 나왔을 때** — 매월 1일 ADS 동기화가 새 논문을 찾아 Pull Request를 엽니다.
확인하고 Merge만 하면 됩니다. 급하면 Actions 탭 → **ADS sync** → Run workflow.

**그림을 바꿀 때** — 같은 이름의 파일로 올리면 끝. [IMAGES.md](IMAGES.md)

### 글 쓸 때 알아둘 것 (Markdown)

- `## 제목` 섹션 제목, `- ` 목록, `[글자](주소)` 링크
- `- 2024-2026 | 내용` 처럼 ` | `로 나누면 약력처럼 연도·내용 두 칸으로 나옵니다
- `![캡션](research/foo.jpg)` 그림. 캡션을 쓰면 그림 아래에 표시됩니다
- 본문에 `<`를 쓸 때는 `&lt;`로 (예: `(&lt;hour)`). `<`가 HTML로 읽히는 걸 막기 위해서입니다

---

## 내 컴퓨터에서 미리 보기

```bash
pip install -r requirements.txt
python3 build.py
python3 -m http.server -d _site 8000     # 브라우저에서 http://localhost:8000
```

`python3 scripts/check_completeness.py`는 원래 사이트의 모든 문장·링크가 새 사이트에
그대로 있는지 대조합니다 (배포할 때마다 자동으로도 돌아갑니다).

---

## 구조

```
content/          페이지 글 (Markdown)
data/             highlights.yml, members.yml, site.yml, publications.yml(자동 생성)
templates/        페이지 틀 (HTML)
assets/css/       스타일
assets/img/       그림 — highlights/<id>.jpg, research/, telescope/, banners/, ...
build.py          사이트 생성 (content + data → _site/)
scripts/
  fetch_images.py       현재 Google Site의 그림을 원본 해상도로 받기
  sync_ads.py           NASA ADS → 논문 목록·새 하이라이트
  check_completeness.py 원문 대조
  migration/            1회용 이전 스크립트 (다시 실행하지 마세요)
_originals/       Google Site 원문 스냅샷 (2026-09-26). 수정 금지 — 대조 기준입니다
.github/workflows/ 자동 배포, 월간 ADS 동기화
```

## 왜 Google Sites에서 옮겼나

Google Sites(신버전)에는 편집용 API가 없어서 논문 목록 갱신 같은 자동화를 붙일 수 없습니다.
여기서는 사이트 전체가 텍스트 파일이라 변경 이력이 남고, 자동화가 되고, Claude가 직접 고칠 수
있습니다. 호스팅 비용은 여전히 0원입니다.
