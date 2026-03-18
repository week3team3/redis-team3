import socket
import threading
from command import handle_command
from store import Store

host = "0.0.0.0"
port = 6379

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen(5)

redis = Store()

print(f"server is listening on {host}:{port}")


def handle_client(client_socket, client_address):
    print(f"client connected: {client_address}")
    buffer = ""

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                if line.lower() == "exit":
                    client_socket.send(b"bye!\r\n")
                    return

                print(f"received: {line}")
                redis_response = handle_command(line, redis)
                client_socket.send((str(redis_response) + "\n").encode("utf-8"))
                print(f"response: {redis_response}")

    except Exception as exc:
        print(f"error: {exc}")
    finally:
        print("connection closed")
        client_socket.close()


while True:
    client_socket, client_address = server_socket.accept()
    threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
