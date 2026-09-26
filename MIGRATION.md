# 옮기는 순서

**6단계 전까지는 지금 사이트(astrojykim.com)에 아무 영향이 없습니다.**
1~5단계는 합쳐서 30분 정도입니다.

---

## 1. 그림 받기 (5분, 맥 터미널)

압축을 푼 폴더에서:

```bash
python3 scripts/fetch_images.py
```

`assets/img/` 아래에 그림 44장이 저장됩니다. Google Site는 아직 고치지 마세요 (그림을 순서로 짝짓습니다).

## 2. GitHub 저장소 만들기 (10분)

1. [github.com](https://github.com) 계정 (무료)
2. **New repository** → 이름은 자유 (예: `astrojykim-site`), **Public**, README 체크 해제
3. 폴더 내용 올리기
   - 웹: 저장소 첫 화면 **uploading an existing file** → 폴더 안의 파일·폴더 전체를 끌어다 놓기 → Commit
     (숨김 폴더 `.github`도 꼭 올라가야 합니다. 웹 업로드에서 빠지면 아래 git 방법으로)
   - 터미널:
     ```bash
     git init -b main && git add -A && git commit -m "Import from Google Sites"
     git remote add origin https://github.com/<계정>/astrojykim-site.git
     git push -u origin main
     ```

## 3. 자동 배포 켜기 (2분)

저장소 **Settings → Pages → Build and deployment → Source: GitHub Actions**

**Actions** 탭에서 *Build and deploy*가 초록불이 되면 끝입니다 (1~2분).
`https://<계정>.github.io/astrojykim-site/` 에서 새 사이트가 보입니다.

## 4. NASA ADS 연결 (5분)

1. [ui.adsabs.harvard.edu](https://ui.adsabs.harvard.edu) 로그인 → Account → **Settings → API Token** → Generate
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ADS_TOKEN`, Secret: 방금 받은 값
3. **Actions → ADS sync → Run workflow**

몇 분 뒤 Pull Request가 하나 열립니다. 새로 추가된 하이라이트를 확인하고 **Merge**하면
Publications 페이지가 채워지고 사이트가 자동으로 다시 배포됩니다. 이후엔 매월 1일 자동입니다.

> 토큰은 파일에 넣지 말고 Secrets에만 두세요.

## 5. 둘러보고 고치기

고칠 곳은 [README.md](README.md)의 표 참고. 저장(Commit)할 때마다 자동 배포됩니다.

---

## 6. 도메인 옮기기 ⚠️ 여기서부터 실제 사이트가 바뀝니다

**먼저** 지금 도메인 관리 화면(가비아·Squarespace·Cloudflare 등, astrojykim.com을 산 곳)의
DNS 설정을 **스크린샷으로 남겨두세요.** 되돌릴 때 필요한 유일한 기록입니다.

1. GitHub 저장소 **Settings → Pages → Custom domain**: `www.astrojykim.com` → Save
2. 도메인 관리 화면에서 Google Sites용 레코드를 지우고 아래로 교체

   | Type | Name | Value |
   |---|---|---|
   | CNAME | `www` | `<계정>.github.io` |
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |

3. 몇 시간(최대 48시간) 뒤 Settings → Pages에서 **Enforce HTTPS** 체크

예전 주소들은 그대로 살아 있습니다: `/research`, `/highlights`, `/members`, `/join-us`, `/contact`,
`/jae-young-kim`, `/2-3m-radio-telescope`은 같은 경로이고, `/home`은 첫 화면으로 넘어갑니다.

**되돌리기**: DNS를 스크린샷대로 돌려놓으면 몇 시간 안에 Google Site로 돌아갑니다.

## 7. Google Site는 3~6개월 그대로 두기

원본 보관용입니다. 도메인은 이미 새 사이트를 가리키므로 방문자 혼선은 없습니다.

---

비용: GitHub 계정·Pages·Actions·HTTPS·ADS API 모두 무료. 도메인 비용만 기존과 같습니다.
