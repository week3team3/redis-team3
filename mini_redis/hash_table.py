from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class _Node:
    key: str
    value: Any


class HashTable:
    """A tiny hash table with separate chaining.

    The implementation is intentionally small so the core mechanics stay easy
    to explain during a demo.
    """

    def __init__(self, capacity: int = 16) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._buckets: list[list[_Node]] = [[] for _ in range(capacity)]
        self._size = 0

    def _hash(self, key: str) -> int:
        value = 5381
        for char in key:
            value = ((value << 5) + value) + ord(char)
        return value % len(self._buckets)

    def set(self, key: str, value: Any) -> None:
        bucket = self._buckets[self._hash(key)]
        for node in bucket:
            if node.key == key:
                node.value = value
                return
        bucket.append(_Node(key=key, value=value))
        self._size += 1

    def get(self, key: str) -> Any | None:
        bucket = self._buckets[self._hash(key)]
        for node in bucket:
            if node.key == key:
                return node.value
        return None

    def contains(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> bool:
        bucket = self._buckets[self._hash(key)]
        for index, node in enumerate(bucket):
            if node.key == key:
                del bucket[index]
                self._size -= 1
                return True
        return False

    def items(self) -> list[tuple[str, Any]]:
        pairs: list[tuple[str, Any]] = []
        for bucket in self._buckets:
            for node in bucket:
                pairs.append((node.key, node.value))
        return pairs

    def __len__(self) -> int:
        return self._size
