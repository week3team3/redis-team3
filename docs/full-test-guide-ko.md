# 전체 테스트 가이드

이 문서는 Mini Redis 기반 좌석 홀드형 티켓팅 서비스를 처음부터 끝까지 테스트하는 방법을 다시 정리한 문서입니다.  
이번 버전은 `curl`보다 **브라우저 데모 페이지**를 중심으로 설명하고, 필요할 때만 CLI나 `curl`을 쓰는 흐름으로 구성했습니다.

## 1. 이 프로젝트에서 테스트하는 것

이 프로젝트는 아래 3가지를 보여주는 데모입니다.

1. 같은 좌석에 동시에 요청이 들어와도 **1명만 성공**하는지
2. 좌석을 잠깐 잡아둔 뒤 확정하지 않으면 **TTL 만료로 자동 해제**되는지
3. 최종 예매 완료된 좌석은 **`SOLD` 상태로 유지**되는지

## 2. 용어 먼저 이해하기

헷갈리기 쉬운 단어를 먼저 정리하면 아래와 같습니다.

- `hold`
  - 동작입니다.
  - 사용자가 좌석을 **임시 점유 요청**하는 행동입니다.
- `HELD`
  - 상태입니다.
  - 좌석이 현재 **임시 점유된 상태**라는 뜻입니다.
- `confirm`
  - 임시 점유된 좌석을 **최종 예매 완료**로 바꾸는 동작입니다.
- `SOLD`
  - 최종 예매 완료 상태입니다.
- `cancel`
  - 임시 점유를 취소하는 동작입니다.
- `AVAILABLE`
  - 비어 있는 좌석 상태입니다.

예를 들어:

- `POST /hold` 요청을 보내면
- 성공 시 좌석 상태가 `HELD`
- 그래서 `/status`에서는 `held` 개수가 올라갑니다

즉:

- `hold` = 잡는 행동
- `HELD` = 잡힌 상태

## 3. 가장 중요한 실행 원칙

이 저장소는 명령어를 전역으로 설치해서 쓰는 방식보다, **가상환경 실행 파일을 직접 경로로 실행하는 방식**이 가장 안전합니다.

따라서 아래처럼 실행하는 것을 기준으로 생각하면 됩니다.

```bash
./hoseok/bin/mini-redis-server
./hoseok/bin/ticketing-api
./hoseok/bin/ticketing-loadtest
./hoseok/bin/pytest
./hoseok/bin/python3
```

`command not found`가 나오면 거의 항상 이 방식으로 해결됩니다.

## 4. 사전 준비

### 4.1 프로젝트 폴더로 이동

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
```

### 4.2 의존성 설치

이미 `hoseok/` 가상환경이 있다면 아래 한 줄이면 됩니다.

```bash
./hoseok/bin/pip install -e '.[dev]'
```

### 4.3 기본 테스트 실행

서버를 띄우기 전에 먼저 단위/통합 테스트가 통과하는지 봅니다.

```bash
./hoseok/bin/pytest
```

### 4.4 기대 결과

- `tests/test_protocol.py` 통과
- `tests/test_store.py` 통과
- `tests/test_ticketing_api.py` 통과
- 전체 결과가 `passed`로 끝남

## 5. 실제 서버 2개 실행

이 프로젝트는 서버가 2개 필요합니다.

1. Mini Redis 서버
2. Ticketing API 서버

### 5.1 터미널 1에서 Mini Redis 실행

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
./hoseok/bin/mini-redis-server --host 127.0.0.1 --port 6380
```

정상 실행 시:

```text
Mini Redis listening on 127.0.0.1:6380
```

### 5.2 터미널 2에서 Ticketing API 실행

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
./hoseok/bin/ticketing-api \
  --host 127.0.0.1 \
  --port 8000 \
  --redis-host 127.0.0.1 \
  --redis-port 6380 \
  --hold-ttl 30
```

정상 실행 시:

```text
Uvicorn running on http://127.0.0.1:8000
```

## 6. 가장 쉬운 테스트 방법: 브라우저 데모 사용

이제 `curl` 없이 브라우저에서 대부분 테스트할 수 있습니다.

### 6.1 브라우저에서 데모 페이지 열기

주소창에 아래를 입력합니다.

```text
http://127.0.0.1:8000/demo
```

### 6.2 데모 페이지에서 할 수 있는 것

- 서버 상태 확인
- 이벤트 생성
- 좌석 `hold`
- 좌석 `confirm`
- 좌석 `cancel`
- 이벤트 상태 조회
- 좌석 목록 조회
- `same-seat` 시나리오 실행
- `random-seats` 시나리오 실행
- `expiry` 시나리오 실행

### 6.3 처음 들어가서 가장 먼저 할 일

1. `서버 상태 확인` 버튼 클릭
2. `API 정상`, `Mini Redis 정상` 표시 확인
3. 샘플 이벤트를 쓰고 싶으면 `샘플 값 넣기`
4. 직접 이벤트를 만들고 싶으면 `이벤트 생성`

## 7. 브라우저에서 수동 기능 테스트하는 방법

부하 테스트 전에 가장 먼저 해보면 좋은 기본 흐름입니다.

### 7.1 이벤트 생성

데모 페이지의 `이벤트 생성` 영역에서 아래처럼 입력합니다.

- 이벤트 ID: `concert-001`
- 제목: `Jungle Live`
- 좌석 목록: `A1, A2, A3, A4, A5`

그다음 `이벤트 생성` 버튼을 누릅니다.

### 7.2 기대 결과

- 현재 이벤트 ID가 `concert-001`로 설정됨
- 상태 패널에 이벤트가 표시됨
- 좌석 목록 테이블에 `A1`부터 `A5`까지 보임
- 모두 `AVAILABLE` 상태여야 함

### 7.3 좌석 hold 테스트

`좌석 액션` 영역에서 아래처럼 입력합니다.

- 현재 이벤트 ID: `concert-001`
- 좌석 ID: `A1`
- 사용자 ID: `user-01`

그다음 `hold` 버튼을 누릅니다.

### 7.4 기대 결과

- `A1` 상태가 `HELD`
- 사용자 ID가 `user-01`
- TTL 값이 보임
- 상태 요약에서 `HELD`가 1 증가

### 7.5 좌석 confirm 테스트

같은 값으로 `confirm` 버튼을 누릅니다.

### 7.6 기대 결과

- `A1` 상태가 `SOLD`
- TTL은 없어짐
- 상태 요약에서 `SOLD`가 1 증가

### 7.7 좌석 cancel 테스트

`cancel`은 `HELD` 상태인 좌석에 대해서만 의미가 있습니다.  
즉, `SOLD`된 좌석에는 `cancel`이 아니라 새 이벤트나 새 좌석으로 다시 시험해야 합니다.

테스트 방법:

1. `A2`를 `user-02`로 `hold`
2. `cancel` 버튼 클릭

기대 결과:

- `A2`가 다시 `AVAILABLE`
- `HELD` 수가 감소

## 8. 시나리오 1: 같은 좌석 동시 요청 테스트

이 시나리오는 가장 중요한 테스트입니다.

### 8.1 무엇을 검증하나

같은 좌석 `A1`에 동시에 `1000`개의 요청이 들어왔을 때:

- 1명만 성공해야 함
- 나머지는 실패해야 함
- 중복 예매가 없어야 함

### 8.2 브라우저에서 실행하는 방법

데모 페이지에서:

1. `같은 좌석 동시 요청` 카드 찾기
2. 동시 요청 수를 `1000`으로 둠
3. `same-seat 실행` 클릭

### 8.3 내부적으로 일어나는 일

1. 이벤트가 자동 생성됨
2. 좌석은 `A1` 한 개만 만들어짐
3. 서로 다른 사용자들이 동시에 `hold` 요청
4. Mini Redis는 `SET seatKey HELD:userId NX EX 30`로 처리
5. 첫 성공 이후의 요청은 모두 실패

### 8.4 기대 결과

- 성공 횟수: `1`
- 실패 횟수: `999`
- 상태 패널:
  - `AVAILABLE = 0`
  - `HELD = 1`
  - `SOLD = 0`

### 8.5 결과를 어떻게 읽나

예를 들어 결과가 이렇게 나오면:

- 성공 `1`
- 실패 `999`
- `held = 1`

이 뜻은:

- 한 명만 좌석을 잠깐 잡았고
- 나머지는 전부 거절되었으며
- 중복 hold는 발생하지 않았다는 뜻입니다

### 8.6 시간이 지나면 어떻게 되나

이 시나리오는 `confirm`을 하지 않기 때문에 약 `30초` 후 자동 만료됩니다.

즉:

- 실행 직후: `HELD = 1`
- 30초 후: 다시 `AVAILABLE = 1`

## 9. 시나리오 2: 여러 좌석 랜덤 요청 테스트

이 시나리오는 좌석 수보다 더 많이 팔리지 않는지 확인하는 테스트입니다.

### 9.1 무엇을 검증하나

- 좌석이 30개면 최종 판매도 최대 30개여야 함
- 같은 좌석이 중복 판매되면 안 됨

### 9.2 브라우저에서 실행하는 방법

데모 페이지에서:

1. `랜덤 좌석 요청` 카드 찾기
2. 요청 수 `500`
3. 좌석 수 `30`
4. `random-seats 실행` 클릭

### 9.3 내부적으로 일어나는 일

1. 좌석 30개짜리 이벤트 생성
2. 사용자 500명이 랜덤 좌석 hold 시도
3. hold 성공한 사용자만 confirm 수행
4. 최종 sold 수 계산

### 9.4 기대 결과

- hold 성공 수는 최대 `30`
- confirm 성공 수는 최대 `30`
- 최종 상태:
  - `AVAILABLE = 0`
  - `HELD = 0`
  - `SOLD = 30`

### 9.5 결과를 어떻게 읽나

예를 들어:

- `hold 성공 30`
- `confirm 성공 30`
- `sold 30`

이면 정상입니다.

이 뜻은:

- 좌석 수만큼만 예매 완료되었고
- 좌석 수를 초과해서 팔리지 않았다는 뜻입니다

## 10. 시나리오 3: TTL 만료 후 재점유 테스트

이 시나리오는 TTL이 실제로 동작하는지 확인합니다.

### 10.1 무엇을 검증하나

- 한 사용자가 hold한 좌석이
- 확정되지 않으면
- 일정 시간이 지난 뒤 자동으로 풀리고
- 다른 사용자가 다시 hold할 수 있는지 확인

### 10.2 브라우저에서 실행하는 방법

데모 페이지에서:

1. `TTL 만료 후 재점유` 카드 찾기
2. `expiry 실행` 클릭

### 10.3 내부적으로 일어나는 일

1. 이벤트 자동 생성
2. 첫 번째 사용자가 `A1` hold
3. 좌석 조회로 TTL 확인
4. `ttl + 1초` 대기
5. 두 번째 사용자가 다시 `A1` hold

### 10.4 기대 결과

- 첫 hold 성공
- 대기 후 두 번째 hold도 성공

이 뜻은:

- 첫 번째 hold가 TTL로 자동 해제되었고
- 좌석이 다시 빈 상태가 되었다는 뜻입니다

## 11. CLI로 시나리오 테스트하는 방법

브라우저 대신 터미널에서 수치 중심으로 테스트하고 싶다면 아래 명령을 씁니다.

### 11.1 same-seat

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
./hoseok/bin/ticketing-loadtest \
  --base-url http://127.0.0.1:8000 \
  --scenario same-seat \
  --concurrency 1000
```

### 11.2 random-seats

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
./hoseok/bin/ticketing-loadtest \
  --base-url http://127.0.0.1:8000 \
  --scenario random-seats \
  --requests 500 \
  --seat-count 30
```

### 11.3 expiry

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
./hoseok/bin/ticketing-loadtest \
  --base-url http://127.0.0.1:8000 \
  --scenario expiry
```

### 11.4 전체 한 번에 실행

```bash
cd /Users/juhoseok/Desktop/redis/redis-team3
./hoseok/bin/ticketing-loadtest \
  --base-url http://127.0.0.1:8000 \
  --scenario all
```

## 12. 필요할 때만 쓰는 추가 확인 방법

브라우저 데모가 있으므로 `curl`은 필수는 아닙니다.  
다만 결과를 직접 숫자로 보고 싶을 때만 쓰면 됩니다.

### 12.1 서버 상태 확인

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/health/full
```

### 12.2 특정 이벤트 상태 확인

CLI 시나리오를 돌리면 `eventId`가 출력됩니다.  
그 값을 넣어서 조회하면 됩니다.

예시:

```bash
curl -s http://127.0.0.1:8000/events/same-seat-af73cfa9/status
curl -s http://127.0.0.1:8000/events/same-seat-af73cfa9/seats
```

### 12.3 응답을 어떻게 읽나

예를 들어:

```json
{"eventId":"same-seat-af73cfa9","available":0,"held":1,"sold":0}
```

이 뜻은:

- 비어 있는 좌석 0개
- 임시 점유된 좌석 1개
- 판매 완료 좌석 0개

시간이 지난 뒤:

```json
{"eventId":"same-seat-af73cfa9","available":1,"held":0,"sold":0}
```

이렇게 바뀌면 TTL 만료로 좌석이 풀린 것입니다.

## 13. 발표용 추천 순서

데모나 발표에서는 아래 순서가 가장 자연스럽습니다.

1. `./hoseok/bin/pytest` 실행
2. Mini Redis 서버 실행
3. Ticketing API 서버 실행
4. 브라우저에서 `/demo` 열기
5. `서버 상태 확인` 버튼으로 연결 상태 보여주기
6. 샘플 이벤트 생성
7. `hold`, `confirm`, `cancel` 직접 시연
8. `same-seat` 실행으로 1명만 성공하는 것 보여주기
9. `random-seats` 실행으로 30석 이상 안 팔리는 것 보여주기
10. `expiry` 실행으로 TTL 만료 후 재점유 보여주기

## 14. 자주 겪는 문제

### 14.1 `command not found`

원인:

- 전역 명령으로 실행했기 때문

해결:

```bash
./hoseok/bin/mini-redis-server
./hoseok/bin/ticketing-api
./hoseok/bin/ticketing-loadtest
./hoseok/bin/python3
```

### 14.2 `ModuleNotFoundError: No module named 'mini_redis'`

원인:

- 잘못된 Python으로 실행했기 때문

해결:

```bash
./hoseok/bin/python3
```

### 14.3 브라우저에서 페이지는 뜨는데 동작이 안 됨

확인할 것:

1. Mini Redis 서버가 살아 있는지
2. Ticketing API 서버가 살아 있는지
3. `/demo` 페이지에서 `서버 상태 확인` 버튼을 눌렀을 때 `API 정상`, `Mini Redis 정상`이 보이는지

## 15. 테스트가 끝난 뒤 종료

서버를 띄운 터미널로 돌아가서 각각 `Ctrl + C`를 누르면 됩니다.

포트가 닫혔는지 보고 싶으면:

```bash
lsof -nP -iTCP:6380 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

아무 결과도 나오지 않으면 정상 종료입니다.

## 16. 참고 문서

- 실제 실행 결과 보고서: [live-load-test-report.md](/Users/juhoseok/Desktop/redis/redis-team3/docs/live-load-test-report.md)
- 프로젝트 개요: [README.md](/Users/juhoseok/Desktop/redis/redis-team3/README.md)
