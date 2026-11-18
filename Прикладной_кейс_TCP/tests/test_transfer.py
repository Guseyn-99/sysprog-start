"""Интеграционные тесты: настоящий TCP по 127.0.0.1."""
import hashlib
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from client import send_file
from protocol import recv_message, send_message
from server import serve


class TcpTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.src = cls.root / "source"
        cls.dst = cls.root / "received"
        cls.src.mkdir()
        cls.dst.mkdir()
        # Запрашиваем свободный тестовый порт до старта сервера.
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        cls.stop_event = threading.Event()
        cls.server_thread = threading.Thread(target=serve, args=("127.0.0.1", cls.port, cls.dst, cls.stop_event), daemon=True)
        cls.server_thread.start()
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.01)
        else:
            raise RuntimeError("Сервер не запустился")

    @classmethod
    def tearDownClass(cls):
        cls.stop_event.set()
        cls.server_thread.join(timeout=2)
        cls.temp.cleanup()

    def make_file(self, name, content):
        path = self.src / name
        path.write_bytes(content)
        return path

    def test_01_small_text(self):
        path = self.make_file("hello.txt", "Привет, TCP! 😀\n".encode())
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        self.assertEqual((self.dst / path.name).read_bytes(), path.read_bytes())

    def test_02_cyrillic_filename(self):
        path = self.make_file("заказ № 407.txt", "Накладная № 407".encode())
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        self.assertEqual((self.dst / path.name).read_bytes(), path.read_bytes())

    def test_03_binary_file(self):
        path = self.make_file("binary.bin", bytes(range(256)) * 2048)
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        self.assertEqual((self.dst / path.name).read_bytes(), path.read_bytes())

    def test_04_large_file(self):
        path = self.make_file("large.bin", b"0123456789ABCDEF" * (1024 * 1024))  # 16 MiB
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        self.assertEqual((self.dst / path.name).read_bytes(), path.read_bytes())

    def test_05_interrupted_transfer_preserves_existing(self):
        path = self.make_file("unchanged.bin", b"z" * (1024 * 1024))
        destination = self.dst / path.name
        destination.write_bytes(b"previous good copy")
        self.assertFalse(send_file(path, "127.0.0.1", self.port, abort_after=100_000))
        # Ждём, пока сервер распознает обрыв и удалит временный файл.
        for _ in range(100):
            if not list(self.dst.glob(".incoming_*.part")):
                break
            time.sleep(0.02)
        self.assertEqual(destination.read_bytes(), b"previous good copy")
        self.assertFalse(list(self.dst.glob(".incoming_*.part")))

    def test_06_repeat_replaces_file(self):
        path = self.make_file("repeat.txt", b"first version")
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        path.write_bytes(b"second version -- changed contents")
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        self.assertEqual((self.dst / path.name).read_bytes(), path.read_bytes())

    def test_07_empty_file(self):
        path = self.make_file("empty.txt", b"")
        self.assertTrue(send_file(path, "127.0.0.1", self.port))
        self.assertEqual((self.dst / path.name).read_bytes(), b"")

    def test_08_reject_path_traversal(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            send_message(sock, {"name": "../unsafe.txt", "size": 0, "sha256": hashlib.sha256(b"").hexdigest()})
            answer = recv_message(sock)
        self.assertFalse(answer["ok"])
        self.assertFalse((self.root / "unsafe.txt").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
