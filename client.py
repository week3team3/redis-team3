"""
Simple RESP client for manual experiments.

Flow:
- user input      -> "SET a 10"
- build_request() -> RESP bytes
- socket send     -> server
- read_response() -> parse server response

Examples to try:
- SET a 10
- GET a
- EXISTS a
- INCR counter
- DECR counter
- SET lock 1 NX
- CLAIM stock
- BADCOMMAND

Type `quit` or `exit` to stop.
"""

from __future__ import annotations

import argparse
import shlex
import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox


HOST = "127.0.0.1"
PORT = 6380


def build_request(tokens: list[str]) -> bytes:
    """Turn ['SET', 'a', '10'] into one RESP array request."""

    parts = [f"*{len(tokens)}\r\n".encode()]
    for token in tokens:
        encoded = token.encode()
        parts.append(f"${len(encoded)}\r\n".encode())
        parts.append(encoded + b"\r\n")
    return b"".join(parts)


def read_line(sock: socket.socket) -> bytes:
    """Read until CRLF, used for RESP line-oriented parsing."""

    data = b""
    while not data.endswith(b"\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("server closed the connection")
        data += chunk
    return data[:-2]


def read_response(sock: socket.socket) -> str:
    """
    Read one RESP response and return a readable string.

    We decode enough to inspect:
    - simple string
    - bulk string
    - nil
    - integer
    - error
    """

    prefix = sock.recv(1)
    if not prefix:
        raise ConnectionError("server closed the connection")

    if prefix == b"+":
        return f"simple string: {read_line(sock).decode()}"

    if prefix == b"-":
        return f"error: {read_line(sock).decode()}"

    if prefix == b":":
        return f"integer: {read_line(sock).decode()}"

    if prefix == b"$":
        length = int(read_line(sock).decode())
        if length == -1:
            return "nil"
        data = b""
        while len(data) < length + 2:
            chunk = sock.recv(length + 2 - len(data))
            if not chunk:
                raise ConnectionError("server closed the connection")
            data += chunk
        return f"bulk string: {data[:-2].decode()}"

    raise ValueError(f"unsupported RESP prefix: {prefix!r}")


def send_command(sock: socket.socket, raw: str) -> tuple[bytes, str]:
    """Build one RESP request, send it, and return the request/response pair."""

    tokens = shlex.split(raw)
    request = build_request(tokens)
    sock.sendall(request)
    response = read_response(sock)
    return request, response


def request_once(raw: str) -> str:
    """Open a short-lived connection, send one command, and return the decoded response."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        _, response = send_command(sock, raw)
        return response


def run_cli() -> None:
    print(f"Connect to {HOST}:{PORT}")
    print("Enter commands like: SET a 10, GET a, DEL a, INCR n, SET lock 1 NX, CLAIM stock")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        while True:
            raw = input("redis> ").strip()
            if not raw:
                continue

            if raw.lower() in {"quit", "exit"}:
                print("bye")
                break

            try:
                request, response = send_command(sock, raw)
            except (ConnectionError, ValueError) as exc:
                print(f"response error: {exc}")
                continue

            print(f"RESP request bytes: {request!r}")
            print(f"server -> {response}")


class CouponGUI:
    """Small coupon-style GUI for stock experiments."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        self.root = tk.Tk()
        self.root.title("Mini Redis Coupon Lab")
        self.root.geometry("430x560")
        self.root.configure(bg="#f5efe6")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.key_var = tk.StringVar(value="stock")
        self.seed_var = tk.StringVar(value="100")
        self.ttl_input_var = tk.StringVar(value="15")
        self.burst_count_var = tk.StringVar(value="100")
        self.stock_var = tk.StringVar(value="-")
        self.ttl_var = tk.StringVar(value="ttl: no expiry")
        self.status_var = tk.StringVar(value="서버에 연결됨")
        self.burst_result_var = tk.StringVar(value="burst result: not run")
        self.auto_refresh_var = tk.BooleanVar(value=True)
        self.auto_refresh_job: str | None = None
        self.button_style = {
            "font": ("Helvetica", 13, "bold"),
            "relief": "flat",
            "bd": 0,
            "activeforeground": "#1f1a16",
            "activebackground": "#ead7b7",
            "cursor": "hand2",
            "pady": 10,
        }

        self.build_layout()
        self.refresh_state()
        self.schedule_auto_refresh()

    def build_layout(self) -> None:
        wrapper = tk.Frame(self.root, bg="#f5efe6", padx=18, pady=18)
        wrapper.pack(fill="both", expand=True)

        tk.Label(
            wrapper,
            text="Coupon Stock Demo",
            font=("Helvetica", 22, "bold"),
            bg="#f5efe6",
            fg="#372c22",
        ).pack(anchor="w")

        tk.Label(
            wrapper,
            text="Try stock sharing, delete, and TTL expiry across two GUI windows.",
            font=("Helvetica", 11),
            bg="#f5efe6",
            fg="#6b5b4d",
        ).pack(anchor="w", pady=(4, 16))

        coupon = tk.Frame(
            wrapper,
            bg="#fff7e8",
            bd=0,
            highlightthickness=2,
            highlightbackground="#e3c58e",
            padx=12,
            pady=10,
        )
        coupon.pack(fill="x")

        tk.Label(
            coupon,
            text="LIMITED COUPON",
            font=("Helvetica", 12, "bold"),
            bg="#fff7e8",
            fg="#b05a2b",
        ).pack(pady=(6, 10))

        tk.Label(
            coupon,
            textvariable=self.stock_var,
            font=("Helvetica", 40, "bold"),
            bg="#fff7e8",
            fg="#2d3a2d",
        ).pack()

        tk.Label(
            coupon,
            text="remaining",
            font=("Helvetica", 12),
            bg="#fff7e8",
            fg="#6b5b4d",
        ).pack(pady=(8, 3))
        tk.Label(
            coupon,
            textvariable=self.ttl_var,
            font=("Helvetica", 11, "bold"),
            bg="#fff7e8",
            fg="#8b4b2b",
        ).pack(pady=(0, 6))

        controls = tk.Frame(wrapper, bg="#f5efe6")
        controls.pack(fill="x", pady=(18, 10))
        controls.columnconfigure(1, weight=1)

        tk.Label(controls, text="Key", bg="#f5efe6", fg="#372c22").grid(row=0, column=0, sticky="w")
        tk.Entry(controls, textvariable=self.key_var, width=18).grid(row=0, column=1, sticky="we", padx=(10, 0))

        tk.Label(controls, text="Initial Stock", bg="#f5efe6", fg="#372c22").grid(row=1, column=0, sticky="w", pady=(10, 0))
        tk.Entry(controls, textvariable=self.seed_var, width=18).grid(row=1, column=1, sticky="we", padx=(10, 0), pady=(10, 0))
        tk.Label(controls, text="TTL Seconds", bg="#f5efe6", fg="#372c22").grid(row=2, column=0, sticky="w", pady=(10, 0))
        tk.Entry(controls, textvariable=self.ttl_input_var, width=18).grid(row=2, column=1, sticky="we", padx=(10, 0), pady=(10, 0))
        tk.Label(controls, text="Burst Users", bg="#f5efe6", fg="#372c22").grid(row=3, column=0, sticky="w", pady=(10, 0))
        tk.Entry(controls, textvariable=self.burst_count_var, width=18).grid(row=3, column=1, sticky="we", padx=(10, 0), pady=(10, 0))

        actions = tk.Frame(wrapper, bg="#f5efe6")
        actions.pack(fill="x", pady=(6, 14))

        tk.Button(
            actions,
            text="Set Stock",
            command=self.seed_stock,
            bg="#d8893d",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Button(
            actions,
            text="Refresh State",
            command=self.refresh_state,
            bg="#4f7c82",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Button(
            actions,
            text="Claim Coupon",
            command=self.claim_coupon,
            bg="#2e6f40",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Button(
            actions,
            text="Apply TTL",
            command=self.apply_ttl,
            bg="#9f6f52",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Button(
            actions,
            text="Delete Coupon Key",
            command=self.delete_coupon,
            bg="#c65d52",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Checkbutton(
            actions,
            text="Auto Refresh (1s)",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh,
            bg="#f5efe6",
            fg="#372c22",
            selectcolor="#f5efe6",
            activebackground="#f5efe6",
            activeforeground="#372c22",
            font=("Helvetica", 11, "bold"),
        ).pack(anchor="w", pady=(8, 0))

        burst_frame = tk.Frame(wrapper, bg="#efe4d2", padx=12, pady=12)
        burst_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            burst_frame,
            text="Concurrency Lab",
            font=("Helvetica", 14, "bold"),
            bg="#efe4d2",
            fg="#372c22",
        ).pack(anchor="w")
        tk.Label(
            burst_frame,
            text="Safe = CLAIM 1회. Unsafe = GET 후 계산 후 SET.",
            font=("Helvetica", 10),
            bg="#efe4d2",
            fg="#6b5b4d",
        ).pack(anchor="w", pady=(3, 8))
        tk.Button(
            burst_frame,
            text="Run 100 Safe Claim",
            command=self.run_safe_burst,
            bg="#5c8a5c",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Button(
            burst_frame,
            text="Run 100 Unsafe Buy",
            command=self.run_unsafe_burst,
            bg="#b36a52",
            fg="#1f1a16",
            **self.button_style,
        ).pack(fill="x", pady=4)
        tk.Label(
            burst_frame,
            textvariable=self.burst_result_var,
            font=("Helvetica", 11, "bold"),
            bg="#efe4d2",
            fg="#372c22",
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

        manual = tk.Frame(wrapper, bg="#f5efe6")
        manual.pack(fill="x", pady=(4, 10))

        self.command_entry = tk.Entry(manual)
        self.command_entry.pack(side="left", fill="x", expand=True)
        self.command_entry.insert(0, "GET stock")
        tk.Button(
            manual,
            text="Send",
            command=self.send_manual,
            bg="#d7ccb8",
            fg="#1f1a16",
            **self.button_style,
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            wrapper,
            textvariable=self.status_var,
            font=("Helvetica", 11, "bold"),
            bg="#f5efe6",
            fg="#7a2f2f",
            anchor="w",
        ).pack(fill="x")

        self.log_box = tk.Text(wrapper, height=11, bg="#fffdf8", fg="#2f2a25")
        self.log_box.pack(fill="both", expand=True, pady=(10, 0))
        self.log_box.insert("end", "실험 로그가 여기에 쌓입니다.\n")
        self.log_box.configure(state="disabled")

    def append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def send_raw_command(self, raw: str) -> str:
        request, response = send_command(self.sock, raw)
        self.append_log(f"> {raw}")
        self.append_log(f"  RESP {request!r}")
        self.append_log(f"  <- {response}")
        self.status_var.set(response)
        return response

    def refresh_stock(self) -> None:
        key = self.key_var.get().strip() or "stock"
        response = self.send_raw_command(f'GET "{key}"')
        if response == "nil":
            self.stock_var.set("sold out")
        elif response.startswith("bulk string: "):
            self.stock_var.set(response.replace("bulk string: ", "", 1))
        else:
            self.stock_var.set("?")

    def refresh_ttl(self) -> None:
        key = self.key_var.get().strip() or "stock"
        response = self.send_raw_command(f'TTL "{key}"')
        if response == "integer: -2":
            self.ttl_var.set("ttl: missing")
        elif response == "integer: -1":
            self.ttl_var.set("ttl: no expiry")
        elif response.startswith("integer: "):
            seconds = response.replace("integer: ", "", 1)
            self.ttl_var.set(f"ttl: {seconds}s")
        else:
            self.ttl_var.set("ttl: error")

    def refresh_state(self) -> None:
        self.refresh_stock()
        self.refresh_ttl()

    def seed_stock(self) -> None:
        key = self.key_var.get().strip() or "stock"
        initial = self.seed_var.get().strip() or "100"
        self.send_raw_command(f'SET "{key}" "{initial}"')
        self.refresh_state()

    def claim_coupon(self) -> None:
        key = self.key_var.get().strip() or "stock"
        response = self.send_raw_command(f'CLAIM "{key}"')
        if response.startswith("integer: "):
            self.stock_var.set(response.replace("integer: ", "", 1))
            self.refresh_ttl()
            return
        if "sold out" in response:
            self.stock_var.set("0")
            self.refresh_ttl()
            messagebox.showinfo("쿠폰", "재고가 모두 소진됐습니다.")

    def apply_ttl(self) -> None:
        key = self.key_var.get().strip() or "stock"
        seconds = self.ttl_input_var.get().strip() or "15"
        response = self.send_raw_command(f'EXPIRE "{key}" "{seconds}"')
        if response == "integer: 1":
            self.refresh_ttl()
            return
        if response == "integer: 0":
            messagebox.showinfo("TTL", "먼저 key를 만든 뒤 TTL을 적용하세요.")

    def delete_coupon(self) -> None:
        key = self.key_var.get().strip() or "stock"
        self.send_raw_command(f'DEL "{key}"')
        self.refresh_state()

    def parse_integer_response(self, response: str) -> int | None:
        if not response.startswith("integer: "):
            return None
        try:
            return int(response.replace("integer: ", "", 1))
        except ValueError:
            return None

    def read_current_stock(self, key: str) -> int | None:
        response = request_once(f'GET "{key}"')
        if response == "nil":
            return None
        if not response.startswith("bulk string: "):
            return None
        try:
            return int(response.replace("bulk string: ", "", 1))
        except ValueError:
            return None

    def run_burst_test(self, mode: str) -> None:
        key = self.key_var.get().strip() or "stock"
        try:
            total_users = int(self.burst_count_var.get().strip() or "100")
        except ValueError:
            messagebox.showerror("Burst", "Burst Users must be an integer.")
            return

        initial_stock = self.read_current_stock(key)
        if initial_stock is None:
            messagebox.showerror("Burst", "먼저 숫자 재고를 세팅하세요. 예: stock = 100")
            return

        success_count = 0
        fail_count = 0
        success_lock = threading.Lock()
        barrier = threading.Barrier(total_users)

        def mark_result(success: bool) -> None:
            nonlocal success_count, fail_count
            with success_lock:
                if success:
                    success_count += 1
                else:
                    fail_count += 1

        def safe_worker() -> None:
            try:
                barrier.wait()
                response = request_once(f'CLAIM "{key}"')
                mark_result(response.startswith("integer: "))
            except Exception:
                mark_result(False)

        def unsafe_worker() -> None:
            try:
                barrier.wait()
                response = request_once(f'GET "{key}"')
                if response == "nil" or not response.startswith("bulk string: "):
                    mark_result(False)
                    return

                current = int(response.replace("bulk string: ", "", 1))
                if current <= 0:
                    mark_result(False)
                    return

                # Delay widens the race window so duplicated success becomes visible.
                time.sleep(0.01)
                request_once(f'SET "{key}" "{current - 1}"')
                mark_result(True)
            except Exception:
                mark_result(False)

        worker = safe_worker if mode == "safe" else unsafe_worker
        threads = [threading.Thread(target=worker) for _ in range(total_users)]

        self.status_var.set(f"running {mode} burst...")
        self.burst_result_var.set(f"burst result: running {total_users} users")

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        final_stock = self.read_current_stock(key)
        final_stock_text = "missing" if final_stock is None else str(final_stock)
        oversell = success_count > initial_stock
        self.burst_result_var.set(
            f"burst result: mode={mode}, users={total_users}, "
            f"success={success_count}, fail={fail_count}, "
            f"initial={initial_stock}, final={final_stock_text}, oversell={oversell}"
        )
        self.append_log(
            f"[BURST] mode={mode} users={total_users} success={success_count} "
            f"fail={fail_count} initial={initial_stock} final={final_stock_text} oversell={oversell}"
        )
        self.refresh_state()

    def run_safe_burst(self) -> None:
        self.run_burst_test("safe")

    def run_unsafe_burst(self) -> None:
        self.run_burst_test("unsafe")

    def send_manual(self) -> None:
        raw = self.command_entry.get().strip()
        if not raw:
            return
        response = self.send_raw_command(raw)
        key = self.key_var.get().strip() or "stock"
        if key in raw:
            self.refresh_state()
        elif response.startswith("bulk string: "):
            self.stock_var.set(response.replace("bulk string: ", "", 1))

    def schedule_auto_refresh(self) -> None:
        if not self.auto_refresh_var.get():
            self.auto_refresh_job = None
            return
        self.auto_refresh_job = self.root.after(1000, self.run_auto_refresh)

    def run_auto_refresh(self) -> None:
        self.auto_refresh_job = None
        try:
            self.refresh_state()
        except (ConnectionError, ValueError, OSError) as exc:
            self.status_var.set(f"auto refresh error: {exc}")
            self.auto_refresh_var.set(False)
            return
        self.schedule_auto_refresh()

    def toggle_auto_refresh(self) -> None:
        if self.auto_refresh_var.get():
            self.status_var.set("auto refresh on")
            if self.auto_refresh_job is None:
                self.schedule_auto_refresh()
            return
        self.status_var.set("auto refresh off")
        if self.auto_refresh_job is not None:
            self.root.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None

    def close(self) -> None:
        try:
            if self.auto_refresh_job is not None:
                self.root.after_cancel(self.auto_refresh_job)
            self.sock.close()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RESP learning client")
    parser.add_argument("--gui", action="store_true", help="open a small coupon stock GUI")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.gui:
        CouponGUI().run()
        return
    run_cli()


if __name__ == "__main__":
    main()
