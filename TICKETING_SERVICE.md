# Ticketing Service Demo

## 개요

이 서비스는 `PyMiniRedis`를 실제로 사용하는 최소 티켓팅/대기열 데모입니다.

역할 분리:

- `PyMiniRedis`: 과제 본체인 raw TCP Mini Redis 서버
- `ticketing_service`: 그 위에서 동작하는 시연용 티켓팅 서비스

서비스 구현은 Python 표준 라이브러리 `http.server`만 사용합니다.
Flask/FastAPI는 사용하지 않습니다.

## 핵심 시나리오

- 사용자는 `/` 진입 페이지에서 예매를 시작한다
- 활성 입장 인원이 가득 차 있지 않으면 `Page A` 예매실로 바로 이동한다
- 가득 차 있으면 `Page B` 대기실로 이동한다
- `Page B`는 주기적으로 상태를 조회하고, 자리가 나면 자동으로 `Page A`로 리다이렉트된다
- 입장한 사용자는 좌석을 홀드할 수 있다
- 이미 홀드된 좌석은 다른 사용자가 잡지 못한다
- 결제 완료 또는 취소 시 다음 대기 사용자를 입장시킬 수 있다
- 운영자는 `/ops` 화면에서 현재 입장 완료자와 대기열을 바로 확인할 수 있다

## Redis 기능 매핑

- 대기열: `ZADD`, `ZRANK`, `ZPOPMIN`, `ZCARD`
- 중복 진입 방지: `SET ... NX`
- 참여자 추적: `SADD`, `SMEMBERS`
- 좌석 예약 정보: `HSET`, `HGETALL`
- 좌석 점유 보호: `LOCK`, `UNLOCK`
- 재고 관리: `DECR`, `INCR`
- 과도한 입장 시도 방어: `RATECHECK`

## 실행

터미널 A:

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379
```

터미널 B:

```bash
python -m ticketing_service.server --host 127.0.0.1 --port 8080 --redis-host 127.0.0.1 --redis-port 6379
```

브라우저에서 접속:

- [http://127.0.0.1:8080](http://127.0.0.1:8080) : 진입 페이지
- [http://127.0.0.1:8080/waiting-room?user_id=user-b](http://127.0.0.1:8080/waiting-room?user_id=user-b) : 대기실 예시
- [http://127.0.0.1:8080/ticketing?user_id=user-a](http://127.0.0.1:8080/ticketing?user_id=user-a) : 예매실 예시
- [http://127.0.0.1:8080/ops](http://127.0.0.1:8080/ops) : 운영 보기

## API

- `GET /`
  - 예매 시작 페이지
- `GET /waiting-room?user_id=<id>`
  - 대기열 전용 Page B
- `GET /ticketing?user_id=<id>`
  - 예매 진행용 Page A
- `GET /ops`
  - 현재 입장자/대기열/좌석 상태를 보는 운영용 화면
- `GET /api/state`
  - 현재 이벤트 상태 조회
- `GET /api/status?user_id=<id>`
  - 특정 사용자의 현재 상태 조회
- `POST /api/enter`
  - 입장 또는 대기열 진입
- `POST /api/advance`
  - 대기열에서 다음 사용자를 입장시킴
- `POST /api/reserve`
  - 좌석 홀드
- `POST /api/confirm`
  - 결제 확정
- `POST /api/cancel`
  - 예약 취소
- `POST /api/reset`
  - 데모 상태 초기화

## 빠른 시연 순서

1. `/ops`를 열어 현재 입장자/대기열이 비어 있는지 확인
2. `/`에서 `user-a`로 예매 시작 -> `Page A`로 이동
3. `/`에서 `user-b`로 예매 시작 -> `Page B`로 이동
4. `Page B` 또는 `/ops`에서 `user-a`가 현재 입장 완료자로 보이는지 확인
5. `user-a`가 `A1`을 홀드하고 결제 확정
6. `user-b`의 `Page B`가 자동으로 `Page A`로 이동하는지 확인

## 테스트

서비스 통합 테스트:

```bash
python -m unittest tests.test_ticketing_service -v
```

검증 항목:

- 인원 초과 시 대기열 이동
- Page A / Page B / 운영 보기 라우트 노출
- 상태 조회에서 현재 입장 완료자 목록 제공
- 결제 완료 후 다음 사용자 승격
- 같은 좌석 중복 홀드 방지
