from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AOFPersistence:
    """Very small append-only log that stores entry snapshots as JSON lines."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path) if path else None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self.path is not None

    def append_upsert(self, key: str, entry: dict[str, Any]) -> None:
        if not self.enabled:
            return
        self._append_line({"op": "upsert", "key": key, "entry": entry})

    def append_delete(self, key: str) -> None:
        if not self.enabled:
            return
        self._append_line({"op": "delete", "key": key})

    def load_operations(self) -> list[dict[str, Any]]:
        if not self.enabled or not self.path.exists():
            return []
        operations: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                operations.append(json.loads(line))
        return operations

    def _append_line(self, payload: dict[str, Any]) -> None:
        assert self.path is not None
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True))
            handle.write("\n")
