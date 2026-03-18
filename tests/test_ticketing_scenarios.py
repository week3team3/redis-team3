from __future__ import annotations

import json
import threading
import time
import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


class MiniRedisTicketingScenarioTest(unittest.TestCase):
    """기능 테스트를 시나리오 단위로 검증한다.

    왜 이렇게 테스트하나:
    - 네트워크 포트를 띄우지 않아도 실제 명령 처리 흐름(handle_command)은 그대로 검증할 수 있다.
    - 티켓팅 시나리오는 결국 Mini Redis 상태 저장소가 어떻게 반영되는지 보는 것이 핵심이라
      RESP 명령 처리부를 직접 때리는 방식이 가장 빠르고 안정적이다.
    """

    def setUp(self) -> None:
        with server.store_lock:
            server.store.clear()

    def run_command(self, *tokens: str) -> tuple[str, str | int | None]:
        return server.handle_command(list(tokens))

    def run_json(self, *tokens: str) -> dict:
        kind, value = self.run_command(*tokens)
        self.assertEqual(kind, "bulk", f"expected bulk json, got {kind}:{value}")
        self.assertIsInstance(value, str)
        return json.loads(value)

    def test_core_store_expire_and_invalidate(self) -> None:
        """Mini Redis 핵심 기능: SET/GET/EXISTS/EXPIRE/INVALIDATE."""

        kind, value = self.run_command("SET", "user:1", "ready")
        self.assertEqual((kind, value), ("simple", "OK"))

        self.assertEqual(self.run_command("GET", "user:1"), ("bulk", "ready"))
        self.assertEqual(self.run_command("EXISTS", "user:1"), ("integer", 1))
        self.assertEqual(self.run_command("EXPIRE", "user:1", "1"), ("integer", 1))

        ttl_kind, ttl_value = self.run_command("TTL", "user:1")
        self.assertEqual(ttl_kind, "integer")
        self.assertGreaterEqual(int(ttl_value), 0)

        self.assertEqual(self.run_command("INVALIDATE", "user:1", "stale-cache"), ("integer", 1))
        self.assertEqual(self.run_command("GET", "user:1"), ("bulk", None))
        self.assertEqual(self.run_command("EXISTS", "user:1"), ("integer", 0))

    def test_ticket_entry_waiting_and_confirm_promotion(self) -> None:
        """티켓팅 핵심 흐름: 입장 -> 대기 -> hold -> confirm -> 다음 사람 승격."""

        state = self.run_json("TICKET_INIT", "concert-demo", "1", "5", "A1", "A2")
        self.assertEqual(state["metrics"]["total_seats"], 2)

        admitted = self.run_json("TICKET_ENTER", "concert-demo", "user-a")
        waiting = self.run_json("TICKET_ENTER", "concert-demo", "user-b")
        self.assertEqual(admitted["status"], "ADMITTED")
        self.assertEqual(waiting["status"], "WAITING")

        hold = self.run_json("TICKET_HOLD", "concert-demo", "user-a", "A1")
        self.assertEqual(hold["status"], "HELD")

        confirmed = self.run_json("TICKET_CONFIRM", "concert-demo", "user-a")
        self.assertEqual(confirmed["status"], "CONFIRMED")

        promoted = self.run_json("TICKET_STATUS", "concert-demo", "user-b")
        self.assertEqual(promoted["status"], "ADMITTED")

        final_state = self.run_json("TICKET_STATE", "concert-demo")
        sold_seat = next(seat for seat in final_state["seats"] if seat["seat_id"] == "A1")
        self.assertEqual(sold_seat["status"], "SOLD")
        self.assertEqual(final_state["queue_size"], 0)

    def test_ticket_hold_ttl_timeout_releases_seat_but_retains_admission(self) -> None:
        """좌석 hold TTL이 끝나면 좌석이 풀리지만 유저는 대기실로 튕기지 않고 유지되는지 본다."""

        self.run_json("TICKET_INIT", "concert-demo", "1", "1", "A1", "A2")
        self.run_json("TICKET_ENTER", "concert-demo", "user-a")
        self.run_json("TICKET_ENTER", "concert-demo", "user-b")

        hold = self.run_json("TICKET_HOLD", "concert-demo", "user-a", "A1")
        self.assertEqual(hold["status"], "HELD")

        time.sleep(1.2)

        state_after_timeout = self.run_json("TICKET_STATE", "concert-demo")
        released_seat = next(seat for seat in state_after_timeout["seats"] if seat["seat_id"] == "A1")
        waiting_user = self.run_json("TICKET_STATUS", "concert-demo", "user-b")
        expired_hold_user = self.run_json("TICKET_STATUS", "concert-demo", "user-a")

        self.assertEqual(released_seat["status"], "AVAILABLE")
        self.assertEqual(expired_hold_user["status"], "ADMITTED")  # Still admitted!
        self.assertEqual(waiting_user["status"], "WAITING")        # Still waiting because user-a is still taking the slot

    def test_ticket_cancel_releases_seat_but_retains_admission(self) -> None:
        """hold 취소 시 좌석이 풀리지만, 사용자는 여전히 입장 상태로 남아서 대기자가 들어오지 않는지 본다."""

        self.run_json("TICKET_INIT", "concert-demo", "1", "5", "A1", "A2")
        self.run_json("TICKET_ENTER", "concert-demo", "user-a")
        self.run_json("TICKET_ENTER", "concert-demo", "user-b")
        self.run_json("TICKET_HOLD", "concert-demo", "user-a", "A1")

        cancelled = self.run_json("TICKET_CANCEL", "concert-demo", "user-a")
        self.assertEqual(cancelled["status"], "CANCELLED")

        state_after_cancel = self.run_json("TICKET_STATE", "concert-demo")
        released_seat = next(seat for seat in state_after_cancel["seats"] if seat["seat_id"] == "A1")
        waiting_user = self.run_json("TICKET_STATUS", "concert-demo", "user-b")
        cancelled_user = self.run_json("TICKET_STATUS", "concert-demo", "user-a")

        self.assertEqual(released_seat["status"], "AVAILABLE")
        self.assertEqual(cancelled_user["status"], "ADMITTED")
        self.assertEqual(waiting_user["status"], "WAITING")
        
        # Now finally user-a truly exits.
        exited = self.run_json("TICKET_EXIT", "concert-demo", "user-a")
        self.assertEqual(exited["status"], "EXITED")
        
        promoted_user = self.run_json("TICKET_STATUS", "concert-demo", "user-b")
        self.assertEqual(promoted_user["status"], "ADMITTED")

    def test_same_seat_concurrency_allows_only_one_hold(self) -> None:
        """safe 환경 검증: 같은 좌석을 동시에 잡아도 실제 성공은 한 명만 나와야 한다."""

        self.run_json("TICKET_INIT", "concert-demo", "2", "5", "A1", "A2")
        self.run_json("TICKET_ENTER", "concert-demo", "user-a")
        self.run_json("TICKET_ENTER", "concert-demo", "user-b")

        barrier = threading.Barrier(2)
        results: list[dict] = []
        errors: list[BaseException] = []
        results_lock = threading.Lock()

        def runner(user_id: str) -> None:
            try:
                barrier.wait()
                payload = self.run_json("TICKET_HOLD", "concert-demo", user_id, "A1")
                with results_lock:
                    results.append(payload)
            except BaseException as exc:  # pragma: no cover - test diagnostic path
                with results_lock:
                    errors.append(exc)

        threads = [
            threading.Thread(target=runner, args=("user-a",), daemon=True),
            threading.Thread(target=runner, args=("user-b",), daemon=True),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertFalse(errors, f"unexpected thread errors: {errors}")
        self.assertEqual(len(results), 2)

        success_count = sum(1 for item in results if item.get("ok"))
        fail_reasons = sorted(item.get("reason") for item in results if not item.get("ok"))

        self.assertEqual(success_count, 1)
        self.assertEqual(fail_reasons, ["seat_not_available"])

        final_state = self.run_json("TICKET_STATE", "concert-demo")
        held_seat = next(seat for seat in final_state["seats"] if seat["seat_id"] == "A1")
        self.assertEqual(held_seat["status"], "HELD")


if __name__ == "__main__":
    unittest.main()
