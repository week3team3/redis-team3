import ast
import socket
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText


class RedisGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Virtual Redis Control Center")
        self.root.geometry("1380x860")
        self.root.minsize(1180, 760)

        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="6379")
        self.key_var = tk.StringVar()
        self.command_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Disconnected")
        self.last_ping_var = tk.StringVar(value="n/a")
        self.dbsize_var = tk.StringVar(value="-")
        self.key_count_var = tk.StringVar(value="-")
        self.expires_var = tk.StringVar(value="-")
        self.inspector_exists_var = tk.StringVar(value="-")
        self.inspector_type_var = tk.StringVar(value="-")
        self.inspector_ttl_var = tk.StringVar(value="-")
        self.inspector_length_var = tk.StringVar(value="-")

        self.current_keys = []

        self._configure_style()
        self._build_layout()
        self._set_connection_state(False)

    def _configure_style(self):
        bg = "#0a1020"
        panel = "#121a30"
        card = "#18233f"
        accent = "#17c964"
        text = "#eaf2ff"
        muted = "#89a0c2"
        stroke = "#2b3d69"

        self.root.configure(bg=bg)

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("App.TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel, relief="flat")
        style.configure("Card.TFrame", background=card, relief="flat")
        style.configure("TLabel", background=panel, foreground=text, font=("Segoe UI", 10))
        style.configure("PanelTitle.TLabel", background=panel, foreground=text, font=("Segoe UI Semibold", 15))
        style.configure("Muted.TLabel", background=panel, foreground=muted, font=("Segoe UI", 10))
        style.configure("CardValue.TLabel", background=card, foreground=text, font=("Consolas", 18, "bold"))
        style.configure("CardLabel.TLabel", background=card, foreground=muted, font=("Segoe UI", 10))
        style.configure("TButton", background=card, foreground=text, borderwidth=0, padding=(12, 8))
        style.map("TButton", background=[("active", stroke)])
        style.configure("Accent.TButton", background=accent, foreground="#04100a", font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", "#2ee97d")])
        style.configure("TEntry", fieldbackground="#0b1327", foreground=text, insertcolor=text, bordercolor=stroke)
        style.configure("TCombobox", fieldbackground="#0b1327", foreground=text, bordercolor=stroke)
        style.configure("Treeview", background="#0b1327", fieldbackground="#0b1327", foreground=text, bordercolor=stroke)
        style.configure("Treeview.Heading", background=card, foreground=text, font=("Segoe UI Semibold", 10))

    def _build_layout(self):
        shell = ttk.Frame(self.root, style="App.TFrame", padding=18)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)
        shell.rowconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        dashboard = ttk.Frame(shell, style="Panel.TFrame", padding=18)
        dashboard.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        inspector = ttk.Frame(shell, style="Panel.TFrame", padding=18)
        inspector.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        console = ttk.Frame(shell, style="Panel.TFrame", padding=18)
        console.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        activity = ttk.Frame(shell, style="Panel.TFrame", padding=18)
        activity.grid(row=1, column=1, sticky="nsew")

        self._build_dashboard(dashboard)
        self._build_inspector(inspector)
        self._build_console(console)
        self._build_activity_log(activity)

    def _build_dashboard(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(2, weight=1)

        ttk.Label(parent, text="Dashboard", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            parent,
            text="Connect to the Python virtual Redis server and keep an eye on keyspace health.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 18))

        controls = ttk.Frame(parent, style="Panel.TFrame")
        controls.grid(row=2, column=0, columnspan=3, sticky="ew")
        controls.columnconfigure(5, weight=1)

        ttk.Label(controls, text="Host").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.host_var, width=18).grid(row=1, column=0, sticky="ew", padx=(0, 10))
        ttk.Label(controls, text="Port").grid(row=0, column=1, sticky="w")
        ttk.Entry(controls, textvariable=self.port_var, width=10).grid(row=1, column=1, sticky="ew", padx=(0, 10))
        ttk.Button(controls, text="Connect", style="Accent.TButton", command=self.connect).grid(row=1, column=2, padx=(0, 8))
        ttk.Button(controls, text="Refresh", command=self.refresh_dashboard).grid(row=1, column=3, padx=(0, 8))
        ttk.Button(controls, text="Load Keys", command=self.load_keys).grid(row=1, column=4)

        status_pill = tk.Label(
            controls,
            textvariable=self.status_var,
            bg="#18233f",
            fg="#eaf2ff",
            padx=12,
            pady=7,
            font=("Segoe UI Semibold", 10),
        )
        status_pill.grid(row=1, column=5, sticky="e")

        self._make_metric_card(parent, "Server Ping", self.last_ping_var).grid(row=3, column=0, sticky="nsew", pady=(18, 14), padx=(0, 8))
        self._make_metric_card(parent, "DBSIZE", self.dbsize_var).grid(row=3, column=1, sticky="nsew", pady=(18, 14), padx=4)
        self._make_metric_card(parent, "Keys With TTL", self.expires_var).grid(row=3, column=2, sticky="nsew", pady=(18, 14), padx=(8, 0))

        keys_panel = ttk.Frame(parent, style="Card.TFrame", padding=14)
        keys_panel.grid(row=4, column=0, columnspan=3, sticky="nsew")
        keys_panel.columnconfigure(0, weight=1)
        keys_panel.rowconfigure(1, weight=1)

        ttk.Label(keys_panel, text="Key Snapshot", background="#18233f", foreground="#eaf2ff", font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w")
        ttk.Label(keys_panel, textvariable=self.key_count_var, background="#18233f", foreground="#89a0c2").grid(row=0, column=1, sticky="e")

        self.key_listbox = tk.Listbox(
            keys_panel,
            bg="#0b1327",
            fg="#eaf2ff",
            selectbackground="#1f6feb",
            selectforeground="#ffffff",
            relief="flat",
            font=("Consolas", 11),
        )
        self.key_listbox.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self.key_listbox.bind("<<ListboxSelect>>", self.on_key_selected)

    def _make_metric_card(self, parent, label, variable):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        ttk.Label(frame, text=label, style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=variable, style="CardValue.TLabel").pack(anchor="w", pady=(8, 0))
        return frame

    def _build_inspector(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

        ttk.Label(parent, text="Value Inspector", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            parent,
            text="Inspect a single key and run the most useful metadata queries against it.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        key_row = ttk.Frame(parent, style="Panel.TFrame")
        key_row.grid(row=2, column=0, sticky="ew")
        key_row.columnconfigure(0, weight=1)

        ttk.Entry(key_row, textvariable=self.key_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(key_row, text="Inspect", style="Accent.TButton", command=self.inspect_key).grid(row=0, column=1)

        meta = ttk.Frame(parent, style="Card.TFrame", padding=14)
        meta.grid(row=3, column=0, sticky="ew", pady=(14, 14))
        for column in range(4):
            meta.columnconfigure(column, weight=1)

        self._make_meta_block(meta, "Exists", self.inspector_exists_var).grid(row=0, column=0, sticky="ew")
        self._make_meta_block(meta, "Type", self.inspector_type_var).grid(row=0, column=1, sticky="ew")
        self._make_meta_block(meta, "TTL", self.inspector_ttl_var).grid(row=0, column=2, sticky="ew")
        self._make_meta_block(meta, "Length", self.inspector_length_var).grid(row=0, column=3, sticky="ew")

        value_card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        value_card.grid(row=4, column=0, sticky="nsew")
        value_card.columnconfigure(0, weight=1)
        value_card.rowconfigure(1, weight=1)

        ttk.Label(value_card, text="Value", background="#18233f", foreground="#eaf2ff", font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w")

        self.value_text = ScrolledText(
            value_card,
            wrap="word",
            bg="#0b1327",
            fg="#dce7ff",
            insertbackground="#dce7ff",
            relief="flat",
            font=("Consolas", 11),
            height=12,
        )
        self.value_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.value_text.configure(state="disabled")

        actions = ttk.Frame(parent, style="Panel.TFrame")
        actions.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        actions.columnconfigure((0, 1, 2, 3), weight=1)
        ttk.Button(actions, text="GET", command=lambda: self.run_key_command("GET {key}")).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="TTL", command=lambda: self.run_key_command("TTL {key}")).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(actions, text="TYPE", command=lambda: self.run_key_command("TYPE {key}")).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(actions, text="DEL", command=lambda: self.run_key_command("DEL {key}", refresh=True)).grid(row=0, column=3, sticky="ew", padx=(6, 0))

    def _make_meta_block(self, parent, label, variable):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=6)
        ttk.Label(frame, text=label, background="#18233f", foreground="#89a0c2", font=("Segoe UI", 9)).pack(anchor="w")
        ttk.Label(frame, textvariable=variable, background="#18233f", foreground="#eaf2ff", font=("Consolas", 15, "bold")).pack(anchor="w", pady=(6, 0))
        return frame

    def _build_console(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        ttk.Label(parent, text="Command Console", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            parent,
            text="Send raw commands to the server. Great for experimenting with your custom Redis commands.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        command_row = ttk.Frame(parent, style="Panel.TFrame")
        command_row.grid(row=2, column=0, sticky="ew")
        command_row.columnconfigure(0, weight=1)

        entry = ttk.Entry(command_row, textvariable=self.command_var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        entry.bind("<Return>", lambda _event: self.execute_command())
        ttk.Button(command_row, text="Send", style="Accent.TButton", command=self.execute_command).grid(row=0, column=1)

        quick_panel = ttk.Frame(parent, style="Card.TFrame", padding=14)
        quick_panel.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        quick_panel.columnconfigure(0, weight=1)
        quick_panel.rowconfigure(1, weight=1)

        ttk.Label(quick_panel, text="Quick Commands", background="#18233f", foreground="#eaf2ff", font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w")

        self.quick_list = tk.Listbox(
            quick_panel,
            bg="#0b1327",
            fg="#eaf2ff",
            selectbackground="#1f6feb",
            selectforeground="#ffffff",
            relief="flat",
            font=("Consolas", 11),
            height=10,
        )
        self.quick_list.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        for command in [
            "PING",
            "INFO",
            "DBSIZE",
            "KEYS *",
            "SET sample hello",
            "GET sample",
            "INCR counter",
            "MSET alpha 1 beta 2",
            "MGET alpha beta",
            "EXPIRE sample 30",
        ]:
            self.quick_list.insert("end", command)
        self.quick_list.bind("<Double-Button-1>", self.use_quick_command)

    def _build_activity_log(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        ttk.Label(parent, text="Activity Log", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            parent,
            text="Every request and response is recorded here so it feels like a lightweight Redis operations console.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        self.log_text = ScrolledText(
            parent,
            wrap="word",
            bg="#0b1327",
            fg="#dce7ff",
            insertbackground="#dce7ff",
            relief="flat",
            font=("Consolas", 10),
        )
        self.log_text.grid(row=2, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def connect(self):
        try:
            response = self.send_command("PING", log_request=False)
        except Exception as exc:
            self._set_connection_state(False)
            messagebox.showerror("Connection failed", str(exc))
            self.log(f"[connect] failed: {exc}")
            return

        self._set_connection_state(True)
        self.last_ping_var.set(response)
        self.log(f"[connect] success -> {self.host_var.get()}:{self.port_var.get()}")
        self.refresh_dashboard()

    def _set_connection_state(self, connected):
        if connected:
            self.status_var.set("Connected")
        else:
            self.status_var.set("Disconnected")

    def send_command(self, command, log_request=True):
        host = self.host_var.get().strip()
        port_text = self.port_var.get().strip()
        if not host or not port_text:
            raise ValueError("Host and port are required.")

        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError("Port must be a number.") from exc

        if log_request:
            self.log(f"> {command}")

        with socket.create_connection((host, port), timeout=2.0) as sock:
            sock.settimeout(0.2)
            sock.sendall((command.strip() + "\n").encode("utf-8"))

            chunks = []
            while True:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    break

                if not data:
                    break
                chunks.append(data)

                if len(data) < 4096:
                    break

        raw_response = b"".join(chunks).decode("utf-8", errors="replace").strip()
        self.log(f"< {raw_response if raw_response else '(no response)'}")
        return raw_response

    def execute_command(self):
        command = self.command_var.get().strip()
        if not command:
            return

        try:
            response = self.send_command(command)
            self.command_var.set("")
            self._set_connection_state(True)
            self._react_to_command(command, response)
        except Exception as exc:
            self._set_connection_state(False)
            self.log(f"[error] {exc}")
            messagebox.showerror("Command failed", str(exc))

    def _react_to_command(self, command, response):
        upper = command.split()[0].upper()
        if upper in {"SET", "SETNX", "DEL", "EXPIRE", "PERSIST", "MSET", "FLUSHDB", "APPEND", "INCR", "DECR", "INCRBY", "DECRBY"}:
            self.refresh_dashboard()
        if upper in {"GET", "TYPE", "TTL", "EXISTS", "STRLEN"}:
            self.inspect_key()
        if upper in {"KEYS", "SCAN"}:
            parsed = self._try_parse_python_value(response)
            if isinstance(parsed, list):
                if upper == "KEYS":
                    self._populate_key_list(parsed)
                elif upper == "SCAN" and len(parsed) == 2 and isinstance(parsed[1], list):
                    self._populate_key_list(parsed[1])

    def refresh_dashboard(self):
        try:
            ping = self.send_command("PING", log_request=False)
            dbsize = self.send_command("DBSIZE", log_request=False)
            info = self.send_command("INFO", log_request=False)
            self.last_ping_var.set(ping or "n/a")
            self.dbsize_var.set(dbsize or "-")

            info_map = {}
            for line in info.splitlines():
                if ":" in line and not line.startswith("#"):
                    key, value = line.split(":", 1)
                    info_map[key] = value

            self.key_count_var.set(f"{info_map.get('keys', '-') } keys loaded")
            self.expires_var.set(info_map.get("expires", "-"))
            self._set_connection_state(True)
        except Exception as exc:
            self._set_connection_state(False)
            self.log(f"[dashboard] refresh failed: {exc}")

    def load_keys(self):
        try:
            response = self.send_command("KEYS *")
            parsed = self._try_parse_python_value(response)
            if not isinstance(parsed, list):
                raise ValueError("KEYS response was not a list.")
            self._populate_key_list(parsed)
            self._set_connection_state(True)
        except Exception as exc:
            self._set_connection_state(False)
            self.log(f"[keys] failed: {exc}")
            messagebox.showerror("Load keys failed", str(exc))

    def _populate_key_list(self, keys):
        self.current_keys = list(keys)
        self.key_listbox.delete(0, "end")
        for key in self.current_keys:
            self.key_listbox.insert("end", key)
        self.key_count_var.set(f"{len(self.current_keys)} keys loaded")

    def on_key_selected(self, _event):
        selection = self.key_listbox.curselection()
        if not selection:
            return
        key = self.key_listbox.get(selection[0])
        self.key_var.set(key)
        self.inspect_key()

    def inspect_key(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showinfo("Value Inspector", "Enter or select a key first.")
            return

        try:
            exists = self.send_command(f"EXISTS {key}", log_request=False)
            key_type = self.send_command(f"TYPE {key}", log_request=False)
            ttl = self.send_command(f"TTL {key}", log_request=False)
            value = self.send_command(f"GET {key}", log_request=False)
            strlen = self.send_command(f"STRLEN {key}", log_request=False)

            self.inspector_exists_var.set(exists)
            self.inspector_type_var.set(key_type)
            self.inspector_ttl_var.set(ttl)
            self.inspector_length_var.set(strlen)
            self._set_value_text(value)
            self._set_connection_state(True)
            self.log(f"[inspect] {key}")
        except Exception as exc:
            self._set_connection_state(False)
            self.log(f"[inspect] failed: {exc}")
            messagebox.showerror("Inspect failed", str(exc))

    def _set_value_text(self, value):
        self.value_text.configure(state="normal")
        self.value_text.delete("1.0", "end")
        self.value_text.insert("1.0", value)
        self.value_text.configure(state="disabled")

    def run_key_command(self, template, refresh=False):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showinfo("Value Inspector", "Select a key first.")
            return

        command = template.format(key=key)
        if command.startswith("DEL "):
            confirmed = messagebox.askyesno("Delete key", f"Delete '{key}'?")
            if not confirmed:
                return

        self.command_var.set(command)
        self.execute_command()
        if refresh:
            self.load_keys()

    def use_quick_command(self, _event):
        selection = self.quick_list.curselection()
        if not selection:
            return
        command = self.quick_list.get(selection[0])
        self.command_var.set(command)
        self.execute_command()

    def _try_parse_python_value(self, raw_text):
        try:
            return ast.literal_eval(raw_text)
        except Exception:
            return raw_text


def main():
    root = tk.Tk()
    app = RedisGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
