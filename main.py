import socket
from hashlib import sha1
from base64 import b64encode

HOST = "127.0.0.1"
PORT = 65432

CONN_UPGRADE = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
connections = set()
client_data = {}


def init_connection(data):
    raw_headers = list(
        map(
            lambda x: list(map(lambda y: y.strip(), x.split(":"))),
            data.decode().split("\r\n"),
        )
    )
    headers = {x[0].lower(): x[1] for x in raw_headers[1:-2]}
    websocket_key = headers.get("sec-websocket-key")
    if (
        not websocket_key
        or headers.get("upgrade").lower() != "websocket"
        or headers.get("connection").lower() != "upgrade"
    ):
        conn.send(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        return False
    websocket_accept = websocket_key.encode() + CONN_UPGRADE
    websocket_accept_sha1 = sha1()
    websocket_accept_sha1.update(websocket_accept)
    websocket_accept_b64 = b64encode(websocket_accept_sha1.digest()).strip()
    conn.send(
        f"HTTP/1.1 101 Switching Protocols\r\nUpgrade:Websocket\r\nConnection:Upgrade\r\nSec-WebSocket-Accept:{websocket_accept_b64.decode()}\r\n\r\n".encode()
    )
    connections.add(websocket_key)
    return True


def read_frames(data):
    frames = list(
        map(
            lambda frame: ("0" * (8 - len(frame[2:]))) + frame[2:],
            [bin(x) for x in data],
        )
    )
    init_byte = frames[0]
    content_length_byte = frames[1]
    print(f"Init Byte: {init_byte}")
    print(f"Mask and Content Length Byte: {content_length_byte}")
    if init_byte[0] != "1":
        print("This is not the end of data, more data will be received")
    opcode = init_byte[4:]
    masked = True
    if int(opcode, base=2) == 1:
        print("This data is of text type")
    if int(content_length_byte, base=2) < 128:
        print("This data is not masked")
        masked = False
    content_length = int(content_length_byte, base=2)
    content_length_index = 1
    if content_length > 128:
        content_length -= 128
    elif content_length >= 126:
        content_length = int(frames[2], base=2) + int(frames[3], base=2)
        content_length_index += 2
        if content_length == 127:
            content_length += int(frames[3], base=2) + int(frames[4], base=2)
            content_length_index += 2
    print(f"Content Length: {content_length}")
    masking_key = []
    if masked:
        for i in range(4):
            masking_key.append(int(frames[content_length_index + i + 1], base=2))
        print(f"Masking Key: {masking_key}")
    payload = []
    payload_index = content_length + 4
    print(frames[payload_index:])
    for i in range(content_length):
        print(int(frames[payload_index + i + 1], base=2))
        print(int(frames[payload_index + i + 1], base=2) ^ (i % len(masking_key)))


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            try:
                print(data.decode())
                success = init_connection(data)
                if not success:
                    break
            except:
                # data is a frame if it cannot be utf-8 decoded
                read_frames(data)
