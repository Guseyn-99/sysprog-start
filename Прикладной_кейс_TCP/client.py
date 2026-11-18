"""Отправка файла по TCP по частям (не загружая целиком в память)."""
import argparse
import socket
import sys
import time
from pathlib import Path

from protocol import CHUNK_SIZE, file_sha256, recv_message, send_message


def send_file(path: Path, host: str, port: int, abort_after: int | None = None,
              chunk_delay: float = 0.0) -> bool:
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")
    size = path.stat().st_size
    digest = file_sha256(path)
    print(f"Отправка {path.name}, {size} байт, SHA-256: {digest}")
    with socket.create_connection((host, port), timeout=15) as connection:
        connection.settimeout(35)
        send_message(connection, {"name": path.name, "size": size, "sha256": digest})
        sent = 0
        if abort_after == 0:
            print("[ТЕСТ] Соединение прервано до передачи данных")
            return False
        with path.open("rb") as stream:
            while True:
                block = stream.read(CHUNK_SIZE)
                if not block:
                    break
                if abort_after is not None:
                    block = block[:max(0, abort_after - sent)]
                if not block:
                    break
                connection.sendall(block)
                sent += len(block)
                if chunk_delay:
                    time.sleep(chunk_delay)
                if abort_after is not None and sent >= abort_after:
                    print(f"[ТЕСТ] Соединение прервано после {sent} из {size} байт")
                    return False
        response = recv_message(connection)
        if not response.get("ok"):
            raise RuntimeError(f"Сервер отклонил файл: {response.get('error')}")
        if response.get("sha256") != digest or response.get("bytes") != size:
            raise RuntimeError("Неверное подтверждение от сервера")
        print(f"[OK] Файл принят целиком: {sent} байт. Хеш совпадает.")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP-клиент для передачи файла")
    parser.add_argument("file", type=Path, help="путь к отправляемому файлу")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9007)
    parser.add_argument("--abort-after", type=int, help="тест: оборвать передачу после N байт")
    parser.add_argument("--chunk-delay", type=float, default=0.0, help="тест: задержка между блоками, секунды")
    args = parser.parse_args()
    if args.abort_after is not None and args.abort_after < 0:
        parser.error("--abort-after не может быть отрицательным")
    if args.chunk_delay < 0:
        parser.error("--chunk-delay не может быть отрицательным")
    try:
        success = send_file(args.file, args.host, args.port, args.abort_after, args.chunk_delay)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[ОШИБКА] {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if success else 2)


if __name__ == "__main__":
    main()
