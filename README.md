# 해양관측 통계 분석실 — Stage 2-A

기존 v0.8 통계 엔진을 유지하고, 정적 일자료 CSV를 GitHub Pages에서 자동 불러옵니다. **이 단계는 기상청 API 자동 갱신이 아닙니다.**

## 데이터 출처

- 기상청 기상자료개방포털: https://data.kma.go.kr/
- 원본 CSV 다운로드 스냅샷: 2026-10-20
- 기상청 제공 자료를 UTF-8 CSV로 인코딩하여 연도별 파일로 분리했습니다. 관측값은 변경하지 않았습니다.
- 홈페이지는 GitHub 저장소와 동일 출처에서만 데이터를 요청하며, API 키를 사용하지 않습니다.
- 지점명/해역 중 일부는 기존 v0.8에 내장된 잠정 분류입니다. 연안·파고부이 73개 공식 선정 기준 재현을 주장하지 않습니다.

## GitHub Pages 배포

1. 사용자 계정에 새 **Public** 저장소 `marine-statistics` 생성. 기존 개인 홈페이지 저장소를 수정하지 않습니다.
2. 이 폴더 내용(압축파일 자체가 아니라 `index.html`, `data/`, `.nojekyll` 등)을 저장소 루트에 업로드 또는 `git push`합니다.
3. GitHub **Settings → Pages → Build and deployment → Deploy from a branch** 에서 `main`과 `/ (root)` 설정 후 Save.
4. Pages 주소 `https://donghyuck-yoon.github.io/marine-statistics/` 로 접속해 자동 데이터 읽기 결과 확인.
5. 기존 2026년 여름철 수온 `24.3℃` · 최근 10년 `1위`와 2026년 10월 동일기간 비교 결과가 유지되는지 검사.

## 구조

- `index.html` — v0.8 통계 엔진 + 자동 자료 로딩 어댑터
- `data/manifest.json` — 관측자료 목록, 관측 종료일, 해시, 연도별 행수
- `data/marine/YYYY.csv` — 해양기상부이 연도별 관측값
- `data/coastal/YYYY.csv` — 연안·파고부이 연도별 관측값
- `.nojekyll` — GitHub Pages 정적파일 그대로 게시

## 주의

- 자동 로딩 실패 시 수동 CSV 업로드 가능.
- Pages 공개 저장소에 업로드한 데이터는 누구나 조회할 수 있습니다. 기상청 공개자료 재배포 가능 범위 및 기관 보안정책을 확인하십시오.
- **API 키를 저장소·HTML·자료 파일에 추가하지 마세요.** 2-B 검증 후 새 키를 GitHub Actions Secrets에 설정할 계획입니다.
- 자동으로 하루마다 갱신하지 않습니다. 현재는 초기 스냅샷입니다.
- 파일을 `file://`로 여는 경우 브라우저 보안정책상 자동 fetch가 차단될 수 있습니다. 로컬 시험은 `python -m http.server 8000` 실행 후 `http://localhost:8000`에 접속합니다.
