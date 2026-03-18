import socket
import threading
from command import handle_command
from store import Store

# 서버 설정
host = '0.0.0.0'
port = 6379

# 서버 소캣을 생성합니다
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen(5)

# 전역으로 저장소 객체 생성
redis = Store()

print(f"서버가 {host}:{port}에서 대기 중입니다...")


def handle_client(client_socket, client_address):
    print(f"클라이언트 {client_address}가 연결되었습니다.")
    buffer = ""
    
    try:
        while True:
            data = client_socket.recv(1024)
            
            # 클라이언트가 연결을 끊으면 서버도 끊습니다
            if not data:
                break

            # 글자를 한 자씩 받음       
            buffer += data.decode("utf-8")
            # Enter 입력 전 까지 계속 누적됨
            if '\n' not in buffer:
                continue

            line, buffer = buffer.split('\n', 1)
            line = line.strip()
        
            # 연결이 종료되는 로직
            if line.lower() == "exit":
                response = "bye!"
                client_socket.send((response + "\r\n").encode("utf-8"))
                break

            # 다음 문구는 서버 콘솔에서 출력됩니다
            print(f"다음 메시지가 발송되었습니다: {line}")

            redis_response = handle_command(line, redis)
            client_socket.send((str(redis_response) + "\n").encode("utf-8"))
            print(f"다음을 반환합니다: {redis_response}")
        
    except Exception as e:
        print(f"오류가 발생하였습니다: {e}")
    finally:
        print("연결 종료")
        client_socket.close()

while True:
    client_socket, client_address = server_socket.accept()
    # 다중 클라이언트가 동시에 연결되도록 처리합니다
    threading.Thread(
        target=handle_client,
        args=(client_socket, client_address)
    ).start()




