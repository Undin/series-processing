#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


def rename_episodes(directory: Path):
    for file in sorted(directory.iterdir()):
        if file.is_file():
            rename_episode(file)


def rename_episode(filepath: Path):
    new_name = normalize(filepath.name)
    if new_name:
        new_filepath = filepath.parent / new_name
        filepath.rename(new_filepath)


EPISODE_NAME_RE = re.compile(r"^(?P<name>.*)([Ss](?P<season>\d+))([Ee]?(?P<episode>\d+)).*?(?P<resolution>\d+([pi])).*?\.(?P<extension>mkv|mp4|wmv|avi)$")

def normalize(filename: str) -> Optional[str]:
    match = EPISODE_NAME_RE.match(filename)
    if not match:
        return None

    show_name = match.group("name").strip(". ").replace(" ", ".")

    season_number = match.group("season")
    if len(season_number) == 1:
        season_number = "0" + season_number

    episode_number = match.group("episode")
    if len(episode_number) == 1:
        episode_number = "0" + episode_number

    resolution = match.group("resolution")
    if not resolution:
        resolution = input("Provide episode resolution")
        if not resolution.endswith("p"):
            resolution = resolution + "p"

    extension = match.group("extension")

    return f"{show_name}.S{season_number}E{episode_number}.{resolution}.{extension}"


def main():
    parser = argparse.ArgumentParser(description="Script to properly name episodes")
    parser.add_argument("path", help="Path to directory")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"{path} doesn't exist", file=sys.stderr)
        exit(1)

    if path.is_file():
        rename_episode(path)
    else:
        rename_episodes(path)


if __name__ == '__main__':
    main()
