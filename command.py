def error(message="ERROR"):
    return f"ERROR {message}"


def handle_command(line, store):
    stripped = line.strip()
    if not stripped:
        return error()

    head, sep, tail = stripped.partition(" ")
    cmd = head.upper()
    args = tail.split() if sep else []

    print(f"command => {cmd}, args => {args}")

    try:
        if cmd == "PING":
            return tail if sep else "PONG"

        if cmd == "ECHO":
            return tail if sep else ""

        if cmd == "SET":
            if not sep:
                return error("wrong number of arguments for SET")
            key, value_sep, value = tail.partition(" ")
            if not value_sep:
                return error("wrong number of arguments for SET")
            return store.set(key, value)

        if cmd == "SETNX":
            if not sep:
                return error("wrong number of arguments for SETNX")
            key, value_sep, value = tail.partition(" ")
            if not value_sep:
                return error("wrong number of arguments for SETNX")
            return store.setnx(key, value)

        if cmd == "GET":
            if len(args) != 1:
                return error("wrong number of arguments for GET")
            return store.get(args[0])

        if cmd == "GETSET":
            if not sep:
                return error("wrong number of arguments for GETSET")
            key, value_sep, value = tail.partition(" ")
            if not value_sep:
                return error("wrong number of arguments for GETSET")
            return store.getset(key, value)

        if cmd == "DEL":
            if not args:
                return error("wrong number of arguments for DEL")
            return store.delete(*args)

        if cmd == "EXISTS":
            if len(args) != 1:
                return error("wrong number of arguments for EXISTS")
            return store.exists(args[0])

        if cmd == "TYPE":
            if len(args) != 1:
                return error("wrong number of arguments for TYPE")
            return store.type_of(args[0])

        if cmd == "INCR":
            if len(args) != 1:
                return error("wrong number of arguments for INCR")
            return store.increment(args[0])

        if cmd == "DECR":
            if len(args) != 1:
                return error("wrong number of arguments for DECR")
            return store.decrement(args[0])

        if cmd == "INCRBY":
            if len(args) != 2:
                return error("wrong number of arguments for INCRBY")
            return store.increment_by(args[0], args[1])

        if cmd == "DECRBY":
            if len(args) != 2:
                return error("wrong number of arguments for DECRBY")
            return store.decrement_by(args[0], args[1])

        if cmd == "MGET":
            if not args:
                return error("wrong number of arguments for MGET")
            return store.mget(*args)

        if cmd == "MSET":
            if len(args) < 2 or len(args) % 2 != 0:
                return error("wrong number of arguments for MSET")
            return store.mset(*args)

        if cmd == "EXPIRE":
            if len(args) != 2:
                return error("wrong number of arguments for EXPIRE")
            return store.expire(args[0], args[1])

        if cmd == "TTL":
            if len(args) != 1:
                return error("wrong number of arguments for TTL")
            return store.ttl(args[0])

        if cmd == "PERSIST":
            if len(args) != 1:
                return error("wrong number of arguments for PERSIST")
            return store.persist(args[0])

        if cmd == "APPEND":
            if not sep:
                return error("wrong number of arguments for APPEND")
            key, value_sep, value = tail.partition(" ")
            if not value_sep:
                return error("wrong number of arguments for APPEND")
            return store.append(key, value)

        if cmd == "STRLEN":
            if len(args) != 1:
                return error("wrong number of arguments for STRLEN")
            return store.strlen(args[0])

        if cmd == "FLUSHDB":
            if args:
                return error("wrong number of arguments for FLUSHDB")
            return store.flushdb()

        if cmd == "KEYS":
            if len(args) != 1:
                return error("wrong number of arguments for KEYS")
            return store.keys(args[0])

        if cmd == "SCAN":
            if len(args) != 1:
                return error("wrong number of arguments for SCAN")
            return store.scan(args[0])

        if cmd == "DBSIZE":
            if args:
                return error("wrong number of arguments for DBSIZE")
            return store.dbsize()

        if cmd == "INFO":
            if args:
                return error("wrong number of arguments for INFO")
            return store.info()

        return error("unknown command")
    except ValueError as exc:
        return error(str(exc))
