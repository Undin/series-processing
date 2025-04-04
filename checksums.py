#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path

COMMANDS = ["generate", "verify"]


def main():
    parser = argparse.ArgumentParser(description="Script to recursively generate/verify checksums")
    parser.add_argument("command", help="Command name. `generate` and `verify` are supported")
    parser.add_argument("path", help="Path to directory")

    args = parser.parse_args()

    if args.command not in COMMANDS:
        print(f"Unsupported command: {args.command}", file=sys.stderr)
        parser.print_help()
        exit(1)

    root_path = Path(args.path)

    if not root_path.exists():
        print(f"{root_path} doesn't exist", file=sys.stderr)
        exit(1)

    if args.command == "generate":
        generate_checksums(root_path)
    elif args.command == "verify":
        verify_checksums(root_path)


KNOWN_EXTENSIONS = [".mkv", ".mp4", ".wmv", ".avi"]


def generate_checksums(dir: Path):
    for file in sorted(dir.iterdir()):
        if file.is_file() and file.suffix in KNOWN_EXTENSIONS:
            print(f"Generating checksum for {file}")
            result = subprocess.run(["md5sum", file.name], cwd=dir, capture_output=True, text=True, check=True)
            checksum_file = dir / f".{file.name}.md5"
            with open(checksum_file, "w") as f:
                f.write(result.stdout)

    for child_file in sorted(dir.iterdir()):
        if child_file.is_dir():
            generate_checksums(child_file)


def verify_checksums(dir: Path):
    for file in sorted(dir.iterdir()):
        if file.is_file() and file.suffix in KNOWN_EXTENSIONS:
            checksum_file = dir / f".{file.name}.md5"
            if not checksum_file.exists():
                print(f"Checksum file doesn't exists for {file}")
            else:
                subprocess.run(["md5sum", "--check", checksum_file.name], cwd=dir)

    for child_file in sorted(dir.iterdir()):
        if child_file.is_dir():
            verify_checksums(child_file)


if __name__ == '__main__':
    main()
