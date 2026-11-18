"""Приём файлов по TCP, с проверкой SHA-256 и безопасной заменой."""
import argparse
import hashlib
import os
import socket
import tempfile
from pathlib import Path

from protocol import CHUNK_SIZE, MAX_FILE_SIZE, recv_message, send_message


def safe_filename(name: object) -> str:
    if not isinstance(name, str) or not name or name in (".", ".."):
        raise ValueError("Некорректное имя файла")
    # Только имя файла, без путей (в том числе Windows-формата).
    if "/" in name or "\\" in name or "\x00" in name or ":" in name:
        raise ValueError("Пути и специальные символы в имени запрещены")
    return name


def handle_client(connection: socket.socket, output_dir: Path) -> None:
    temp_path = None
    try:
        connection.settimeout(30)
        request = recv_message(connection)
        name = safe_filename(request.get("name"))
        size = request.get("size")
        expected_hash = request.get("sha256")
        if type(size) is not int or size < 0 or size > MAX_FILE_SIZE:
            raise ValueError("Некорректный размер файла")
        if not (isinstance(expected_hash, str) and len(expected_hash) == 64
                and all(ch in "0123456789abcdef" for ch in expected_hash)):
            raise ValueError("Некорректный SHA-256")

        output_dir.mkdir(parents=True, exist_ok=True)
        # Пишем во временный файл: при обрыве конечный файл не изменяется.
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".incoming_", suffix=".part",
                                         dir=output_dir, delete=False) as tmp:
            temp_path = Path(tmp.name)
            digest = hashlib.sha256()
            received = 0
            while received < size:
                block = connection.recv(min(CHUNK_SIZE, size - received))
                if not block:
                    raise ConnectionError(f"Обрыв: получено {received} из {size} байт")
                tmp.write(block)
                digest.update(block)
                received += len(block)
            tmp.flush()
            os.fsync(tmp.fileno())

        actual_hash = digest.hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("Хеш SHA-256 не совпал: полученный файл повреждён")
        final_path = output_dir / name
        os.replace(temp_path, final_path)  # атомарная замена в пределах одного диска
        temp_path = None
        send_message(connection, {"ok": True, "name": name, "bytes": received, "sha256": actual_hash})
        print(f"[OK] {name}: {received} байт, SHA-256 {actual_hash}", flush=True)
    except (OSError, ValueError, ConnectionError, UnicodeError) as exc:
        print(f"[ОШИБКА] {exc}", flush=True)
        try:
            send_message(connection, {"ok": False, "error": str(exc)})
        except OSError:
            pass
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def serve(host: str, port: int, output_dir: Path, stop_event=None) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(5)
        server.settimeout(0.5)
        print(f"Сервер запущен: {host}:{server.getsockname()[1]} -> {output_dir.resolve()}", flush=True)
        try:
            while stop_event is None or not stop_event.is_set():
                try:
                    connection, address = server.accept()
                except socket.timeout:
                    continue
                print(f"Подключение: {address[0]}:{address[1]}", flush=True)
                with connection:
                    handle_client(connection, output_dir)
        except KeyboardInterrupt:
            print("\nСервер остановлен.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP-сервер для файлов (Python 3.9+)")
    parser.add_argument("--host", default="127.0.0.1", help="127.0.0.1 локально, 0.0.0.0 для локальной сети")
    parser.add_argument("--port", type=int, default=9007)
    parser.add_argument("--out", type=Path, default=Path("received"))
    args = parser.parse_args()
    serve(args.host, args.port, args.out)


if __name__ == "__main__":
    main()
