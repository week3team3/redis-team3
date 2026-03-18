# PyMiniRedis Specification

## 1. Document Purpose

This file is the source of truth for PyMiniRedis.
Every feature change must update this document together with implementation and tests.

Current version: `v1.4`
Status: `implemented`

## 2. Product Goal

PyMiniRedis is a simplified Redis-like TCP server implemented in Python.
It is intentionally small and explainable, and it uses a custom hash table as the primary data store.

The project goal is not full Redis compatibility.
The goal is to provide a Mini Redis that demonstrates:

- TCP/IP request handling
- custom protocol parsing
- in-memory key-value storage
- expiration and jitter
- invalidation
- atomic counters
- mutex-style coordination
- fixed-window rate limiting
- hash/set/zset data structures
- queue-friendly ranking operations
- stock decrement operations
- concurrency handling
- optional append-only persistence

## 3. Scope

Included in `v1.4`:

- TCP server using Python standard library
- line-based text protocol
- minimal RESP array request parsing
- RESP-formatted replies for RESP requests
- custom hash table with separate chaining
- thread-safe shared store
- lazy expiration
- background sweeper
- invalidation with grace-period cleanup
- mutex-style resource locking
- fixed-window rate limiting
- hash operations
- set operations
- sorted-set operations
- counter delta operations
- optional AOF persistence
- bundled interactive CLI client
- automated tests by feature
- traffic/load validation script

Excluded from `v1.4`:

- HTTP API
- Flask, FastAPI, or any web framework
- full Redis RESP protocol compatibility
- replication, clustering, pub/sub, transactions
- authentication and authorization
- snapshots, RDB format, Lua scripting

## 4. Runtime Model

- transport: TCP/IP
- encoding: UTF-8
- request unit: one line ending with `\n` or one RESP array request
- response unit: line reply for text requests or RESP reply for RESP requests
- server class: `socketserver.ThreadingTCPServer`
- concurrency model: multi-client TCP server with a single lock-protected store
- cleanup model: background sweeper thread plus lazy checks on access
- default data lifetime: memory only
- optional persistence: append-only log with state snapshots per mutation
- bundled operator tool: `python -m mini_redis.cli`

## 4.1 CLI Utility

PyMiniRedis includes a small CLI similar in role to `redis-cli`.

Supported modes:

- interactive prompt mode
- one-shot command mode

Examples:

```text
python -m mini_redis.cli --host 127.0.0.1 --port 6379
python -m mini_redis.cli --host 127.0.0.1 --port 6379 PING
```

## 5. Storage Model

Primary store:

- key type: string
- value type: typed value
- supported top-level data types: `string`, `hash`, `set`, `zset`
- collision strategy: separate chaining
- hash function: `djb2`-style string hash
- initial bucket count: `16`

The storage engine must not use Python `dict` as the primary key-value store.

Stored entry shape:

- `data_type: str`
- `value: Any`
- `expires_at: float | None`
- `invalidated: bool`
- `invalidation_reason: str | None`
- `invalidated_at: float | None`

Behavior rules:

- `SET` overwrites the existing entry and clears expiration/invalidation state
- expired keys behave as missing keys
- invalidated keys behave as missing keys
- expired and invalidated keys are eventually physically removed
- `DEL`, `EXISTS`, `EXPIRE`, and `TTL` operate on the top-level key across all supported data types
- wrong-type operations return `-ERR wrong type for operation`

Additional in-memory meta tables:

- lock table
- fixed-window rate-limit table

## 6. Protocol Rules

- PyMiniRedis accepts both inline text commands and minimal RESP array requests
- commands are space-delimited
- command names are case-insensitive
- empty lines are rejected
- keys do not contain spaces
- `SET`, `INVALIDATE`, and `HSET` allow trailing text payloads
- integer arguments must parse as base-10 integers
- integer replies use the `:N` format
- RESP request support is limited to arrays of bulk strings
- RESP compatibility is intentionally partial and only covers the implemented command set

Example:

```text
SET greeting hello world
```

Parsed as:

- command: `SET`
- key: `greeting`
- value: `hello world`

## 7. Command Specification

### 7.1 `PING`

Request:

```text
PING
```

Response:

```text
+PONG
```

### 7.2 `SET <key> <value> [NX]`

Stores or overwrites a string value.

Behavior:

- plain `SET` overwrites the current top-level key
- `SET ... NX` stores only when the key is currently missing
- expired or invalidated keys count as missing for `NX`

Responses:

- success: `+OK`
- skipped by `NX`: `$nil`

Errors:

```text
-ERR usage: SET <key> <value>
-ERR only NX modifier is supported
```

### 7.3 `GET <key>`

Reads a string value.

Existing key:

```text
$value
```

Missing, expired, or invalidated key:

```text
$nil
```

Usage error:

```text
-ERR usage: GET <key>
```

### 7.4 `DEL <key>`

Deletes a top-level key.

- deleted: `:1`
- not found: `:0`

Usage error:

```text
-ERR usage: DEL <key>
```

### 7.5 `EXISTS <key>`

Checks whether a visible top-level key exists.

- exists: `:1`
- missing, expired, or invalidated: `:0`

Usage error:

```text
-ERR usage: EXISTS <key>
```

### 7.6 `EXPIRE <key> <seconds>`

Assigns TTL to an existing visible top-level key.

- updated: `:1`
- key not found: `:0`

Errors:

```text
-ERR usage: EXPIRE <key> <seconds>
-ERR seconds must be an integer
-ERR seconds must be positive
```

### 7.7 `TTL <key>`

Returns remaining lifetime in seconds.

- no expiration: `:-1`
- missing, expired, or invalidated: `:-2`
- active TTL: `:N`

`N` is rounded up to the next whole second.

Usage error:

```text
-ERR usage: TTL <key>
```

### 7.8 `EXPIREJITTER <key> <seconds> <jitter_seconds>`

Assigns randomized TTL from `seconds` through `seconds + jitter_seconds`.

- updated: `:actual_ttl`
- key not found: `:0`

Errors:

```text
-ERR usage: EXPIREJITTER <key> <seconds> <jitter_seconds>
-ERR seconds and jitter_seconds must be integers
-ERR seconds must be positive
-ERR jitter_seconds must be non-negative
```

### 7.9 `INCR <key>`

Atomically increments a string integer value by `1`.

Behavior:

- missing key becomes `1`
- existing integer string is incremented
- non-integer value returns an error

Responses:

- success: `:N`
- error:

```text
-ERR value is not an integer
```

Usage error:

```text
-ERR usage: INCR <key>
```

### 7.10 `DECR <key>`

Atomically decrements a string integer value by `1`.

Behavior:

- missing key becomes `-1`
- existing integer string is decremented
- non-integer value returns an error

Responses:

- success: `:N`

Errors:

```text
-ERR usage: DECR <key>
-ERR value is not an integer
```

### 7.11 `INCRBY <key> <amount>`

Atomically increments a string integer value by the given amount.

Responses:

- success: `:N`

Errors:

```text
-ERR usage: INCRBY <key> <amount>
-ERR amount must be an integer
-ERR value is not an integer
```

### 7.12 `DECRBY <key> <amount>`

Atomically decrements a string integer value by the given amount.

Responses:

- success: `:N`

Errors:

```text
-ERR usage: DECRBY <key> <amount>
-ERR amount must be an integer
-ERR amount must be non-negative
-ERR value is not an integer
```

### 7.13 `INVALIDATE <key> [reason]`

Marks a top-level key as logically invalid.

Behavior:

- invalidated key becomes invisible to `GET`, `EXISTS`, and `TTL`
- key remains in memory until the sweeper removes it after the grace period
- invalidation reason is stored internally

Responses:

- updated: `:1`
- key not found: `:0`

Usage error:

```text
-ERR usage: INVALIDATE <key> [reason]
```

### 7.14 `LOCK <key> <owner> <ttl_seconds>`

Attempts to acquire a mutex-style lock for a resource key.

Behavior:

- missing or expired lock can be acquired
- same owner can reacquire and renew the lock TTL
- different owner is rejected while the lock is live

Responses:

- acquired or renewed: `:1`
- held by different owner: `:0`

Errors:

```text
-ERR usage: LOCK <key> <owner> <ttl_seconds>
-ERR ttl_seconds must be an integer
-ERR ttl_seconds must be positive
```

### 7.15 `UNLOCK <key> <owner>`

Releases a mutex-style lock if the owner matches.

Responses:

- released: `:1`
- missing, expired, or owner mismatch: `:0`

Usage error:

```text
-ERR usage: UNLOCK <key> <owner>
```

### 7.16 `RATECHECK <key> <limit> <window_seconds>`

Checks and updates a fixed-window rate limit counter.

Behavior:

- first request in a new window starts `count=1`
- requests up to `limit` are allowed
- requests above `limit` are blocked until the window resets
- blocked requests do not increase the counter further

Allowed response:

```text
+ALLOWED remaining=4 reset_in=10 count=1
```

Blocked response:

```text
+BLOCKED remaining=0 reset_in=7 count=5
```

Errors:

```text
-ERR usage: RATECHECK <key> <limit> <window_seconds>
-ERR limit and window_seconds must be integers
-ERR limit must be positive
-ERR window_seconds must be positive
```

### 7.17 `HSET <key> <field> <value>`

- new field: `:1`
- overwritten field: `:0`

Usage error:

```text
-ERR usage: HSET <key> <field> <value>
```

### 7.18 `HGET <key> <field>`

- existing field: `$value`
- missing field or key: `$nil`

Usage error:

```text
-ERR usage: HGET <key> <field>
```

### 7.19 `HDEL <key> <field>`

- deleted: `:1`
- not found: `:0`

Usage error:

```text
-ERR usage: HDEL <key> <field>
```

### 7.20 `HGETALL <key>`

- existing hash: `$<json-object>`
- missing key: `$nil`

Usage error:

```text
-ERR usage: HGETALL <key>
```

### 7.21 `SADD <key> <member>`

- new member: `:1`
- existing member: `:0`

Usage error:

```text
-ERR usage: SADD <key> <member>
```

### 7.22 `SISMEMBER <key> <member>`

- present: `:1`
- absent: `:0`

Usage error:

```text
-ERR usage: SISMEMBER <key> <member>
```

### 7.23 `SREM <key> <member>`

- deleted: `:1`
- not found: `:0`

Usage error:

```text
-ERR usage: SREM <key> <member>
```

### 7.24 `SMEMBERS <key>`

- existing set: `$<json-array>`
- missing key: `$nil`

Usage error:

```text
-ERR usage: SMEMBERS <key>
```

### 7.25 `ZADD <key> <score> <member>`

- new member: `:1`
- updated member: `:0`

Errors:

```text
-ERR usage: ZADD <key> <score> <member>
-ERR score must be a number
```

### 7.26 `ZRANK <key> <member>`

- rank found: `:N`
- missing member or key: `:-1`

Usage error:

```text
-ERR usage: ZRANK <key> <member>
```

### 7.27 `ZRANGE <key> <start> <stop>`

- existing key: `$<json-array>`
- missing key: `$nil`

Errors:

```text
-ERR usage: ZRANGE <key> <start> <stop>
-ERR start and stop must be integers
```

### 7.28 `ZREM <key> <member>`

- deleted: `:1`
- not found: `:0`

Usage error:

```text
-ERR usage: ZREM <key> <member>
```

### 7.29 `ZPOPMIN <key>`

- existing key: `$["member",score]`
- missing key: `$nil`

Usage error:

```text
-ERR usage: ZPOPMIN <key>
```

### 7.30 `ZCARD <key>`

- count: `:N`

Usage error:

```text
-ERR usage: ZCARD <key>
```

### 7.31 `QUIT`

Closes the current connection.

Response:

```text
+BYE
```

## 7.32 Minimal RESP Support

Supported request shape:

- RESP arrays of bulk strings
- example:

```text
*1\r\n$4\r\nPING\r\n
```

Supported response shapes:

- simple strings for `+OK`, `+PONG`, `+BYE`
- errors for `-ERR ...`
- integers for `:N`
- bulk strings for `$value`
- null bulk strings for missing values

Non-goals:

- full Redis RESP compatibility
- nested arrays
- mixed request element types
- binary-safe arbitrary payload coverage beyond UTF-8 command strings

## 8. Response Format

- `+...`: success markers
- `+ALLOWED ...`: allowed rate-limit response
- `+BLOCKED ...`: blocked rate-limit response
- `$...`: string value replies or compact JSON strings
- `$nil`: missing value
- `:...`: integer replies
- `-ERR ...`: usage or command errors

Collection-style replies use compact JSON strings inside `$...`.

## 9. Error Handling Rules

- unknown command:

```text
-ERR unknown command 'COMMAND'
```

- empty command:

```text
-ERR empty command
```

- wrong-type access:

```text
-ERR wrong type for operation
```

- argument count errors use the command-specific usage message
- integer parsing errors use the command-specific integer message

## 10. Expiration and Invalidation Rules

- expiration is enforced lazily on visible-key access
- sweeper periodically removes expired keys
- invalidated keys behave like missing immediately
- invalidated keys remain stored until `invalidated_at + invalidation_grace_seconds`
- sweeper removes invalidated keys after the grace period

## 11. Locking Rules

- lock state is stored in a separate in-memory table
- lock ownership is identified by the `owner` argument
- expired locks can be stolen by a new owner
- live locks can only be released by the same owner
- lock state is not persisted to AOF

## 12. Rate Limiting Rules

- rate limiting uses a fixed-window counter per key
- each key has its own `count` and `window_end`
- blocked requests leave the count unchanged at the limit
- expired windows are reset on the next request or by sweeper cleanup
- rate-limit state is not persisted to AOF

## 13. Persistence Rules

Persistence is optional and enabled only when `--aof-path` is provided.

Implementation policy:

- each top-level key mutation appends one JSON line to the AOF
- `SET`, `EXPIRE`, `EXPIREJITTER`, `INCR`, `INCRBY`, `DECRBY`, `INVALIDATE`, `HSET`, `HDEL`, `SADD`, `SREM`, `ZADD`, `ZREM`, and `ZPOPMIN` persist through the typed entry snapshot model
- `DEL` and cleanup purges persist as `delete`
- `LOCK`, `UNLOCK`, and `RATECHECK` are not persisted
- on startup the AOF is replayed
- expired entries are not restored
- invalidated entries are restored only if their grace period has not elapsed

This is a project-specific append-only log, not Redis AOF compatibility.

## 14. Concurrency Rules

- multiple clients may connect concurrently
- all store mutations and reads are protected by a shared `RLock`
- `INCR` and `INCRBY/DECRBY` behave atomically under concurrent requests
- lock acquisition and release behave atomically under concurrent requests
- fixed-window rate checks are consistent under concurrent requests
- thread safety is guaranteed only within one Python process
- multi-process coordination is out of scope

## 15. Verification Rules

Any feature is complete only when all three are updated together:

1. `SPEC.md`
2. implementation
3. feature-specific tests

Traffic validation must exist in two layers:

- deterministic automated concurrency tests
- manual repeatable load testing through `scripts/load_test.py`

## 16. Acceptance Criteria for v1.4

The implementation is valid only if all of the following are true:

- the server starts from the command line and listens on a TCP port
- all commands in section 7 behave as documented
- minimal RESP array parsing works for direct request verification
- RESP replies are emitted for RESP requests
- the backing store is the custom hash table implementation
- expired keys return missing semantics and are eventually purged
- invalidated keys return missing semantics and are eventually purged
- `INCR` is atomic under concurrent access
- `DECR` and `SET ... NX` behave as documented
- `LOCK` and `UNLOCK` follow owner-based mutex semantics
- `RATECHECK` enforces a fixed-window limit and reports remaining/reset metadata
- hash, set, and sorted-set commands behave as documented
- queue-oriented commands `ZRANK`, `ZRANGE`, and `ZPOPMIN` support waiting-room flows
- `DECRBY` supports ticket stock deduction
- optional AOF persistence restores live keys after restart
- bundled CLI can connect and execute commands without requiring manual PowerShell stream objects
- feature-specific automated tests pass
- load testing script reports totals, latency, and throughput without protocol corruption

## 17. Current Test Mapping

- `tests/test_hash_table.py`: hash table behavior
- `tests/test_protocol_basic.py`: `PING`, `SET`, `GET`, `DEL`, `EXISTS`, usage errors
- `tests/test_protocol_expiration.py`: `EXPIRE`, `TTL`, `EXPIREJITTER`
- `tests/test_protocol_counter.py`: `INCR`, `DECR`, `INCRBY`, `DECRBY`
- `tests/test_protocol_resp.py`: RESP parsing and RESP request/response flow
- `tests/test_protocol_setnx.py`: `SET ... NX`
- `tests/test_protocol_invalidation.py`: `INVALIDATE`, sweeper purge
- `tests/test_protocol_locking.py`: `LOCK`, `UNLOCK`
- `tests/test_protocol_rate_limit.py`: `RATECHECK`
- `tests/test_protocol_hash.py`: hash commands
- `tests/test_protocol_sets.py`: set commands
- `tests/test_protocol_sorted_set.py`: sorted-set commands
- `tests/test_store_expiration.py`: store-level expiration behavior
- `tests/test_concurrency.py`: concurrent `SET/GET` and atomic `INCR`
- `tests/test_persistence.py`: restart recovery with AOF
- `tests/test_cli.py`: CLI command dispatch
- `scripts/load_test.py`: manual traffic validation for `setget`, `incr`, `ratecheck`, `queue`
