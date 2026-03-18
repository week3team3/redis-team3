# 이 파일은 기존 실행 경로를 유지하기 위한 호환용 래퍼입니다.
# 실제 과부하 실험 로직은 experiments/traffic/load_test.py로 이동했습니다.

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.traffic.load_test import main


if __name__ == "__main__":
    raise SystemExit(main())
