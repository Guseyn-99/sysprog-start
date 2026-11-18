"""Общий простой протокол: 4 байта длины JSON, JSON, затем байты файла."""
import hashlib
import json
import socket
import struct
from pathlib import Path

CHUNK_SIZE = 64 * 1024
MAX_HEADER = 16 * 1024
MAX_FILE_SIZE = 20 * 1024**3  # лимит для учебного проекта — 20 ГиБ


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """TCP — поток: recv() может вернуть меньше запрошенного."""
    parts = bytearray()
    while len(parts) < size:
        block = sock.recv(min(CHUNK_SIZE, size - len(parts)))
        if not block:
            raise ConnectionError(f"Соединение закрыто: получено {len(parts)} из {size} байт")
        parts.extend(block)
    return bytes(parts)


def send_message(sock: socket.socket, message: dict) -> None:
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_HEADER:
        raise ValueError("Слишком длинный заголовок")
    sock.sendall(struct.pack("!I", len(data)) + data)


def recv_message(sock: socket.socket) -> dict:
    length = struct.unpack("!I", recv_exact(sock, 4))[0]
    if not 0 < length <= MAX_HEADER:
        raise ValueError("Недопустимый размер заголовка")
    result = json.loads(recv_exact(sock, length).decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Заголовок должен быть JSON-объектом")
    return result


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()
