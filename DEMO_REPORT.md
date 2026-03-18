# PyMiniRedis 실전 시연 보고서 (Demo Report)

이 문서는 PyMiniRedis 팀 프로젝트의 핵심 기능을 팀원 및 발표자 누구나 따라하며 검증할 수 있도록 구성된 실습 가이드라인입니다.

---

## 🏁 1단계: 준비물 및 서버 실행

가장 먼저 PyMiniRedis 서버를 구동합니다. AOF(Append-Only File) 영속성을 켜두어, 추후 재시작 시 데이터 복원이 잘 되는지도 실험할 예정입니다.

**[터미널 A] - 서버 구동**
```powershell
# 프로젝트 루트 디렉토리로 이동 후 실행
python -m mini_redis.server --host 127.0.0.1 --port 6379 --aof-path data/appendonly.aof
```
> 👉 *확인 포인트:* 서버가 `127.0.0.1:6379`에서 정상적으로 리스닝을 시작하는지 확인합니다.

---

## 💻 2단계: CLI 접속 및 기본 명령 확인

다른 터미널 창을 열고, 내장된 CLI 클라이언트나 일반 TCP Client를 이용해 접속합니다.
여기서는 가장 쉬운 PowerShell Raw 소켓 연결 방식으로 진행하겠습니다. (본 접속 방식이 한 연결 내 다중 요청을 증명합니다)

**[터미널 B] - 클라이언트 연결 및 기본 검증**
```powershell
$client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 6379)
$stream = $client.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$reader = New-Object System.IO.StreamReader($stream)
$writer.AutoFlush = $true

# 1. 단일 연결 다중 요청 및 에러 입력 테스트
$writer.WriteLine("PING")
$reader.ReadLine()  # 예상 출력: +PONG

$writer.WriteLine("INVALID_COMMAND")
$reader.ReadLine()  # 예상 출력: -ERR unknown command 'INVALID_COMMAND'
```
> 👉 *확인 포인트:* 연결 내에서 `PING` 정상 응답 및 정의되지 않은 `에러 입력`에 대한 예외 처리를 검증합니다.

---

## 🛠️ 3단계: RESP Raw 요청 직접 보내기

단순 텍스트 프로토콜뿐 아니라, Redis 정식 규격인 RESP(REdis Serialization Protocol) 배열을 파싱하는지 확인합니다.

**[터미널 B] - 연속해서 진행**
```powershell
# RESP 포맷으로 'SET resp_key resp_value' 전송 (*3으로 3개의 인자 선언)
$writer.Write("*3`r`n`$3`r`nSET`r`n`$8`r`nresp_key`r`n`$10`r`nresp_value`r`n")
$reader.ReadLine()  # 예상 출력: +OK

# RESP 포맷으로 'GET resp_key' 전송
$writer.Write("*2`r`n`$3`r`nGET`r`n`$8`r`nresp_key`r`n")
$reader.ReadLine()  # 예상 출력: $10
$reader.ReadLine()  # 예상 출력: resp_value

# 일반 구문으로 삭제하여 혼용 가능성 확인
$writer.WriteLine("DEL resp_key")
$reader.ReadLine()  # 예상 출력: :1
```
> 👉 *확인 포인트:* `parse_resp()` 로직이 동작하여 `*3\r\n$3` 형태의 바이너리 호환 구문을 파싱하고, 정상적인 `SET`/`GET`/`DEL` RESP 응답 처리를 수행하는지 검증합니다. 

---

## 🚦 4단계: 티켓팅 시나리오 - SET NX 중복 방지

특정 유저가 티켓팅 큐나 좌석을 한 번만 잡을 수 있도록, 키가 없을 때만 저장하는 `NX` 플래그를 확인합니다.

**[터미널 B] - 연속해서 진행**
```powershell
$writer.WriteLine("SET seat:A user-1 NX")
$reader.ReadLine()  # 예상 출력: +OK

# 다른 유저가 동일 좌석 선점 시도
$writer.WriteLine("SET seat:A user-2 NX")
$reader.ReadLine()  # 예상 출력: $-1 (수행 실패)

$writer.WriteLine("GET seat:A")
$reader.ReadLine()  # 예상 출력: $user-1
```
> 👉 *확인 포인트:* 티켓팅의 중복 진입과 이중 결제를 방지하는 핵심 플래그 `SET NX`의 동작을 검증합니다.

---

## 🔢 5단계: 재고 변경 (INCR/DECR) 실험

티켓 재고량을 Atomic하게 감소/증가시킵니다.

**[터미널 B] - 연속해서 진행**
```powershell
# 초기 재고 등록
$writer.WriteLine("SET stock:event1 100")
$reader.ReadLine()  # 예상 출력: +OK

# 재고 1개 차감 (티켓 구매)
$writer.WriteLine("DECRBY stock:event1 1")
$reader.ReadLine()  # 예상 출력: :99

# 티켓 취소로 2개 원복 
$writer.WriteLine("INCRBY stock:event1 2")
$reader.ReadLine()  # 예상 출력: :101
```
> 👉 *확인 포인트:* `INCR`/`DECR` 명령어가 숫자를 인식해 원자적(Atomic) 증감을 제대로 수행하는지 봅니다.

---

## 🏃 6단계: 대기열 순번 확인 (ZSET)

대기열 시스템에서 입장 순서를 타임스탬프(Score) 기반으로 줄을 세우는 기능입니다.

**[터미널 B] - 연속해서 진행**
```powershell
# 대기열에 3명 진입 (Score: 타임스탬프 등 우선순위치)
$writer.WriteLine("ZADD waiting-room 10.0 user-c")
$reader.ReadLine()  # 예상 출력: :1
$writer.WriteLine("ZADD waiting-room 5.0 user-a")
$reader.ReadLine()  # 예상 출력: :1
$writer.WriteLine("ZADD waiting-room 7.0 user-b")
$reader.ReadLine()  # 예상 출력: :1

# 내 순번(Rank) 확인 (0부터 시작하므로 user-a는 0, user-b는 1)
$writer.WriteLine("ZRANK waiting-room user-b")
$reader.ReadLine()  # 예상 출력: :1

# 먼저 온 순서대로 빼내기 (티켓팅 입장 체계)
$writer.WriteLine("ZPOPMIN waiting-room")
$reader.ReadLine()  # 예상 출력: $["user-a",5.0]
```
> 👉 *확인 포인트:* 비동기적으로 몰리는 유저를 줄 세우고(`ZADD`), 내 앞 대기 인원(`ZRANK`), 차례가 된 유저 추출(`ZPOPMIN`) 흐름을 완벽히 소화합니다. 

---

## 🔒 7단계: 좌석 점유 경쟁 확인 (LOCK / 다중 클라이언트 테스트)

두 개의 클라이언트가 같은 데이터를 접근할 때 상호 배제가 되는지 알아봅니다.

**[터미널 B] - 클라이언트 1**
```powershell
$writer.WriteLine("LOCK seat_lock owner_A 10")
$reader.ReadLine()  # 예상 출력: :1 (락 획득 성공)
```

**[터미널 C] - 두 번째 클라이언트 생성 (새 창)**
```powershell
$client2 = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 6379)
$stream2 = $client2.GetStream()
$writer2 = New-Object System.IO.StreamWriter($stream2)
$reader2 = New-Object System.IO.StreamReader($stream2)
$writer2.AutoFlush = $true

# [터미널 C] owner_B가 같은 자리에 권한을 요청해도 거절당함
$writer2.WriteLine("LOCK seat_lock owner_B 10")
$reader2.ReadLine()  # 예상 출력: :0 (락 획득 실패)
```
> 👉 *확인 포인트:* 다중 클라이언트 접속 환경에서 임계 구역(Critical Section) 보호가 제대로 동작함을 입증합니다.

---

## 🛡️ 8단계: 매크로 트래픽 방어 확인 (RATECHECK)

매크로 봇이 API를 도배하지 못하도록 레이트 리밋을 체크합니다. (초당 2건 제한)

**[터미널 B] - 연속해서 진행**
```powershell
$writer.WriteLine("RATECHECK api:user_A 2 10")
$reader.ReadLine()  # 예상 출력: +ALLOWED remaining=1 ...
$writer.WriteLine("RATECHECK api:user_A 2 10")
$reader.ReadLine()  # 예상 출력: +ALLOWED remaining=0 ...
$writer.WriteLine("RATECHECK api:user_A 2 10")
$reader.ReadLine()  # 예상 출력: +BLOCKED remaining=0 ...
```
> 👉 *확인 포인트:* 동일 유저/IP가 설정된 윈도우 범위를 초과할 때 즉시 `+BLOCKED`를 던져 부하를 차단하는지 확인합니다.

---

## 🔄 9단계: 서버 재시작 및 AOF 영속성 확인

지금까지 작업했던 데이터가 휘발되지 않고 저장되었는지 AOF 파일 복원을 실험합니다.

1. **[터미널 A]** 서버 구동 터미널에서 `Ctrl+C`를 눌러 서버를 끕니다. 
2. **[터미널 B]** 소켓이 닫혔으므로 기존 연결 객체를 닫아줍니다. 
   ```powershell
   $client.Close()
   ```
3. **[터미널 A]** 아까와 동일한 명령어로 **서버를 다시 켭니다.**
   ```powershell
   python -m mini_redis.server --host 127.0.0.1 --port 6379 --aof-path data/appendonly.aof
   ```
4. **[터미널 B]** 다시 접속하여 앞서 남겨둔 `stock:event1` 데이터가 남아있는지 봅니다.
   ```powershell
   $client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 6379)
   $stream = $client.GetStream()
   $writer = New-Object System.IO.StreamWriter($stream)
   $reader = New-Object System.IO.StreamReader($stream)
   $writer.AutoFlush = $true

   $writer.WriteLine("GET stock:event1")
   $reader.ReadLine()  # 예상 출력: $101 (서버를 끄기 전 최신 데이터로 복원됨)
   ```
> 👉 *확인 포인트:* AOF 파싱을 통해 서버가 재시작되어도 영속성 처리가 무결함을 입증합니다. 성공입니다!

---
---

## 🎤 번외: 4분 발표용 시연 축약 버전 흐름

발표 시간이 촉박할 땐 다음 흐름만 4분 안에 빠르게 타이핑하여 보여줍니다.

1. **[1분] AOF 포함 서버 켜기 & 연결**: PowerShell 연결 후 `PING` 응답 시연
2. **[1분] RESP & 티켓점유 시연**: `*3\r\n...` Raw 페이로드 발동 시연 후, `SET seat user-A NX` & 다른 유저의 중복 `NX` 실패 보여주기
3. **[1분] 재고 증감과 트래픽 한도**: `SET stock 100`, `DECRBY stock 1`로 잔여 99 확인하고, `RATECHECK ip:123 1 5` 직후 바로 재요청하여 `+BLOCKED` 뜨는 화면 시연
4. **[1분] 서버 껐다 켜기**: 서버 `Ctrl+C` 종료 후 재시작. 방금 99로 차감된 `GET stock` 값 복원 결과 보여주며 영속성 시연 끝.

> **💡 실패 시 점검 포인트**
> - *응답이 오지 않고 멈춰있나요?* : 명령어 끝에 개행(Enter / `\n`)이 누락되지 않았는지 점검하세요. 
> - *AOF 복원이 안 되나요?* : 서버를 띄울 때 `--aof-path` 옵션 지정이 누락되었거나, 파일 권한 문제일 수 있습니다. (data 폴더 접근 불가 등)
> - *RESP 오류?* `$N\r\n` 에서 길이(N) 글자 수 계산이 어긋나면 파싱 에러가 발생합니다. Payload 길이를 재확인하세요.
