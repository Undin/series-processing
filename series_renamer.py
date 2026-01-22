#!/usr/bin/env python3
"""
Core module for renaming TV series files to a standardized format.

Provides a reusable SeriesRenamer class that can be configured for different shows.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class EpisodeInfo:
    """Information extracted from an episode filename."""
    season: int
    episodes: list[int]
    resolution: Optional[str] = None


@dataclass
class EpisodePattern:
    """
    Pattern for matching episode information in filenames.

    Attributes:
        pattern: Compiled regex pattern to match against filenames
        season_group: Group index/name for season number, or None to use season from directory
        episodes_group: Group index/name for episode(s) - can be "E01E02" format or single number
        resolution_group: Group index/name for resolution, or None if not in pattern
    """
    pattern: re.Pattern
    season_group: Optional[int | str] = 1
    episodes_group: int | str = 2
    resolution_group: Optional[int | str] = None


@dataclass
class SeriesConfig:
    """
    Configuration for a TV series renaming operation.

    Attributes:
        base_dir: Root directory containing season subdirectories
        show_name: Show name for filenames (e.g., "House.M.D")
        show_name_spaced: Show name for directories (e.g., "House M.D.")
        season_dir_patterns: Patterns to extract season number from directory names
        episode_patterns: Patterns to extract episode info from filenames
        resolution_extractor: Optional callback to extract resolution from filename
    """
    base_dir: Path
    show_name: str
    show_name_spaced: str
    season_dir_patterns: list[re.Pattern]
    episode_patterns: list[EpisodePattern]
    resolution_extractor: Optional[Callable[[str], Optional[str]]] = None


class SeriesRenamer:
    """Handles renaming of TV series files to a standardized format."""

    def __init__(self, config: SeriesConfig):
        self.config = config

    def get_season_from_directory(self, directory: Path) -> Optional[int]:
        """Extract season number from directory name."""
        for pattern in self.config.season_dir_patterns:
            match = pattern.search(directory.name)
            if match:
                # Check for named groups first (s_num, season_num)
                try:
                    groups = match.groupdict()
                    if groups:
                        # Try common named groups
                        for group_name in ['s_num', 'season_num', 'season']:
                            if group_name in groups and groups[group_name] is not None:
                                return int(groups[group_name])
                except (AttributeError, IndexError):
                    pass

                # Fall back to positional group 1
                try:
                    return int(match.group(1))
                except (IndexError, TypeError):
                    pass
        return None


    def parse_episode_info(self, filename: str, season_from_dir: Optional[int]) -> Optional[EpisodeInfo]:
        """Parse episode information from filename."""
        for ep_pattern in self.config.episode_patterns:
            match = ep_pattern.pattern.match(filename)
            if not match:
                continue

            # Extract season
            season: Optional[int] = None
            if ep_pattern.season_group is not None:
                try:
                    season_str = match.group(ep_pattern.season_group)
                    if season_str:
                        season = int(season_str)
                except (IndexError, TypeError):
                    pass

            if season is None:
                season = season_from_dir

            if season is None:
                continue  # Can't determine season

            # Extract episodes
            try:
                episodes_str = match.group(ep_pattern.episodes_group)
            except (IndexError, TypeError):
                continue

            # Parse episodes - could be "E01E02" format or single number
            if episodes_str.upper().startswith('E') or re.search(r'E\d+', episodes_str, re.IGNORECASE):
                # Multi-episode format like "E01" or "E01E02"
                episodes = [int(m.group(1)) for m in re.finditer(r"[Ee](\d+)", episodes_str)]
            else:
                # Single number
                episodes = [int(episodes_str)]

            if not episodes:
                continue

            # Extract resolution from pattern
            resolution: Optional[str] = None
            if ep_pattern.resolution_group is not None:
                try:
                    res_str = match.group(ep_pattern.resolution_group)
                    if res_str:
                        resolution = f"{res_str}p" if not res_str.endswith('p') else res_str
                except (IndexError, TypeError):
                    pass

            return EpisodeInfo(
                season=season,
                episodes=episodes,
                resolution=resolution,
            )

        return None

    def build_new_filename(self, season: int, episodes: list[int], resolution: str) -> str:
        """Build the new filename in standard format."""
        season_str = f"S{season:02d}"
        episodes_str = "".join(f"E{ep:02d}" for ep in episodes)
        return f"{self.config.show_name}.{season_str}{episodes_str}.{resolution}.mkv"

    def rename_files_in_season(self, season_dir: Path, season_num: int, dry_run: bool = True):
        """Rename all episode files in a season directory."""
        resolution_cache: Optional[str] = None
        files_to_rename: list[tuple[Path, EpisodeInfo]] = []

        for file in sorted(season_dir.iterdir()):
            if not file.is_file() or not file.name.lower().endswith(".mkv"):
                continue

            info = self.parse_episode_info(file.name, season_num)
            if not info:
                print(f"  Skipping unmatched file: {file.name}")
                continue

            files_to_rename.append((file, info))

        # Determine resolution for the season
        if files_to_rename:
            first_file, first_info = files_to_rename[0]

            # Priority: filename pattern -> resolution_extractor -> mkvinfo -> error
            if first_info.resolution:
                resolution_cache = first_info.resolution
            elif self.config.resolution_extractor:
                resolution_cache = self.config.resolution_extractor(first_file.name)

            if not resolution_cache:
                print(f"  Getting resolution from mkvinfo...")
                resolution_cache = self.get_resolution_from_mkvinfo(first_file)

            if not resolution_cache:
                print(f"  Error: Could not determine resolution for {first_file.name}")
                print(f"  Skipping season {season_num}")
                return

        # Now rename all files
        for file, info in files_to_rename:
            # Resolution priority for each file: its own -> resolution_extractor -> cache
            resolution = info.resolution
            if not resolution and self.config.resolution_extractor:
                resolution = self.config.resolution_extractor(file.name)
            if not resolution:
                resolution = resolution_cache

            new_name = self.build_new_filename(info.season, info.episodes, resolution)

            if file.name == new_name:
                print(f"  Already correct: {file.name}")
                continue

            new_path = file.parent / new_name
            print(f"  {file.name} -> {new_name}")

            if not dry_run:
                file.rename(new_path)

    def rename_season_directory(self, season_dir: Path, dry_run: bool = True) -> Path:
        """Rename a season directory to the new format."""
        season_num = self.get_season_from_directory(season_dir)
        if season_num is None:
            print(f"Skipping unmatched directory: {season_dir.name}")
            return season_dir

        new_name = f"{self.config.show_name_spaced} {season_num}"

        if season_dir.name == new_name:
            print(f"Directory already correct: {season_dir.name}")
            return season_dir

        new_path = season_dir.parent / new_name
        print(f"Directory: {season_dir.name} -> {new_name}")

        if not dry_run:
            season_dir.rename(new_path)
            return new_path

        return season_dir

    def run(self, dry_run: bool = True):
        """Run the renaming process for all seasons."""
        if dry_run:
            print("=== DRY RUN MODE (no changes will be made) ===\n")
        else:
            print("=== EXECUTING RENAMES ===\n")

        if not self.config.base_dir.exists():
            print(f"Error: {self.config.base_dir} does not exist")
            sys.exit(1)

        # Collect all season directories
        season_dirs = sorted([d for d in self.config.base_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])

        # First, rename files inside each season directory
        for season_dir in season_dirs:
            season_num = self.get_season_from_directory(season_dir)
            if season_num is None:
                print(f"\nSkipping non-season directory: {season_dir.name}")
                continue

            print(f"\nProcessing: {season_dir.name} (Season {season_num})")
            self.rename_files_in_season(season_dir, season_num, dry_run)

        # Then, rename the season directories themselves
        print("\n--- Renaming directories ---")
        for season_dir in season_dirs:
            if self.get_season_from_directory(season_dir) is None:
                continue
            self.rename_season_directory(season_dir, dry_run)

        if dry_run:
            print("\n=== Run without --dry-run to apply changes ===")


    @staticmethod
    def get_resolution_from_mkvinfo(filepath: Path) -> Optional[str]:
        """Get video resolution from mkv file using mkvinfo."""
        try:
            result = subprocess.run(
                ["mkvinfo", str(filepath)],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Look for "Pixel height: XXXX" in output
            height_match = re.search(r"Pixel height:\s*(\d+)", result.stdout)
            if height_match:
                height = int(height_match.group(1))
                # Map common heights to resolution labels
                # Use slightly lower thresholds to account for minor variations (e.g., 1068, 1072 -> 1080p)
                if height >= 2000:
                    return "2160p"
                elif height >= 1000:
                    return "1080p"
                elif height >= 680:
                    return "720p"
                elif height >= 450:
                    return "480p"
                else:
                    return f"{height}p"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"  Warning: Could not get resolution from mkvinfo: {e}")

        return None


def create_cli_main(config: SeriesConfig) -> Callable[[], None]:
    """Create a main function for CLI usage with a given config."""
    def main():
        dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
        renamer = SeriesRenamer(config)
        renamer.run(dry_run)

    return main
