# Redis RESP Learning Project

Python socket으로 만든 학습용 미니 Redis 서버입니다.  
목표는 완전한 Redis 구현이 아니라, `RESP 파싱 -> 명령 처리 -> 응답 생성 -> 상태 저장소 반영` 흐름을 직접 실험해보는 것입니다.

이 프로젝트로 볼 수 있는 핵심은 아래입니다.

- 문자열 split 서버가 아니라 RESP 프로토콜 서버로 요청을 처리하는 흐름
- 여러 클라이언트가 같은 key를 공유할 때 상태가 어떻게 반영되는지
- `safe`한 상태 변경과 `unsafe`한 상태 변경이 왜 다른지
- TTL 만료, 삭제, 조회 같은 무효화 흐름
- GUI에서 사용자 화면 반영과 실제 서버 상태가 어떻게 어긋날 수 있는지

## Files

- `server.py`
  - TCP 서버
  - RESP 요청 파싱
  - 명령 처리
  - RESP 응답 생성
  - 인메모리 상태 저장소(dict) 관리
- `client.py`
  - CLI 테스트 클라이언트
  - GUI 실험 클라이언트
  - safe/unsafe 동시성 비교 실험

## Server Structure

- `parse_resp()`
  - 입력 파싱부
  - TCP로 들어온 바이트를 RESP 규칙대로 읽어서 `['SET', 'a', '10']` 같은 토큰으로 바꿉니다.
- `handle_command()`
  - 명령 처리부
  - 저장소(dict)를 읽고/쓰고/삭제하고/감소시키는 실제 로직이 들어 있습니다.
- `build_resp_response()`
  - 출력 응답부
  - 처리 결과를 `+OK`, bulk string, integer, error 같은 RESP 응답으로 만듭니다.
- `store`
  - 인메모리 상태 저장소
  - 서버가 켜져 있는 동안만 값이 유지되고, 서버를 재시작하면 사라집니다.

## Supported Commands

기본 명령:

- `SET key value`
- `GET key`
- `DEL key`

추가 명령:

- `EXISTS key`
- `INCR key`
- `DECR key`
- `SET key value NX`
- `CLAIM key`
  - 재고가 남아 있을 때만 1 감소시키는 쿠폰/재고용 명령
- `EXPIRE key seconds`
  - TTL 설정
- `TTL key`
  - 남은 TTL 확인

## RESP Examples

예를 들어 `SET a 10`은 실제로 이런 RESP 요청으로 바뀝니다.

```text
*3\r\n$3\r\nSET\r\n$1\r\na\r\n$2\r\n10\r\n
```

`GET a`는 이렇게 갑니다.

```text
*2\r\n$3\r\nGET\r\n$1\r\na\r\n
```

응답 예시는 아래처럼 나옵니다.

```text
+OK\r\n
$2\r\n10\r\n
$-1\r\n
:1\r\n
-ERR wrong number of arguments\r\n
```

## Run

프로젝트 폴더로 이동:

```bash
cd /Users/hmm/Desktop/jungle/project/redis/redis-team3
```

### 1. Server Run

```bash
python3 server.py
```

정상 실행 예시:

```text
Mini RESP Redis server listening on 127.0.0.1:6380
State store is a plain Python dict. Restart the server to reset all data.
```

### 2. CLI Client Run

```bash
python3 client.py
```

예시 입력:

```text
SET stock 100
GET stock
CLAIM stock
TTL stock
DEL stock
```

### 3. GUI Client Run

```bash
python3 client.py --gui
```

## GUI Features

GUI에서는 아래 기능을 바로 실험할 수 있습니다.

- `Set Stock`
  - key에 초기 재고 저장
- `Refresh State`
  - 현재 재고와 TTL 상태를 다시 읽어옴
- `Claim Coupon`
  - `CLAIM key`
  - 재고가 있을 때만 1 감소
- `Apply TTL`
  - `EXPIRE key seconds`
- `Delete Coupon Key`
  - `DEL key`
- `Auto Refresh (1s)`
  - 1초마다 현재 상태를 다시 읽어옴
- `Send`
  - 직접 명령어 전송
- `Concurrency Lab`
  - safe/unsafe 동시성 비교 실험

## Why Safe And Unsafe Are Different

### Safe

`CLAIM stock`

- 서버 안에서 `읽기 -> 검사 -> 감소 -> 응답`을 한 번에 처리합니다.
- 성공 수가 재고 수를 넘지 않도록 만드는 데 유리합니다.

### Unsafe

`GET stock -> 계산 -> SET stock new_value`

- 읽기와 쓰기가 분리돼 있습니다.
- 여러 사용자가 같은 이전 값을 읽고 각각 쓰면 oversell처럼 보이는 문제가 생길 수 있습니다.

## Concurrency Lab

GUI에서 `Run 100 Safe Claim`, `Run 100 Unsafe Buy`를 눌러 비교할 수 있습니다.

실험 전에 보통 이렇게 시작하면 됩니다.

1. `Initial Stock = 100`
2. `Set Stock`
3. `Run 100 Safe Claim`
4. 결과 확인
5. 다시 `Set Stock`
6. `Run 100 Unsafe Buy`
7. 결과 비교

결과에는 아래가 표시됩니다.

- `success`
- `fail`
- `initial`
- `final`
- `oversell`

보통 기대하는 해석은 아래와 같습니다.

- safe
  - `success`가 재고 수량 안에서 끝남
  - `oversell=False`
- unsafe
  - `success`가 초기 재고보다 커질 수 있음
  - `oversell=True` 가능

## TTL / Invalidation Test

TTL과 삭제를 같이 보면 상태 무효화 흐름을 보기 좋습니다.

추천 순서:

1. `Set Stock`
2. `TTL Seconds = 10`
3. `Apply TTL`
4. `Refresh State` 또는 `Auto Refresh`
5. 시간이 지나면 key가 사라지는지 확인
6. `Delete Coupon Key`로 즉시 삭제도 확인

이 실험으로 볼 수 있는 것은:

- 서버 상태 저장소에 값이 반영되는 방식
- TTL 만료 시 key가 사라지는 방식
- 사용자 화면은 주기적으로 다시 읽어와야 최신 상태를 반영한다는 점

## What To Focus On

이 프로젝트에서 핵심은 단순히 네트워크 지연만 보는 것이 아닙니다.  
더 중요한 것은 아래입니다.

- 상태 저장소(dict)에 값이 언제 반영되는가
- 여러 요청이 같은 key를 어떤 순서로 변경하는가
- 서버가 어떤 값을 기준으로 응답을 반환하는가
- 화면은 그 값을 언제 다시 읽어오는가

즉, `선착순`, `쿠폰 발급`, `좌석 점유` 같은 문제를  
`공유 상태 저장소 반영 시점`과 `응답 반환 시점` 관점에서 실험해보기 위한 프로젝트입니다.

## Branch Usage

이 작업 내용은 현재 `redis-test` 브랜치에 올라가 있습니다.  
`main`이 아니라 이 브랜치로 내려받아 실험하면 됩니다.

### 이미 저장소가 있는 경우

```bash
git fetch origin
git switch redis-test
```

로컬에 아직 브랜치가 없으면:

```bash
git fetch origin
git switch -c redis-test --track origin/redis-test
```

### 처음 clone 하는 경우

```bash
git clone https://github.com/week3team3/redis-team3.git
cd redis-team3
git switch -c redis-test --track origin/redis-test
```

### 현재 브랜치 확인

```bash
git branch --show-current
```

정상이라면 아래처럼 나와야 합니다.

```text
redis-test
```
