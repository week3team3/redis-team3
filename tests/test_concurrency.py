from __future__ import annotations

import threading

from tests.support import MiniRedisTCPTestCase


class MiniRedisConcurrencyTests(MiniRedisTCPTestCase):
    def test_parallel_set_get_workload(self) -> None:
        client_count = 10
        iterations = 20
        barrier = threading.Barrier(client_count)
        errors: list[str] = []
        errors_lock = threading.Lock()

        def worker(worker_id: int) -> None:
            barrier.wait()
            for index in range(iterations):
                key = f"client:{worker_id}:key:{index}"
                value = f"value-{worker_id}-{index}"
                set_reply = self.send(f"SET {key} {value}")
                get_reply = self.send(f"GET {key}")
                if set_reply != "+OK" or get_reply != f"${value}":
                    with errors_lock:
                        errors.append(
                            f"worker={worker_id} index={index} set={set_reply} get={get_reply}"
                        )

        threads = [
            threading.Thread(target=worker, args=(worker_id,), daemon=True)
            for worker_id in range(client_count)
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(self.server.store.size(), client_count * iterations)

    def test_parallel_incr_on_same_key_is_atomic(self) -> None:
        client_count = 10
        iterations = 25
        barrier = threading.Barrier(client_count)
        errors: list[str] = []
        errors_lock = threading.Lock()

        def worker() -> None:
            barrier.wait()
            for _ in range(iterations):
                reply = self.send("INCR shared-counter")
                if not reply.startswith(":"):
                    with errors_lock:
                        errors.append(reply)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(client_count)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(self.send("GET shared-counter"), f"${client_count * iterations}")
