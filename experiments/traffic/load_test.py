from __future__ import annotations

# 이 파일은 PyMiniRedis TCP 서버에 많은 요청을 병렬로 보내서
# 처리량, 평균 지연, p95 지연, 실패 수를 확인하는 과부하 실험 도구입니다.
# 앞으로 추가될 트래픽/비교 실험 도구도 이 폴더에 함께 모읍니다.

import argparse
import socket
import statistics
import threading
import time
from queue import Queue


PROFILE_DEFAULTS: dict[str, tuple[int, int]] = {
    "quick": (20, 50),
    "stress": (100, 200),
    "overload": (200, 500),
}


def send_line(host: str, port: int, command: str, timeout: float) -> str:
    with socket.create_connection((host, port), timeout=timeout) as client:
        client.sendall(f"{command}\n".encode("utf-8"))
        data = client.recv(4096)
    return data.decode("utf-8").strip()


class PersistentLineClient:
    # 이 클래스는 워커 하나가 하나의 TCP 연결을 계속 재사용하도록 도와줍니다.
    # 과부하 테스트에서 명령마다 새 연결을 열면 클라이언트 측 포트가 먼저 고갈될 수 있어서,
    # 실제 명령 처리 성능을 보려면 연결 재사용 방식이 더 적합합니다.

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self._socket = socket.create_connection((host, port), timeout=timeout)
        self._reader = self._socket.makefile("r", encoding="utf-8", newline="\n")
        self._writer = self._socket.makefile("w", encoding="utf-8", newline="\n")

    def send(self, command: str) -> str:
        self._writer.write(f"{command}\n")
        self._writer.flush()
        return self._reader.readline().strip()

    def close(self) -> None:
        try:
            self._writer.close()
        finally:
            try:
                self._reader.close()
            finally:
                self._socket.close()


def set_get_workload(worker_id: int, iteration: int) -> tuple[str, str]:
    key = f"worker:{worker_id}:key:{iteration}"
    value = f"value-{worker_id}-{iteration}"
    return f"SET {key} {value}", f"GET {key}"


def incr_workload(_: int, __: int) -> tuple[str, str]:
    return "INCR shared-load-counter", "GET shared-load-counter"


def ratecheck_workload(worker_id: int, _: int) -> tuple[str, str]:
    key = f"ratelimit:user:{worker_id % 8}"
    return f"RATECHECK {key} 10 2", f"RATECHECK {key} 10 2"


def queue_workload(worker_id: int, iteration: int) -> tuple[str, str]:
    member = f"user-{worker_id}-{iteration}"
    score = float(worker_id * 100000 + iteration)
    return f"ZADD waiting-room {score} {member}", f"ZRANK waiting-room {member}"


def worker(
    worker_id: int,
    host: str,
    port: int,
    iterations: int,
    timeout: float,
    mode: str,
    results: Queue,
    start_barrier: threading.Barrier,
) -> None:
    if mode == "setget":
        workload = set_get_workload
    elif mode == "incr":
        workload = incr_workload
    elif mode == "queue":
        workload = queue_workload
    else:
        workload = ratecheck_workload

    client: PersistentLineClient | None = None
    try:
        client = PersistentLineClient(host, port, timeout)
        start_barrier.wait()
        for iteration in range(iterations):
            first_command, second_command = workload(worker_id, iteration)
            started = time.perf_counter()
            try:
                first_reply = client.send(first_command)
                second_reply = client.send(second_command)
                elapsed_ms = (time.perf_counter() - started) * 1000
                success = _is_success(mode, worker_id, iteration, first_reply, second_reply)
                results.put((success, elapsed_ms, first_reply, second_reply))
            except Exception as exc:  # noqa: BLE001
                elapsed_ms = (time.perf_counter() - started) * 1000
                results.put((False, elapsed_ms, "EXCEPTION", str(exc)))
                return
    finally:
        if client is not None:
            client.close()


def _is_success(
    mode: str,
    worker_id: int,
    iteration: int,
    first_reply: str,
    second_reply: str,
) -> bool:
    if mode == "setget":
        expected_value = f"$value-{worker_id}-{iteration}"
        return first_reply == "+OK" and second_reply == expected_value
    if mode == "queue":
        return first_reply in {":0", ":1"} and second_reply.startswith(":")
    if mode == "ratecheck":
        return first_reply.startswith("+") and second_reply.startswith("+")
    return first_reply.startswith(":") and second_reply.startswith("$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Concurrent load test for PyMiniRedis.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--clients", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--profile", choices=("quick", "stress", "overload"), default="stress")
    parser.add_argument("--mode", choices=("setget", "incr", "ratecheck", "queue"), default="setget")
    return parser


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * pct)))
    return ordered[index]


def resolve_load_shape(profile: str, clients: int | None, iterations: int | None) -> tuple[int, int]:
    default_clients, default_iterations = PROFILE_DEFAULTS[profile]
    return clients or default_clients, iterations or default_iterations


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    clients, iterations = resolve_load_shape(args.profile, args.clients, args.iterations)

    results: Queue = Queue()
    barrier = threading.Barrier(clients)
    threads = [
        threading.Thread(
            target=worker,
            args=(
                index,
                args.host,
                args.port,
                iterations,
                args.timeout,
                args.mode,
                results,
                barrier,
            ),
            daemon=True,
        )
        for index in range(clients)
    ]

    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    total_duration = time.perf_counter() - started

    total_request_pairs = clients * iterations
    successes = 0
    failures = 0
    latencies: list[float] = []
    sample_failures: list[tuple[str, str]] = []

    while not results.empty():
        success, latency_ms, first_reply, second_reply = results.get()
        latencies.append(latency_ms)
        if success:
            successes += 1
        else:
            failures += 1
            if len(sample_failures) < 5:
                sample_failures.append((first_reply, second_reply))

    total_commands = total_request_pairs * 2
    avg_ms = statistics.mean(latencies) if latencies else 0.0
    p95_ms = percentile(latencies, 0.95)
    throughput = total_commands / total_duration if total_duration > 0 else 0.0

    print(f"profile={args.profile}")
    print(f"mode={args.mode}")
    print(f"clients={clients}")
    print(f"iterations_per_client={iterations}")
    print(f"request_pairs={total_request_pairs}")
    print(f"total_commands={total_commands}")
    print(f"successes={successes}")
    print(f"failures={failures}")
    print(f"avg_pair_latency_ms={avg_ms:.2f}")
    print(f"p95_pair_latency_ms={p95_ms:.2f}")
    print(f"throughput_cmd_per_sec={throughput:.2f}")

    if sample_failures:
        print("sample_failures:")
        for first_reply, second_reply in sample_failures:
            print(f"  - first={first_reply} second={second_reply}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
