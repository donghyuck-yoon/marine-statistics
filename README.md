# 해양관측 통계 분석실 — 공식 CSV 보관·수동 갱신 (v1.0)

웹사이트: https://donghyuck-yoon.github.io/marine-statistics/

## 보관 방식

**GitHub 기준자료**: 기상자료개방포털에서 받은 공식 일자료의 연도별 CSV가 `data/`에 보관됩니다. 사이트를 열면 자동으로 이 기준자료를 불러옵니다. 기존 스냅샷은 2026-10-20 다운로드, 마지막 관측일 2026-10-19입니다. 현재 API 자동 수집은 사용하지 않습니다.

**수동 CSV 추가**: 사이트에 새로운 `OBS_BUOY_DD_*.csv`, `OBS_CWBUOY_DD_*.csv`를 올리고 **새 공식 CSV 추가 · 이 브라우저에 저장**을 누르면 기존 지점·날짜는 보존하고 중복 날짜는 새 업로드 값으로 교체합니다. GitHub 기준자료와 달라진 일자료만 브라우저 IndexedDB에 저장됩니다. 새로고침·재접속 시 다시 불러옵니다. 지점정보 META CSV도 로컬에 저장할 수 있습니다.

**주의**: 브라우저 IndexedDB 자료는 현재 기기의 브라우저 프로필에만 남습니다. 다른 기기에서 보이지 않고 시크릿 모드/캐시·사이트 데이터 삭제/임시 업무용 PC 초기화 시 없어질 수 있습니다. 필요하면 사이트의 **추가자료 백업/백업 복원**을 이용하세요.

## 모든 기기에서 영구 이용하려면 (권장)

1. [공식 기상자료개방포털](https://data.kma.go.kr/)에서 최신 일자료 CSV를 다운로드합니다.
2. [GitHub 공식 CSV 업로드](https://github.com/donghyuck-yoon/marine-statistics/upload/main/uploads)에 해양기상부이/연안·파고부이 원본 CSV를 추가하고 **Commit changes**를 누릅니다.
3. 기존 [Merge official KMA portal daily CSV](https://github.com/donghyuck-yoon/marine-statistics/actions/workflows/import-portal-daily.yml) 작업이 CSV 유효성을 확인하고, 지점+날짜별 추가·정정 후 `data/manifest.json`을 갱신하고 GitHub Pages 재배포를 요청합니다.
4. 배포 완료 후 다른 PC나 브라우저에서도 최신 공식 자료가 자동으로 나타납니다.

**공식 일자료 자체를 수동 업데이트**하는 것이며, API 시간자료에서 추정한 일평균을 사용하지 않습니다.

## 통계 계산 방식

기존 v0.8 계산식과 기준 해양기상부이 17개 기본 선택을 그대로 유지합니다. 업로드 CSV에 새 해양기상부이 지점이 나타나면 체크해 확장 분석할 수 있고, 확장 분석은 기존 보도자료 재현값과 구별됩니다. 연안·파고부이 공식 73개 모집단과의 완전한 일치는 아직 확인되지 않았습니다.

공공데이터 출처: 기상청 기상자료개방포털. API 인증키나 비공개 자료를 공개 GitHub 저장소에 업로드하지 마세요.
