import socket
# 1. 서버에 연결
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 6379))
# 2. PING 날려보기
client.sendall(b"PING\n")
print(client.recv(4096).decode("utf-8"))
# 3. RESP Raw 바이트 직접 전송 (*3\r\n...)
client.sendall(b"*3\r\n$3\r\nSET\r\n$8\r\nresp_key\r\n$10\r\nresp_value\r\n")
print(client.recv(4096).decode("utf-8"))  # 기대 응답: +OK
# 4. 일반 GET 전송
client.sendall(b"GET resp_key\n")
print(client.recv(4096).decode("utf-8"))