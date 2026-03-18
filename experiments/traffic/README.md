# Traffic Experiments

이 폴더는 `PyMiniRedis`의 과부하, 트래픽, 비교 실험 도구를 모아두는 전용 공간입니다.

의도:

- 기능이 되는지만 확인하는 테스트와 분리
- 많은 요청량을 주는 성능/과부하 실험 도구 집중 관리
- 이후 `Redis 사용 / 미사용` 비교 스크립트도 같은 위치에 추가

현재 포함된 도구:

- `load_test.py`
  - PyMiniRedis TCP 서버에 많은 요청을 병렬로 보내는 과부하 실험 도구
  - `setget`, `incr`, `ratecheck`, `queue` 모드 지원

권장 사용 방식:

- 빠른 점검: `--profile quick`
- 기본 스트레스 테스트: `--profile stress`
- 강한 과부하 테스트: `--profile overload`

예시:

```bash
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode setget --profile stress
python experiments/traffic/load_test.py --host 127.0.0.1 --port 6379 --mode queue --profile overload
```
