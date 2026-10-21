# 공식 기상자료개방포털 일자료 반자동 갱신 (Stage 2-C)

이 폴더에 **기상자료개방포털에서 내려받은 일자료 CSV만** 업로드하세요.

- 해양기상부이: `OBS_BUOY_DD_*.csv`
- 연안·파고부이: `OBS_CWBUOY_DD_*.csv`

직접 CSV를 수정하거나 머리글을 바꾸지 말아주세요. 파일 인코딩은 원본 CP949 또는 UTF-8 모두 지원합니다.
업로드한 원본 CSV는 GitHub Actions가 검증 후 연도별 `data/` 파일과 `data/manifest.json`을 갱신하고, 처리된 원본은 `uploads/` 디렉터리에서 삭제합니다. 원본 파일은 Git 기록에 남을 수 있으니 공개 데이터 외 파일은 올리지 마세요.

### 사용 순서
1. [해양기상부이 일자료](https://data.kma.go.kr/data/sea/selectBuoyRltmList.do?pgmNo=52), [파고부이 일자료](https://data.kma.go.kr/data/sea/selectFargoBuoyRltmList.do?pgmNo=55)에서 유형을 **일**로 설정하고 최신 기간을 CSV로 내려받습니다.
2. [이 폴더에 파일 업로드](https://github.com/donghyuck-yoon/marine-statistics/upload/main/uploads)에서 두 원본 CSV를 **압축하지 않은 채** 첨부합니다. 원본이 한 종류뿐이면 하나만 올려도 됩니다.
3. 아래 **Commit changes** 클릭.
4. [Actions - Merge official KMA portal daily CSV](https://github.com/donghyuck-yoon/marine-statistics/actions/workflows/import-portal-daily.yml)에서 실행이 **success**인지 확인합니다.
5. [해양관측 통계 분석실](https://donghyuck-yoon.github.io/marine-statistics/)을 새로고침하고 왼쪽 **관측자료 자동 로딩 완료**에서 마지막 관측일을 확인합니다.

### 안전 장치
- 공식 열 이름, 일자료 형태, 지점번호·날짜·숫자값 검증
- 지점번호+날짜 기준으로 추가·정정·중복 제거
- 업로드에 없는 기존 관측 날짜와 지점 값은 유지
- 포털 원자료의 기존 이상치나 품질관리값을 임의 수정하지 않음
- 잘못된 파일이 있으면 전체 병합 실패하며 공개 데이터는 그대로 유지
- 재실행 및 원본 중복 업로드 가능
- 10년 전체 다운로드도 가능하지만 매번은 최근 수개월만 받아도 됨. 과거 정정치 반영은 해당 과거 기간을 다시 다운로드해야 함.

### 자동 다운로드 관련
현재 공개된 공식 웹 안내는 UI CSV 내려받기를 명시하지만, 외부에서 인증 없이 사용할 수 있는 기상자료개방포털 CSV 직접 다운로드 API는 아직 검증되지 않았습니다. 이 자동화는 기존 포털 다운로드를 대체하지 않으며, 사용자가 CSV를 올릴 때만 동작합니다.

원본 출처: 기상청 기상자료개방포털. API 인증키는 올리지 마세요.
