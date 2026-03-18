# PyMiniRedis Usage Guide

## 1. 서버 실행

기본 실행:

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379
```

AOF 영속성 포함 실행:

```bash
python -m mini_redis.server --host 127.0.0.1 --port 6379 --aof-path data/appendonly.aof
```

옵션:

- `--host`: 바인딩 주소
- `--port`: TCP 포트
- `--aof-path`: append-only log 파일 경로
- `--sweep-interval`: 백그라운드 청소 주기
- `--invalidation-grace-seconds`: invalidated key 보관 시간

## 2. CLI 접속

가장 편한 방법은 내장 CLI를 쓰는 것입니다.

```bash
python -m mini_redis.cli --host 127.0.0.1 --port 6379
```

예시:

```text
127.0.0.1:6379> PING
+PONG
127.0.0.1:6379> SET hello world
+OK
127.0.0.1:6379> GET hello
$world
127.0.0.1:6379> quit
+BYE
```

한 번만 보내는 one-shot 명령도 가능합니다.

```bash
python -m mini_redis.cli --host 127.0.0.1 --port 6379 PING
python -m mini_redis.cli --host 127.0.0.1 --port 6379 SET hello world
python -m mini_redis.cli --host 127.0.0.1 --port 6379 GET hello
```

## 3. PowerShell에서 직접 접속

```powershell
$client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 6379)
$stream = $client.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$reader = New-Object System.IO.StreamReader($stream)
$writer.AutoFlush = $true
```

명령 전송:

```powershell
$writer.WriteLine("PING")
$reader.ReadLine()
```

연결 종료:

```powershell
$writer.WriteLine("QUIT")
$reader.ReadLine()
$client.Close()
```

## 4. 명령 예시

### 4.1 기본 저장

```text
SET hello world
+OK
GET hello
$world
EXISTS hello
:1
DEL hello
:1
GET hello
$nil
```

### 4.1.1 조건부 저장 (`SET NX`)

```text
SET queue-token user-a NX
+OK
GET queue-token
$user-a
SET queue-token user-b NX
$nil
GET queue-token
$user-a
```

이미 존재하는 key에는 쓰지 않고, 없을 때만 저장합니다.

### 4.2 TTL

```text
SET session active
+OK
TTL session
:-1
EXPIRE session 5
:1
TTL session
:5
```

### 4.3 TTL 지터

```text
SET cache warm
+OK
EXPIREJITTER cache 10 3
:12
TTL cache
:12
```

실제 TTL은 `10`초부터 `13`초 사이에서 랜덤하게 정해집니다.

### 4.4 카운터

```text
INCR visits
:1
DECR visits
:0
INCRBY stock:event:1 100
:100
DECRBY stock:event:1 1
:99
GET stock:event:1
$99
```

### 4.4.1 RESP 직접 확인

PowerShell에서 최소 RESP 요청 하나를 직접 보내 볼 수 있습니다.

```powershell
$client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 6379)
$stream = $client.GetStream()
$writer = New-Object System.IO.BinaryWriter($stream)
$reader = New-Object System.IO.StreamReader($stream)
$payload = [System.Text.Encoding]::ASCII.GetBytes("*1`r`n`$4`r`nPING`r`n")
$writer.Write($payload)
$writer.Flush()
$reader.ReadLine()
```

예상 응답:

```text
+PONG
```

`SET`, `GET`, `DEL`도 같은 방식으로 RESP 배열 요청을 보내 검증할 수 있습니다.

### 4.5 무효화

```text
SET profile cached
+OK
INVALIDATE profile stale-data
:1
GET profile
$nil
EXISTS profile
:0
```

invalidated key는 즉시 조회 대상에서 제외되지만, 내부적으로는 잠시 보관되다가 background sweeper가 정리합니다.

### 4.6 락

```text
LOCK seat:A-10 user-a 5
:1
LOCK seat:A-10 user-b 5
:0
UNLOCK seat:A-10 user-b
:0
UNLOCK seat:A-10 user-a
:1
```

`LOCK`은 같은 리소스 키에 대해 owner 기반으로 상호 배제를 제공합니다.

### 4.7 레이트 리밋

```text
RATECHECK api:user:1 2 3
+ALLOWED remaining=1 reset_in=3 count=1
RATECHECK api:user:1 2 3
+ALLOWED remaining=0 reset_in=3 count=2
RATECHECK api:user:1 2 3
+BLOCKED remaining=0 reset_in=3 count=2
```

### 4.8 해시

```text
HSET reservation:1 user_id user-a
:1
HSET reservation:1 seat_id A-10
:1
HGET reservation:1 seat_id
$A-10
HGETALL reservation:1
${"seat_id":"A-10","user_id":"user-a"}
```

### 4.9 셋

```text
SADD joined-users user-a
:1
SADD joined-users user-a
:0
SISMEMBER joined-users user-a
:1
SMEMBERS joined-users
$["user-a"]
```

### 4.10 정렬 셋

```text
ZADD waiting-room 1000 user-a
:1
ZADD waiting-room 1001 user-b
:1
ZRANK waiting-room user-b
:1
ZRANGE waiting-room 0 -1
$["user-a","user-b"]
ZPOPMIN waiting-room
$["user-a",1000.0]
```

## 5. 응답 형식

- `+...`: 성공 응답
- `+ALLOWED ...`: rate limit 허용
- `+BLOCKED ...`: rate limit 차단
- `$...`: 문자열 값 또는 compact JSON 문자열
- `$nil`: 값 없음
- `:...`: 정수 응답
- `-ERR ...`: 오류

## 6. 기능별 검증

전체 테스트:

```bash
python -m unittest discover -s tests -v
```

기능별 실행 예시:

```bash
python -m unittest tests.test_protocol_basic -v
python -m unittest tests.test_protocol_expiration -v
python -m unittest tests.test_protocol_counter -v
python -m unittest tests.test_protocol_resp -v
python -m unittest tests.test_protocol_setnx -v
python -m unittest tests.test_protocol_invalidation -v
python -m unittest tests.test_protocol_locking -v
python -m unittest tests.test_protocol_rate_limit -v
python -m unittest tests.test_protocol_hash -v
python -m unittest tests.test_protocol_sets -v
python -m unittest tests.test_protocol_sorted_set -v
python -m unittest tests.test_concurrency -v
python -m unittest tests.test_persistence -v
python -m unittest tests.test_cli -v
```

## 7. 트래픽 검증

기본 set/get 부하:

```bash
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode setget --profile stress
```

같은 키 카운터 증가 부하:

```bash
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode incr --profile stress
```

레이트 리밋 부하:

```bash
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode ratecheck --profile stress
```

대기열 부하:

```bash
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode queue --profile overload
```

프로필 기준 기본 부하량:

- `quick`: 빠른 점검용
- `stress`: 기본 스트레스 테스트용
- `overload`: 강한 과부하 테스트용
