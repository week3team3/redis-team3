# Antigravity Test Visualization Prompt

다음 저장소의 테스트/부하 결과를 시각화해줘.

프로젝트:
- `C:\Users\cedis\Downloads\refis_project`

목표:
- PyMiniRedis의 기능 테스트 결과와 트래픽 테스트 결과를 한눈에 설명할 수 있는 시각 자료를 만든다.
- 메인 서비스 계획인 `티켓팅 사이트 + 대기열 시스템`에 어떤 Redis 기능이 대응되는지 같이 설명할 수 있어야 한다.
- 발표/데모용으로 바로 사용할 수 있어야 한다.

참고 문서:
- `SPEC.md`
- `PROJECT_PLAN.md`
- `README.md`
- `USAGE.md`
- `REPORT.md`

참고 테스트 파일:
- `tests/test_protocol_basic.py`
- `tests/test_protocol_expiration.py`
- `tests/test_protocol_counter.py`
- `tests/test_protocol_resp.py`
- `tests/test_protocol_setnx.py`
- `tests/test_protocol_invalidation.py`
- `tests/test_protocol_locking.py`
- `tests/test_protocol_rate_limit.py`
- `tests/test_protocol_hash.py`
- `tests/test_protocol_sets.py`
- `tests/test_protocol_sorted_set.py`
- `tests/test_concurrency.py`
- `tests/test_persistence.py`
- `tests/test_cli.py`

참고 부하 스크립트:
- `scripts/load_test.py`

원하는 산출물:
- 기능별 테스트 현황 표
- 기능 분류 다이어그램
- 티켓팅 서비스 계획과 Redis 기능 매핑 요약
- 트래픽 테스트 결과 시각화
- `setget`, `incr`, `ratecheck`, `queue` 모드 비교 차트
- 발표용 한 페이지 요약 이미지 또는 Markdown 리포트
- `REPORT.md` 내용을 보완하는 발표용 요약본

반영했으면 하는 시각화 항목:
- 기능 카테고리별 테스트 개수
- 프로토콜 기능 목록과 상태
- RESP 체크리스트 완료 상태
- 동시성 테스트와 일반 기능 테스트 구분
- 대기열/예약/재고/방어 관점에서 기능 그룹핑
- 부하 테스트의 `avg_pair_latency_ms`, `p95_pair_latency_ms`, `throughput_cmd_per_sec`
- 모드별 성공/실패 비교

출력 형식:
- 우선 `Markdown 리포트`
- 가능하면 차트용 CSV 또는 Mermaid/ASCII 차트도 함께

주의:
- 구현 코드를 바꾸지 말고, 시각화와 정리만 수행
- 문서는 현재 저장소 기준 최신 상태를 따를 것
