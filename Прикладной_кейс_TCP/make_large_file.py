"""Генерация большого тестового файла потоковой записью (без огромного расхода RAM)."""
import argparse
import hashlib
from pathlib import Path

BLOCK = bytes(range(256)) * 4096  # 1 МиБ шаблона


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size-mib", type=int, default=200)
    args = parser.parse_args()
    if not 1 <= args.size_mib <= 2048:
        parser.error("Размер от 1 до 2048 МиБ")
    folder = Path("extra_payloads")
    folder.mkdir(exist_ok=True)
    target = folder / f"large_{args.size_mib}mb.bin"
    with target.open("wb") as output:
        for _ in range(args.size_mib):
            output.write(BLOCK)
    print(f"Создан тестовый файл: {target}, {target.stat().st_size} байт")


if __name__ == "__main__":
    main()
