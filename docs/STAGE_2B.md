# 2-B: 기상청 API 정합성 검증 (읽기 전용)

현재 GitHub Pages 통계 웹사이트와 2017–2026년 관측자료는 변경하지 않습니다.

## 검증 API
- 해양기상월보 **일별(부이)기상자료조회**: SeaMtlyInfoService/getDailyBuoy
- 해양기상월보 **일별(파고부이)기상자료조회**: SeaMtlyInfoService/getDailyWaveBuoy
- 공식 문서: https://apihub.kma.go.kr/apiList.do?seqApi=3

**주의:** 위 API의 year/month는 월보 '발표년도·발표월'로 기술되어 있습니다. 따라서 포털 최신 일자료와 동일한지 확인하지 않고 자동 갱신에 사용하면 안 됩니다.

## 최초 설정 (사용자)
1. 기존에 채팅에 공유한 키 대신 API허브에서 새 인증키를 발급하고, 해당 API의 활용승인을 확인하세요.
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret.
3. Name = KMA_API_KEY, Secret = 새 인증키. **코드나 공개 저장소에 키를 입력하지 마세요.**
4. Actions → **Verify KMA marine API (read-only)** → Run workflow.
5. 실행 로그와 Artifacts의 api-probe-report.json을 확인하고 성공 또는 실패를 알려주세요.

검증은 덕적도(22101)와 독도(22441)의 2025-09, 2026-09, 2026-10 일자료를 읽어 현재 GitHub의 원본 CSV와 비교합니다.
평균수온 일치 판정은 공통 5일 이상, ±0.11°C 이내 일치율 95% 이상입니다.
2026-10은 미완성 월이므로 진단용으로만 사용합니다.

실패해도 **data/**, **manifest.json**, **index.html**은 절대 수정하지 않습니다.
기준을 통과한 후에만 자동 갱신 방식(원자료 병합·이상치/결측 검사·manifest 갱신·예약 실행)을 설계합니다.
