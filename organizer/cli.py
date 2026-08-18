"""Command-line interface for the Smart File Organizer."""

import argparse
from pathlib import Path

from organizer.classifier import DEFAULT_RULES
from organizer.config import ConfigError, load_rules
from organizer.mover import execute_moves
from organizer.planner import PlannedMove, plan_moves
from organizer.scanner import scan_directory


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="smart-organizer",
        description="Organize files in a directory by file type.",
    )
    parser.add_argument("directory", help="Directory to organize")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the proposed moves after confirmation (default: dry run only)",
    )
    parser.add_argument(
        "--config",
        help="Path to a TOML file defining custom classification rules "
        "(default: use built-in rules)",
    )
    return parser.parse_args(argv)


def _print_preview(root: Path, plan: list[PlannedMove]) -> None:
    print("Proposed moves:\n")
    for move in plan:
        relative_destination = move.destination.relative_to(root)
        print(move.source.name)
        print(f"  -> {relative_destination}\n")
    print(f"{len(plan)} files would be moved.")
    print("No files have been modified.")


def _print_results(root: Path, results) -> int:
    moved = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\nMove results:\n")
    print(f"Moved: {len(moved)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print()
        for result in failed:
            relative_destination = result.move.destination.relative_to(root)
            print(f"  {result.move.source.name} -> {relative_destination}: {result.error}")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.directory)

    rules = DEFAULT_RULES
    if args.config:
        try:
            rules = load_rules(Path(args.config))
        except ConfigError as exc:
            print(f"Error: {exc}")
            return 1

    print("Smart File Organizer\n")
    print("Scanning:")
    print(f"{root}\n")

    try:
        files = scan_directory(root)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {exc}")
        return 1

    if not files:
        print("No files to organize.")
        return 0

    try:
        plan = plan_moves(files, root, rules)
    except NotADirectoryError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Found {len(files)} files.\n")
    _print_preview(root, plan)

    if not args.apply:
        print("Dry run only. No files were modified.")
        return 0

    answer = input("Apply these changes? [y/N]: ")
    if answer.strip().lower() not in ("y", "yes"):
        print("Operation cancelled. No files were modified.")
        return 0

    results = execute_moves(plan)
    return _print_results(root, results)


if __name__ == "__main__":
    raise SystemExit(main())
