from __future__ import annotations

import unittest

from mini_redis.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_set_get_and_delete(self) -> None:
        table = HashTable(capacity=2)

        table.set("apple", "red")
        table.set("banana", "yellow")

        self.assertEqual(table.get("apple"), "red")
        self.assertEqual(table.get("banana"), "yellow")
        self.assertTrue(table.delete("apple"))
        self.assertIsNone(table.get("apple"))
        self.assertFalse(table.delete("missing"))

    def test_overwrite_existing_key(self) -> None:
        table = HashTable()

        table.set("key", "v1")
        table.set("key", "v2")

        self.assertEqual(table.get("key"), "v2")
        self.assertEqual(len(table), 1)


if __name__ == "__main__":
    unittest.main()
