# PyMiniRedis

Python 표준 라이브러리만으로 구현한 TCP/IP 기반 Mini Redis입니다. 웹 프레임워크를 쓰지 않고, 직접 구현한 해시 테이블을 저장소 본체로 사용합니다.

`redis-cli`처럼 바로 붙어서 명령을 입력할 수 있는 CLI도 포함합니다. 메인 목표는 이후 `티켓팅 사이트 + 대기열 시스템`에서 사용할 Redis 대체 서버를 직접 구현하고 검증하는 것입니다.

현재는 `Page A 예매실 / Page B 대기실 / 운영 보기(/ops)`가 있는 티켓팅 데모 서비스까지 붙어 있습니다.

현재는 기존 라인 기반 텍스트 프로토콜에 더해, 체크리스트 검증용 최소 `RESP` 배열 요청과 `RESP` 형식 응답도 지원합니다.

## 현재 기능

- `PING`
- `SET <key> <value>`
- `SET <key> <value> NX`
- `GET <key>`
- `DEL <key>`
- `EXISTS <key>`
- `EXPIRE <key> <seconds>`
- `TTL <key>`
- `EXPIREJITTER <key> <seconds> <jitter_seconds>`
- `INCR <key>`
- `DECR <key>`
- `INCRBY <key> <amount>`
- `DECRBY <key> <amount>`
- `INVALIDATE <key> [reason]`
- `LOCK <key> <owner> <ttl_seconds>`
- `UNLOCK <key> <owner>`
- `RATECHECK <key> <limit> <window_seconds>`
- `HSET`, `HGET`, `HDEL`, `HGETALL`
- `SADD`, `SISMEMBER`, `SREM`, `SMEMBERS`
- `ZADD`, `ZRANK`, `ZRANGE`, `ZREM`, `ZPOPMIN`, `ZCARD`
- `QUIT`
- background sweeper
- optional AOF persistence

## 실행

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379
```

AOF까지 켜려면:

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379 --aof-path data/appendonly.aof
```

CLI 접속:

```bash
python -m mini_redis.cli --host 127.0.0.1 --port 6379
```

프롬프트에서 바로 입력:

```text
127.0.0.1:6379> PING
+PONG
127.0.0.1:6379> SET hello world
+OK
127.0.0.1:6379> GET hello
$world
```

## 문서

- 구현 기준 명세: [SPEC.md](SPEC.md)
- 메인 서비스 계획: [PROJECT_PLAN.md](PROJECT_PLAN.md)
- 사용 예제와 운영 방법: [USAGE.md](USAGE.md)
- 티켓팅 데모 서비스 실행 가이드: [TICKETING_SERVICE.md](TICKETING_SERVICE.md)
- 현재 검증 보고서: [REPORT.md](REPORT.md)
- 시각화용 프롬프트: [ANTIGRAVITY_VIS_PROMPT.md](ANTIGRAVITY_VIS_PROMPT.md)
- 시현 보고서용 프롬프트: [ANTIGRAVITY_DEMO_REPORT_PROMPT.md](ANTIGRAVITY_DEMO_REPORT_PROMPT.md)

## 테스트

전체 테스트:

```bash
python -m unittest discover -s tests -v
```

현재 기준 결과: `55`개 테스트 통과

기능별 테스트 파일:

- 기본 프로토콜: `tests/test_protocol_basic.py`
- 만료/TTL: `tests/test_protocol_expiration.py`
- 카운터: `tests/test_protocol_counter.py`
- RESP: `tests/test_protocol_resp.py`
- SET NX: `tests/test_protocol_setnx.py`
- 무효화: `tests/test_protocol_invalidation.py`
- 락: `tests/test_protocol_locking.py`
- 레이트 리밋: `tests/test_protocol_rate_limit.py`
- 해시: `tests/test_protocol_hash.py`
- 셋: `tests/test_protocol_sets.py`
- 정렬셋: `tests/test_protocol_sorted_set.py`
- 동시성: `tests/test_concurrency.py`
- 영속성: `tests/test_persistence.py`
- 티켓팅 서비스: `tests/test_ticketing_service.py`
- 저장소 단위 테스트: `tests/test_hash_table.py`, `tests/test_store_expiration.py`
- CLI: `tests/test_cli.py`

## 티켓팅 데모

티켓팅 데모 서비스 실행:

```bash
python -m ticketing_service.server --host 127.0.0.1 --port 8080 --redis-host 127.0.0.1 --redis-port 6379
```

환경에 따라 로컬 런처를 써도 됩니다.

```bash
python run_ticketing_service_local.py --host 127.0.0.1 --port 8080 --redis-host 127.0.0.1 --redis-port 6379
```

접속 경로:

- `/` : 예매 시작 페이지
- `/ticketing?user_id=user-a` : Page A 예매실
- `/waiting-room?user_id=user-b` : Page B 대기실
- `/ops` : 현재 입장 완료자 / 대기열 / 좌석 상태 확인

## 트래픽 테스트

서버를 먼저 띄운 뒤 부하 테스트 스크립트를 실행합니다.

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode setget --profile stress
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode incr --profile stress
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode ratecheck --profile stress
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode queue --profile overload
```

출력 항목:

- `mode`
- `request_pairs`
- `total_commands`
- `successes`, `failures`
- `avg_pair_latency_ms`
- `p95_pair_latency_ms`
- `throughput_cmd_per_sec`

실험 도구 정리 위치:

- [experiments/traffic/README.md](C:\Users\cedis\Downloads\refis_project\experiments\traffic\README.md)
- [experiments/traffic/load_test.py](C:\Users\cedis\Downloads\refis_project\experiments\traffic\load_test.py)
