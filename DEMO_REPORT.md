# PyMiniRedis 실전 시연 보고서 (Demo Report)

이 문서는 PyMiniRedis 팀 프로젝트의 핵심 기능을 팀원 및 발표자 누구나 따라하며 검증할 수 있도록 구성된 실습 가이드라인입니다.
복잡한 소켓 프로그래밍 지식 없이, 제공된 **내장 관리자 CLI**와 기본 제공 파이썬 스크립트를 통해 스펙을 검증할 수 있습니다.

---

## 🏁 1단계: 준비물 및 서버 실행

가장 먼저 PyMiniRedis 서버를 구동합니다. AOF(Append-Only File) 영속성을 켜두어, 추후 재시작 시 데이터 복원이 잘 되는지도 실험할 예정입니다.

**[터미널 A] - 서버 구동**
```bash
# 프로젝트 루트 디렉토리로 이동 후 실행
python -m mini_redis.server --host 127.0.0.1 --port 6379 --aof-path data/appendonly.aof
```
> 👉 *확인 포인트:* 서버가 `127.0.0.1:6379`에서 정상적으로 리스닝을 시작하는지 확인합니다.

---

## 💻 2단계: 내장 CLI 접속 및 기본 명령 확인

다른 터미널 창을 열고, 프로젝트에 내장된 대화형 CLI(Command Line Interface) 클라이언트로 접속합니다. 사람이 읽기 편한 평문 형태로 접속하여 즉시 다중 명령과 에러 처리를 검증할 수 있습니다.

**[터미널 B] - CLI 클라이언트 실행 및 테스트**
```bash
python -m mini_redis.cli --host 127.0.0.1 --port 6379
```

프롬프트(`127.0.0.1:6379> `)가 뜨면 아래 명령들을 직접 타이핑해 봅니다.
```text
127.0.0.1:6379> PING
+PONG

127.0.0.1:6379> INVALID_COMMAND
-ERR unknown command 'INVALID_COMMAND'
```
> 👉 *확인 포인트:* 연결 내에서 `PING` 정상 응답 및 정의되지 않은 `에러 입력`에 대한 예외 처리를 검증합니다.

---

## 🚦 3단계: (CLI 환경) 티켓팅 시나리오 - NX 중복 방지

특정 유저가 티켓팅 큐나 좌석을 한 번만 잡을 수 있도록, 키가 없을 때만 저장하는 `NX` 플래그를 확인합니다.

**[터미널 B (CLI 연속 진행)]**
```text
127.0.0.1:6379> SET seat:A user-1 NX
+OK
127.0.0.1:6379> SET seat:A user-2 NX
$-1
127.0.0.1:6379> GET seat:A
$user-1
```
> 👉 *확인 포인트:* 이미 다른 유저가 선점한(`user-1`) 좌석에 이중 쓰기를 시도(`user-2`)하면 `$-1` 로 거절당하는 중복 진입 방지 로직을 검증합니다.

---

## 🔢 4단계: (CLI 환경) 재고 변경 (INCR/DECR) 실험

티켓 재고량을 Atomic하게 감소/증가시킵니다.

**[터미널 B (CLI 연속 진행)]**
```text
127.0.0.1:6379> SET stock:event1 100
+OK
127.0.0.1:6379> DECRBY stock:event1 1
:99
127.0.0.1:6379> INCRBY stock:event1 2
:101
```
> 👉 *확인 포인트:* `INCR`/`DECR` 명령어가 숫자를 인식해 원자적(Atomic) 증감을 제대로 수행하는지 봅니다.

---

## 🏃 5단계: (CLI 환경) 대기열 순번 확인 (ZSET)

대기열 시스템에서 입장 순서를 타임스탬프(Score) 기반으로 정렬합니다.

**[터미널 B (CLI 연속 진행)]**
```text
127.0.0.1:6379> ZADD waiting-room 10.0 user-c
:1
127.0.0.1:6379> ZADD waiting-room 5.0 user-a
:1
127.0.0.1:6379> ZADD waiting-room 7.0 user-b
:1
127.0.0.1:6379> ZRANK waiting-room user-b
:1
127.0.0.1:6379> ZPOPMIN waiting-room
$["user-a",5.0]
```
> 👉 *확인 포인트:* 비동기적으로 몰리는 유저를 줄 세우고, 내 앞 대기 인원 파악(`ZRANK`), 차례가 된 유저 추출(`ZPOPMIN`) 흐름을 완벽히 소화합니다. 

---

## 🔒 6단계: (CLI 환경) 좌석 점유 경쟁 확인 (LOCK 다중 접속 테스트)

**[터미널 B (CLI 연속 진행)]**
```text
127.0.0.1:6379> LOCK seat_lock owner_A 10
:1
```

**[터미널 C] - 두 번째 CLI 창 생성 (새 터미널 열기)**
터미널을 하나 더 열어 CLI로 들어갑니다.
```bash
python -m mini_redis.cli --host 127.0.0.1 --port 6379
```
```text
127.0.0.1:6379> LOCK seat_lock owner_B 10
:0
```
> 👉 *확인 포인트:* owner_B가 같은 임계 구역 획득을 시도했지만 `:0`(거절)을 받아 다중 클라이언트 간 잠금 장치가 제대로 동작함을 입증합니다.

---

## 🛡️ 7단계: (CLI 환경) 매크로 트래픽 방어 (RATECHECK)

**[터미널 B (CLI 여전히 켜둔 곳)]**
빠른 속도로 같은 명령어를 세 번 쳐봅니다. (제한: 10초 내 2회)
```text
127.0.0.1:6379> RATECHECK api:user_A 2 10
+ALLOWED remaining=1 reset_in=10 count=1
127.0.0.1:6379> RATECHECK api:user_A 2 10
+ALLOWED remaining=0 reset_in=10 count=2
127.0.0.1:6379> RATECHECK api:user_A 2 10
+BLOCKED remaining=0 reset_in=10 count=2
```
> 👉 *확인 포인트:* 횟수 초과 시 즉시 `+BLOCKED`를 던져 봇/매크로 부하를 차단하는지 확인합니다. 확인 후 `QUIT`을 치고 터미널 창(B, C)에서 빠져나옵니다.

---

## 🔄 8단계: 서버 재시작 및 AOF 영속성 확인

지금까지 작업했던 데이터가 저장되었는지 복원을 실험합니다.

1. **[터미널 A]** 서버 터미널에서 `Ctrl+C`를 눌러 서버를 끕니다. 
2. **[터미널 A]** 동일 명령어(`python -m mini_redis.server --host 127.0.0.1 --port 6379 --aof-path data/appendonly.aof`)로 **다시 켭니다.**
3. **[터미널 B]** 다시 CLI로 들어갑니다.
   ```bash
   python -m mini_redis.cli
   ```
4. 잔여 재고 등 아까 저장했던 데이터를 불러옵니다.
   ```text
   127.0.0.1:6379> GET stock:event1
   $101
   ```
> 👉 *확인 포인트:* AOF 파싱을 통해 서버가 완전히 죽었다 살아나도 저장소(`101`)가 완벽히 복원됨을 봅니다. CLI를 끕니다(`QUIT`).

---
---

## 🛠️ 번외(고급): RESP (바이너리) 프로토콜 송수신 호환성 증명 전용 실험

우리의 서버는 위에서 쓴 텍스트 기반 접근뿐 아니라, 표준 클라이언트들의 호환 스펙인 `RESP (REdis Serialization Protocol)` 구조(`*3\r\n$3...`)도 이해하고 응답할 수 있습니다. CLI 창은 엔터 입력 시 `\n`를 강제로 더하므로 Raw 파싱을 증명하려면 순수 파이썬 스크립트가 필요합니다.

**[터미널 B] - 일반 쉘 (CLI 종료 상태)**
새로운 파이썬 파일 `test_resp.py` 를 만들고 아래 코드를 붙여넣습니다. (혹은 바로 실행)

```python
import socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 6379))

# 1. 터미널 명령이 아닌 '바이트 단위'로 날림
client.sendall(b"*3\r\n$3\r\nSET\r\n$8\r\nresp_key\r\n$10\r\nresp_value\r\n")
print(client.recv(4096).decode("utf-8").strip())  # 결과: +OK

# 2. 값 확인
client.sendall(b"GET resp_key\n")
print(client.recv(4096).decode("utf-8").strip())  # 결과: $10 \n resp_value
```

**실행 방법 (모든 OS 공통):**
```bash
python test_resp.py
```
출력에 `+OK`와 `resp_value`가 나오면 정규 RESP 파서(`parse_resp`)가 정확히 소켓 수준에서 이중으로 동작한다는 점을 증명하는 것입니다. 즉결 증명 끝!

---

## 🎤 번외: 4분 발표용 시연 축약 버전 흐름

발표 시간이 촉박할 땐 다음 흐름만 빠르게 타이핑하여 보여줍니다.

1. **[1분] AOF 포함 서버 켜기 & CLI 연결**: `python -m mini_redis.cli` 실행 후 터미널 창에서 `PING` 응답 시연
2. **[1분] 재고 증감과 트래픽 한도**: `SET stock 100`, `DECRBY stock 1`로 잔여 99 확인하고, `RATECHECK ip:123 1 5` 직후 바로 재요청하여 `+BLOCKED` 차단 화면 시연
3. **[1분] 서버 껐다 켜기**: 서버 `Ctrl+C` 종료 후 재시작. 방금 99로 차감된 `GET stock` 값 복원 결과 보여주며 영속성 시연 완료.
4. **[1분] RESP 파이썬 스크립트 시연**: 이미 복사해둔 `test_resp.py`를 파이썬으로 켡 한 번 돌려서 `+OK`가 뜨는 모습을 보여주며 통신 규격 호환성 증명!
