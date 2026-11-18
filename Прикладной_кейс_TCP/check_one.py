"""Проверка SHA-256 двух файлов."""
import argparse
from pathlib import Path
from protocol import file_sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("received", type=Path)
    args = parser.parse_args()
    if not args.source.is_file() or not args.received.is_file():
        parser.error("Оба файла должны существовать")
    left = file_sha256(args.source)
    right = file_sha256(args.received)
    print(f"Исходный:   {left}")
    print(f"Полученный: {right}")
    print("OK: совпадают" if left == right else "FAIL: файлы отличаются")
    raise SystemExit(0 if left == right else 1)


if __name__ == "__main__":
    main()
