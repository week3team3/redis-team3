# Antigravity Demo Report Prompt

다음 저장소를 기준으로, 팀원이 그대로 따라 하면 기능 시현과 기능 테스트를 동시에 할 수 있는 `시현 보고서`를 작성해줘.

프로젝트 경로: 
- `C:\Users\cedis\Downloads\refis_project`

목표:
- PyMiniRedis의 핵심 기능을 팀원에게 직접 시현할 수 있는 실습형 보고서를 만든다.
- 보고서에 적힌 명령어를 순서대로 그대로 입력하면, 기능이 실제로 동작하는지 검증할 수 있어야 한다.
- 체크리스트 항목이 모두 어디서 검증되는지도 연결해줘.

반드시 참고할 문서:
- `SPEC.md`
- `USAGE.md`
- `PROJECT_PLAN.md`
- `REPORT.md`
- `README.md`

반드시 참고할 테스트 파일:
- `tests/test_protocol_basic.py`
- `tests/test_protocol_resp.py`
- `tests/test_protocol_setnx.py`
- `tests/test_protocol_counter.py`
- `tests/test_protocol_expiration.py`
- `tests/test_protocol_locking.py`
- `tests/test_protocol_rate_limit.py`
- `tests/test_protocol_hash.py`
- `tests/test_protocol_sets.py`
- `tests/test_protocol_sorted_set.py`
- `tests/test_concurrency.py`
- `tests/test_persistence.py`

반드시 반영할 체크리스트:
- RESP 요청 1개 직접 확인
- `parse_resp()` 동작 확인
- `SET`, `GET`, `DEL` RESP 처리
- RESP 응답 확인
- 한 연결에서 여러 요청 처리
- 에러 입력 보내보기
- 서버 재시작 후 데이터 확인
- 클라이언트 2개로 같은 key 조회
- `INCR` / `DECR` 실험
- `SET NX` 실험

원하는 산출물 형식:
- 파일명 제안: `DEMO_REPORT.md`
- 한국어 작성
- 발표/실습 겸용 문서
- 명령어와 예상 출력값을 모두 포함
- 각 단계 끝에 “무엇을 확인한 것인지”를 짧게 설명

반드시 포함할 섹션:
1. 준비물
2. 서버 실행 방법
3. CLI 접속 방법
4. 체크리스트 기반 시현 순서
5. RESP 직접 실험 방법
6. 동시성/공유 상태 실험 방법
7. 재시작/AOF 실험 방법
8. 티켓팅/대기열 기능 시현 예시
9. 실패 시 점검 포인트

문서 작성 규칙:
- 각 단계는 복붙 가능한 명령어 블록으로 작성
- PowerShell 기준으로 작성
- 필요하면 터미널 A / 터미널 B를 나눠서 표시
- RESP 실험은 raw RESP payload를 직접 보내는 예시를 꼭 포함
- `SET NX`, `DECR`, `ZADD/ZRANK`, `LOCK/UNLOCK`, `RATECHECK`는 반드시 시연 흐름에 포함
- 티켓팅/대기열 관점에서 왜 이 기능이 필요한지도 짧게 연결
- 코드 수정은 하지 말고, 문서화와 정리만 수행

좋은 출력 예시 방향:
- “1단계: 서버 실행”
- “2단계: CLI로 기본 명령 확인”
- “3단계: RESP raw 요청 보내기”
- “4단계: SET NX로 중복 방지 확인”
- “5단계: INCR/DECR로 재고 변경 확인”
- “6단계: ZSET으로 대기열 순번 확인”
- “7단계: LOCK으로 좌석 점유 경쟁 확인”
- “8단계: RATECHECK으로 트래픽 방어 확인”

추가 요청:
- 마지막에 “4분 발표용 시연 축약 버전”도 따로 정리해줘.
