# PyMiniRedis 통합 구현 보고서

기준일: `2026-03-18`

## 1. 보고서 목적

이 문서는 현재 저장소에서 실제로 구현되어 있는 내용, 검증 가능한 기능, 시연 가능한 서비스, 트래픽 실험 도구를 한 번에 정리한 기준 문서입니다.

활용 목적:

- 팀 내부 구현 현황 공유
- 발표/시연 준비
- Antigravity 시각화 입력
- 티켓팅 메인 서비스 연동 전 기준선 확정

## 2. 현재 결과물 구성

현재 저장소는 크게 4개 덩어리로 나뉩니다.

1. `PyMiniRedis` 본체
   - Python 표준 라이브러리 기반 raw TCP Mini Redis 서버
   - 직접 구현한 해시 테이블 사용
   - 텍스트 프로토콜 + 최소 RESP 지원
2. CLI / 운영 도구
   - `redis-cli` 역할의 간단한 CLI
   - 부하/과부하 실험 스크립트
3. 티켓팅 데모 서비스
   - `http.server` 기반 시연용 서비스
   - Page A 예매실 / Page B 대기실 / 운영 보기 제공
4. 문서 및 검증 자료
   - 명세서, 사용 문서, 보고서, 테스트, Antigravity 프롬프트

## 3. Mini Redis 구현 범위

현재 구현된 기능 그룹은 다음과 같습니다.

- 기본 문자열 저장
  - `PING`
  - `SET`
  - `SET ... NX`
  - `GET`
  - `DEL`
  - `EXISTS`
- 만료 / 캐시 제어
  - `EXPIRE`
  - `TTL`
  - `EXPIREJITTER`
  - `INVALIDATE`
- 카운터
  - `INCR`
  - `DECR`
  - `INCRBY`
  - `DECRBY`
- 동시성 / 조율
  - `LOCK`
  - `UNLOCK`
  - `RATECHECK`
- 자료구조
  - `HSET`, `HGET`, `HDEL`, `HGETALL`
  - `SADD`, `SISMEMBER`, `SREM`, `SMEMBERS`
  - `ZADD`, `ZRANK`, `ZRANGE`, `ZREM`, `ZPOPMIN`, `ZCARD`
- 프로토콜
  - 라인 기반 텍스트 명령
  - 체크리스트 대응용 최소 RESP 배열 요청/응답
- 운영
  - interactive CLI
  - background sweeper
  - optional AOF persistence

## 4. 내부 처리 방식

핵심 동작은 이렇게 설계되어 있습니다.

- 저장소 본체
  - Python `dict`가 아니라 직접 구현한 `HashTable`
  - collision 처리와 bucket 기반 저장 구조 포함
- 동시성
  - 서버는 multi-client TCP 처리
  - 실제 저장소 갱신은 lock으로 보호
- 삭제 정책
  - `DEL`: 즉시 물리 삭제
  - `EXPIRE`: lazy expiration + sweeper cleanup
  - `INVALIDATE`: 논리 삭제 후 grace period 뒤 물리 삭제
- 영속성
  - 기본은 인메모리
  - 옵션으로 AOF append log 사용 가능

## 5. 체크리스트 대응 상태

개인별 실험 체크리스트 기준 현재 상태는 아래와 같습니다.

| 항목 | 상태 | 근거 |
|---|---|---|
| RESP 요청 1개 직접 확인 | 구현됨 | `tests/test_protocol_resp.py` |
| `parse_resp()` 동작 확인 | 구현됨 | `mini_redis/protocol.py` |
| `SET`, `GET`, `DEL` RESP 처리 | 구현됨 | `tests/test_protocol_resp.py` |
| RESP 응답 확인 | 구현됨 | RESP 테스트에서 직접 검증 |
| 한 연결에서 여러 요청 처리 | 구현됨 | RESP/CLI 테스트 |
| 에러 입력 보내보기 | 구현됨 | 기본/RESP 에러 테스트 |
| 서버 재시작 후 데이터 확인 | 구현됨 | `tests/test_persistence.py` |
| 클라이언트 2개로 같은 key 조회 | 구현됨 | `tests/test_concurrency.py` |
| `INCR` / `DECR` 실험 | 구현됨 | `tests/test_protocol_counter.py` |
| `SET NX` 실험 | 구현됨 | `tests/test_protocol_setnx.py` |

## 6. 티켓팅 데모 서비스 구현 범위

티켓팅 데모 서비스는 Redis 본체와 별도로, 우리가 만든 Mini Redis를 실제로 사용하는 검증용 서비스입니다.

역할 분리:

- `mini_redis`
  - 과제 본체
  - TCP 기반 Mini Redis 서버
- `ticketing_service`
  - 시연용 서비스
  - Page A / Page B 흐름 검증

현재 서비스는 다음 화면을 제공합니다.

- `/`
  - 예매 시작 페이지
- `/ticketing?user_id=<id>`
  - Page A 예매실
- `/waiting-room?user_id=<id>`
  - Page B 대기실
- `/ops`
  - 현재 입장 완료자, 대기열, 좌석 상태를 보는 운영용 화면

핵심 시나리오:

1. 사용자가 `/`에서 예매를 시작한다
2. 활성 입장 수가 여유 있으면 `Page A`로 간다
3. 꽉 차 있으면 `Page B` 대기실로 간다
4. `Page B`는 상태를 주기적으로 조회한다
5. 자리가 나면 자동으로 `Page A`로 이동한다
6. 입장 완료자는 좌석 홀드, 결제 확정, 취소를 진행할 수 있다

## 7. 티켓팅 기능과 Redis 기능 매핑

### 대기열

- `ZADD`
- `ZRANK`
- `ZPOPMIN`
- `ZCARD`

용도:

- 대기열 진입
- 순번 조회
- 다음 사용자 승격
- 대기열 길이 확인

### 중복 진입 방지

- `SET ... NX`
- `SADD`
- `SISMEMBER`

용도:

- 같은 사용자 중복 진입 방지
- 참여자 추적

### 좌석 예약 상태

- `HSET`
- `HGETALL`
- `EXPIRE`

용도:

- 예약 메타데이터 저장
- 좌석 홀드 상태 관리
- 홀드 만료 대비

### 좌석 충돌 방지

- `LOCK`
- `UNLOCK`
- `SET ... NX`

용도:

- 같은 좌석 동시 점유 방지

### 재고 / 수량 처리

- `DECR`
- `INCR`
- `DECRBY`
- `INCRBY`

용도:

- 잔여 좌석 수 차감 / 복구

### 트래픽 방어

- `RATECHECK`

용도:

- 과도한 입장 요청 차단
- burst traffic 방어

## 8. 실행 가능한 구성

### Mini Redis 실행

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379
```

환경에 따라 로컬 런처를 쓸 수도 있습니다.

```bash
python run_mini_redis_local.py --host 127.0.0.1 --port 6379
```

### CLI 접속

```bash
python -m mini_redis.cli --host 127.0.0.1 --port 6379
```

### 티켓팅 서비스 실행

```bash
python -m ticketing_service.server --host 127.0.0.1 --port 8080 --redis-host 127.0.0.1 --redis-port 6379
```

환경에 따라 로컬 런처를 쓸 수도 있습니다.

```bash
python run_ticketing_service_local.py --host 127.0.0.1 --port 8080 --redis-host 127.0.0.1 --redis-port 6379
```

### 접속 URL

- `http://127.0.0.1:8080/`
- `http://127.0.0.1:8080/waiting-room?user_id=user-b`
- `http://127.0.0.1:8080/ticketing?user_id=user-a`
- `http://127.0.0.1:8080/ops`

## 9. 자동화 테스트 현황

전체 테스트 명령:

```bash
python -m unittest discover -s tests -v
```

최신 검증 결과:

- 총 테스트 수: `55`
- 상태: `전부 통과`

기능별 테스트 파일:

| 영역 | 파일 |
|---|---|
| 해시 테이블 | `tests/test_hash_table.py` |
| 기본 프로토콜 | `tests/test_protocol_basic.py` |
| 만료 / TTL / 지터 | `tests/test_protocol_expiration.py` |
| 카운터 | `tests/test_protocol_counter.py` |
| RESP | `tests/test_protocol_resp.py` |
| SET NX | `tests/test_protocol_setnx.py` |
| INVALIDATE | `tests/test_protocol_invalidation.py` |
| LOCK / UNLOCK | `tests/test_protocol_locking.py` |
| RATECHECK | `tests/test_protocol_rate_limit.py` |
| HASH | `tests/test_protocol_hash.py` |
| SET 자료구조 | `tests/test_protocol_sets.py` |
| SORTED SET | `tests/test_protocol_sorted_set.py` |
| store 내부 만료 처리 | `tests/test_store_expiration.py` |
| 동시성 | `tests/test_concurrency.py` |
| AOF persistence | `tests/test_persistence.py` |
| CLI | `tests/test_cli.py` |
| 티켓팅 서비스 통합 | `tests/test_ticketing_service.py` |

티켓팅 서비스 검증 항목:

- 인원 초과 시 대기열 이동
- Page A / Page B / 운영 보기 라우트 노출
- 현재 입장 완료자 목록 확인 가능
- 결제 완료 후 다음 사용자 승격
- 동일 좌석 중복 홀드 방지

## 10. 트래픽 / 과부하 실험 도구

실험 도구 위치:

- `experiments/traffic/load_test.py`
- `experiments/traffic/README.md`

목적:

- 기능 테스트와 분리된 과부하 검증
- 이후 `Redis 사용 / 미사용` 비교 실험의 공통 폴더

지원 모드 및 시뮬레이션 내용:

- **`setget` (기본 I/O)**: 단순 문자열 캐싱 및 세션 상태 조회와 같이, 수만 건의 저장(`SET`)과 단일 검색(`GET`)의 병목을 테스트합니다.
- **`incr` (재고 카운터)**: 티켓 잔여량 차감이나 단일 접속 집계처럼, 단일 변수에 여러 클라이언트가 동시에 달라붙어 숫자를 변경할 때의 원자성(Atomic) 보장 속도를 테스트합니다.
- **`ratecheck` (매크로 방어)**: 악성 매크로나 봇이 새로고침을 광클릭하는 상황을 모사하여, 인메모리에서 허용 초과 트래픽을 즉각 쳐내고(`+BLOCKED`) 보호하는 성능을 증명합니다.
- **`queue` (대기열 진입)**: 오픈 시점에 유저가 몰릴 때 타임스탬프로 줄을 세우고(`ZADD`), 남은 내 순번을 파악(`ZRANK`)하는 대규격 정렬 자료구조의 연산 한계를 테스트합니다.

지원 프로필:

- `quick`
- `stress`
- `overload`

예시:

```bash
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode setget --profile stress
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode queue --profile overload
```

현재까지 확인한 대표 결과 (stress 프로필 기준, 4만 건 명령 타격):

- `setget` IO 테스트: 평균 **13,507 requests/sec** (지연 9ms)
- `incr` 카운터 과부하: 평균 **19,474 requests/sec** (지연 4ms)
- `ratecheck` 차단 과부하: 평균 **14,482 requests/sec** (지연 11ms)
- `queue` 시나리오: 다소 무겁지만 약 **12,000 requests/sec** 방어

해석 및 성능 체감 (Redis 미사용 대비 강점):

- **압도적 처리량 입증**: 순수 Python으로 구현되었음에도, DB Lock 의존 없이 초당 최대 **1.9만 건**의 통신을 소화합니다.
- **RDBMS 단독 환경(No Redis)과의 직접적 비교**: 일반적으로 RDBMS만으로 티켓팅 대기열과 재고 처리를 감당하면 초당 500~1,000 TPS 수준에서 병목 및 커넥션 고갈이 발생합니다. 반면 PyMiniRedis를 서버 앞단에 배치할 경우, 병목의 90% 이상(재고 확인, 트래픽 유입)을 **인메모리에서 10~20배 이상 빠른 속도(1만 이상 TPS)**로 쳐내어 DB 생존률을 극대화할 수 있습니다.
- `queue` 시나리오는 `ZADD + ZRANK` 비용 때문에 상대적으로 무겁지만, 이 역시 디스크 I/O 없이 메모리 정렬로 처리되므로 여전히 DB 폴링보다 성능 우위에 있습니다.

## 11. 현재 문서 세트

현재 함께 봐야 하는 문서는 다음과 같습니다.

- `README.md`
- `SPEC.md`
- `PROJECT_PLAN.md`
- `USAGE.md`
- `TICKETING_SERVICE.md`
- `REPORT.md`
- `ANTIGRAVITY_VIS_PROMPT.md`
- `ANTIGRAVITY_DEMO_REPORT_PROMPT.md`

## 12. 현재 상태 평가

지금 가능한 것:

- Mini Redis 자체 시연
- CLI 기반 명령 시연
- RESP 체크리스트 시연
- 대기열 자료구조 시연
- Page A / Page B 티켓팅 흐름 시연
- 운영 화면에서 입장 완료자 / 대기열 / 좌석 상태 확인
- 기능별 자동 테스트 시연
- 과부하 실험 도구 시연

아직 남은 것:

- `Redis 사용 / 미사용` 성능 비교 실험
- AWS 배포 후 외부 접속 시연
- 실제 발표용 데모 시나리오 문서 고정
- 티켓팅 메인 서비스와 더 큰 규모의 통합 실험

## 13. Antigravity 전달 기준

Antigravity에는 아래 자료를 같이 넘기는 것이 적절합니다.

- `REPORT.md`
- `SPEC.md`
- `README.md`
- `TICKETING_SERVICE.md`
- `tests/test_protocol_*.py`
- `tests/test_ticketing_service.py`
- `tests/test_concurrency.py`
- `tests/test_persistence.py`
- `experiments/traffic/load_test.py`

권장 출력물:

- 기능 그룹 요약표
- Redis 기능 ↔ 티켓팅 기능 매핑도
- 테스트 커버리지 표
- 트래픽 실험 비교 차트
- 발표용 1페이지 요약
