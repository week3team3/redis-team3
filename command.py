# 이곳은 redis 명령어를 작성하는 곳 입니다
def handle_command(line, store):
    parts = line.split(' ')
    print(f"받은 명령어 => {parts}")

    if not parts:
        return 'ERROR'
    
    cmd = parts[0].upper()

    if cmd =='SET' and len(parts) >= 3:
        key = parts[1]
        value = parts[2]
        return store.set(key, value)
    elif cmd == 'GET' and len(parts) >= 2:
        key = parts[1]
        return store.get(key)
    elif cmd == 'DEL' and len(parts) >= 2:
        key = parts[1]
        removed_value = store.delete(key)
        if removed_value is not None: return 1
        else: return 0
    elif cmd == 'INCR' and len(parts) >= 2:
        key = parts[1]
        return store.increment(key)
    else:
        return 'ERROR'

