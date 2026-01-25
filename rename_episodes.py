#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


def rename_episodes(directory: Path, dry_run: bool = False):
    print()
    print(f"--- Processing {directory} ---")
    print()

    for file in sorted(directory.iterdir()):
        if file.is_file():
            rename_episode(file, dry_run)


def rename_episode(filepath: Path, dry_run: bool = False):
    new_name = normalize(filepath.name)
    if new_name:
        print(f"{filepath.name} -> {new_name}")
        new_filepath = filepath.parent / new_name
        if not dry_run:
            filepath.rename(new_filepath)
    else:
        print(f"Skipping {filepath.name}")

EPISODE_GROUP_RE = re.compile(r"[Ee](?P<episode>\d+)")
EPISODE_NAME_RE = re.compile(rf"^(?P<name>.*)([Ss](?P<season>\d+))(?P<episodes>({EPISODE_GROUP_RE.pattern})+).*?(?P<resolution>\d+([p\u0440i])).*?\.(?P<extension>mkv|mp4|wmv|avi)$")


def normalize(filename: str) -> Optional[str]:
    match = EPISODE_NAME_RE.match(filename)
    if not match:
        return None

    show_name = match.group("name").strip(". ").replace(" ", ".")

    season_number = match.group("season")
    if len(season_number) == 1:
        season_number = "0" + season_number

    episodes_group = match.group("episodes")
    episode_numbers = ""
    for m in EPISODE_GROUP_RE.finditer(episodes_group):
        episode_number = m.group("episode")
        if len(episode_number) == 1:
            episode_number = "0" + episode_number
        episode_numbers += f"E{episode_number}"

    resolution = match.group("resolution")
    if not resolution:
        resolution = input("Provide episode resolution")
        if not resolution.endswith("p"):
            resolution = resolution + "p"
    else:
        # replace russian `р` with english `p`
        resolution = resolution.replace('\u0440', 'p')

    extension = match.group("extension")

    return f"{show_name}.S{season_number}{episode_numbers}.{resolution}.{extension}"


def main():
    parser = argparse.ArgumentParser(description="Script to properly name episodes")
    parser.add_argument("path", help="Path to directory")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show expected changes without renaming")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"{path} doesn't exist", file=sys.stderr)
        exit(1)

    if path.is_file():
        rename_episode(path, args.dry_run)
    else:
        rename_episodes(path, args.dry_run)


if __name__ == '__main__':
    main()
