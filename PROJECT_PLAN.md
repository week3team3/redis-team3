# Ticketing Service Plan

## 목표

메인 프로젝트는 `티켓팅 사이트 + 대기열 시스템`을 구현하고, 그 뒤에서 `PyMiniRedis`로 트래픽 방어와 상태 관리를 수행하는 것입니다.

## 핵심 시나리오

- 사용자는 티켓팅 시작 전 대기열에 진입한다.
- 대기열은 진입 순서 또는 점수 기준으로 순번을 관리한다.
- 허용된 사용자만 티켓팅 페이지에 입장한다.
- 좌석 또는 재고는 중복 예약되지 않아야 한다.
- 과도한 요청은 rate limiting으로 차단한다.
- 예약 상태와 홀드 상태는 TTL로 자동 정리한다.

## PyMiniRedis 기능 매핑

### 대기열

- `ZADD waiting-room <score> <user>`
- `ZRANK waiting-room <user>`
- `ZRANGE waiting-room 0 9`
- `ZPOPMIN waiting-room`
- `ZCARD waiting-room`

사용 목적:

- 대기열 순번 계산
- 상위 입장 대상 사용자 선정
- 현재 대기열 길이 집계

### 사용자/예약 상태

- `HSET reservation:<id> user_id <value>`
- `HSET reservation:<id> seat_id <value>`
- `HGET reservation:<id> seat_id`
- `HGETALL reservation:<id>`
- `DEL reservation:<id>`

사용 목적:

- 예약 상세 상태 저장
- 결제 전 임시 홀드 정보 관리
- 사용자별 티켓팅 상태 저장

### 중복 방지

- `SADD joined-users <user>`
- `SISMEMBER joined-users <user>`
- `SREM joined-users <user>`
- `SET queue-token:<user> <token> NX`

사용 목적:

- 동일 사용자 중복 대기열 진입 방지
- 특정 이벤트에 대한 중복 처리 방지
- 1회성 토큰 발급 중복 방지

### 재고/카운터

- `INCR inventory:view-count`
- `INCRBY stock:event:1 100`
- `DECRBY stock:event:1 1`

사용 목적:

- 남은 재고 관리
- 트래픽 및 진입 수 카운트

### 트래픽 방어

- `RATECHECK api:user:<id> <limit> <window>`
- `RATECHECK api:ip:<ip> <limit> <window>`

사용 목적:

- 봇성 요청 차단
- 짧은 시간 내 과도한 API 호출 방지

### 임계구역 보호

- `LOCK seat:<seat_id> <owner> <ttl>`
- `UNLOCK seat:<seat_id> <owner>`

사용 목적:

- 같은 좌석 동시 예약 방지
- 결제 직전 상태 변경 경쟁 완화

### 만료/정리

- `EXPIRE reservation:<id> <seconds>`
- `TTL reservation:<id>`
- `EXPIREJITTER cache:<key> <seconds> <jitter>`
- `INVALIDATE page-cache:<key> <reason>`

사용 목적:

- 홀드 만료 자동 정리
- 캐시 만료 시점 분산
- 오래된 캐시 강제 무효화

## 권장 서비스 흐름

### 1. 대기열 진입

1. `SISMEMBER joined-users <user>`
2. 없으면 `SADD joined-users <user>`
3. `ZADD waiting-room <timestamp_or_score> <user>`
4. `ZRANK waiting-room <user>`로 현재 순번 반환

### 2. 입장 허용

1. 운영 배치 또는 관리 API가 `ZPOPMIN waiting-room` 반복
2. 선택된 사용자를 티켓팅 페이지로 이동
3. 필요한 경우 `HSET session:<user> stage ticketing`

### 3. 좌석 홀드

1. `LOCK seat:<seat_id> <user> 30`
2. 성공 시 `DECRBY stock:event:<id> 1`
3. `HSET reservation:<id> user_id <user>`
4. `HSET reservation:<id> seat_id <seat_id>`
5. `EXPIRE reservation:<id> 300`

### 4. 결제 완료 또는 취소

- 결제 완료:
  - `UNLOCK seat:<seat_id> <user>`
  - 필요 시 예약 상태 갱신
- 취소/타임아웃:
  - `INCRBY stock:event:<id> 1`
  - `DEL reservation:<id>`
  - `UNLOCK seat:<seat_id> <user>`

## 현재 PyMiniRedis에서 확보된 기반

- 문자열 key-value
- TTL / TTL jitter
- invalidation
- lock / unlock
- rate limiting
- hash
- set
- sorted set
- CLI
- feature-oriented tests

## 다음 서비스 단계

1. 간단한 티켓팅 웹 서비스 구현
2. 대기열 API를 `ZSET` 기반으로 연결
3. 예약 API를 `LOCK + HASH + DECRBY` 기반으로 연결
4. 부하 테스트 시 `PyMiniRedis` 지표와 티켓팅 성공/실패 수를 함께 수집
