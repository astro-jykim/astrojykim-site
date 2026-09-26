# 그림 넣기

설정 파일은 건드리지 않고 **파일 이름만 맞춰서 넣으면** 됩니다.
파일이 없으면 그 자리에 파일 이름이 적힌 자리표시가 나오므로, 뭘 넣어야 하는지 화면에서 바로 보입니다.

## 1. 지금 사이트의 그림 가져오기 (한 번만)

Google Site에 있는 그림 44장(하이라이트 20, 망원경 사진 10, 페이지 배너 7, 로고 등)을
**원본 해상도로** 받아 올바른 이름으로 저장합니다. 설치할 것 없습니다.

```bash
cd astrojykim-site
python3 scripts/fetch_images.py
```

- Google Site를 **고치기 전에** 실행하세요. 그림을 페이지 안 순서로 짝지어 이름을 붙입니다
- 구글 그림 주소는 시간이 지나면 만료되기 때문에, 이 스크립트는 실행할 때마다 페이지를 새로 읽습니다
- 페이지 구조가 달라져 개수가 안 맞으면 멈추지 않고 `extra-1.jpg` 같은 이름으로 따로 저장한 뒤 알려줍니다

## 2. 그림 추가·교체

| 넣을 곳 | 파일 이름 |
|---|---|
| 하이라이트 카드 | `assets/img/highlights/<id>.jpg` — `<id>`는 `data/highlights.yml`의 `id` |
| 페이지 배너 | `assets/img/banners/<페이지>.jpg` (예: `research.jpg`) |
| 본문 그림 | Markdown에 쓴 이름 그대로 (예: `assets/img/research/effelsberg.jpg`) |
| 약력 사진 | `assets/img/about/profile.jpg` |
| 로고 | `assets/img/site/logo.png` |

`.jpg` 대신 `.png`, `.webp`도 됩니다. 같은 이름으로 올리면 교체되고, 이전 파일은 Git 이력에 남아서 되돌릴 수 있습니다.

**GitHub 웹에서**: 폴더를 열고 **Add file → Upload files**로 끌어다 놓기 → Commit.

**Claude에게**: 그림을 첨부하고 "eht2025 하이라이트 그림으로 넣어줘".

## 3. 본문에 새 그림 넣기

```markdown
![Picture: Effelsberg 100-m radio telescope. Credit: Dr. Schorsch](research/effelsberg.jpg)
```

`[ ]` 안의 글이 그림 아래 캡션이 됩니다. 크레딧은 여기에 적으세요.
여러 장을 격자로 보이려면 `<div class="gallery" markdown="1">` … `</div>`로 감쌉니다
(`content/2-3m-radio-telescope.md`의 Pictures 부분 참고).

## 권장 크기

하이라이트 카드는 가로 1200~1600px, 파일당 1MB 안쪽이면 충분합니다.
큰 파일은 macOS에서 `sips -Z 1600 파일.jpg`로 줄일 수 있습니다.
