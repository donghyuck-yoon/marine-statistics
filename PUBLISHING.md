# 새 GitHub 저장소에 올리기

개인 홈페이지 저장소를 수정하지 않으려면 새 **public** 저장소 `marine-statistics`를 먼저 만들어야 합니다.

### 웹 브라우저만 사용하는 방법

1. GitHub에서 + → New repository → `marine-statistics` → Public → Create repository.
2. 본 ZIP을 압축 해제하고, 해제한 폴더의 **내용 전체**를 선택해 GitHub의 Add file → Upload files에 드래그합니다. `index.html` 및 `data/` 디렉터리가 저장소 최상위에 와야 합니다. 100개 이상은 한 번에 업로드하지 마세요.
3. Commit changes.
4. Settings → Pages → Source: Deploy from a branch → Branch `main`, Folder `/ (root)` → Save.
5. 잠시 후 Pages 주소를 열고 데이터 자동 로딩 완료를 확인합니다.

### git 명령으로 올리는 방법 (git 설치 PC)

압축해제 후 `marine-statistics_stage2a` 폴더 내에서 터미널을 열고 아래 명령을 실행하세요.

```bash
git init -b main
git add .
git commit -m "Stage 2-A: hosted observational data and automatic loading"
git remote add origin https://github.com/donghyuck-yoon/marine-statistics.git
git push -u origin main
```

기존 코드나 데이터에 API 키를 절대 붙여 넣지 마세요.
