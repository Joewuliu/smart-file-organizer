"""Command-line interface for the Smart File Organizer."""

import argparse
from pathlib import Path

from organizer import history
from organizer.classifier import DEFAULT_RULES, category_names
from organizer.config import ConfigError, load_rules
from organizer.date_organizer import is_date_destination_dir
from organizer.mover import execute_moves
from organizer.planner import PlannedMove, plan_moves, plan_moves_by_date
from organizer.scanner import scan_directory


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="smart-organizer",
        description="Organize files in a directory by file type.",
    )
    parser.add_argument(
        "directory", nargs="?", default=None, help="Directory to organize (omit with --undo)"
    )
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
    parser.add_argument(
        "--by",
        choices=["category", "date"],
        default="category",
        help="Organize by rule-based category (default) or by modification date",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Undo the most recent successful apply operation",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Also scan nested subdirectories (default: top level only)",
    )
    return parser.parse_args(argv)


def _print_preview(root: Path, plan: list[PlannedMove]) -> None:
    print("Proposed moves:\n")
    for move in plan:
        relative_source = move.source.relative_to(root)
        relative_destination = move.destination.relative_to(root)
        print(str(relative_source))
        print(f"  -> {relative_destination}\n")
    print(f"{len(plan)} files would be moved.")
    print("No files have been modified.")


def _print_undo_preview(root: Path, plan: list[PlannedMove]) -> None:
    print("Undo last operation:\n")
    for move in plan:
        relative_source = move.source.relative_to(root)
        relative_destination = move.destination.relative_to(root)
        print(str(relative_source))
        print(f"  -> {relative_destination}\n")
    print(f"{len(plan)} files would be restored.")


def _print_results(root: Path, results) -> int:
    moved = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\nMove results:\n")
    print(f"Moved: {len(moved)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print()
        for result in failed:
            relative_source = result.move.source.relative_to(root)
            relative_destination = result.move.destination.relative_to(root)
            print(f"  {relative_source} -> {relative_destination}: {result.error}")
        return 1

    return 0


def _run_undo() -> int:
    operation = history.load_last_operation()
    if operation is None:
        print("No operation available to undo.")
        return 0

    undo_plan = history.build_undo_plan(operation)
    root = operation.root

    print("Smart File Organizer\n")
    _print_undo_preview(root, undo_plan)

    answer = input("Undo these changes? [y/N]: ")
    if answer.strip().lower() not in ("y", "yes"):
        print("Operation cancelled. No files were modified.")
        return 0

    results = execute_moves(undo_plan)

    remaining = [
        history.HistoryMove(source=result.move.destination, destination=result.move.source)
        for result in results
        if not result.success
    ]
    if remaining:
        history.save_remaining_operation(remaining, root)
    else:
        history.clear_history()

    return _print_results(root, results)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.undo:
        if args.directory is not None:
            print("Error: --undo cannot be combined with a directory argument.")
            return 1
        if args.apply:
            print(
                "Error: --undo cannot be combined with --apply "
                "(undo always previews and confirms on its own)."
            )
            return 1
        if args.by == "date":
            print("Error: --undo cannot be combined with --by (undo does not reclassify files).")
            return 1
        if args.config:
            print(
                "Error: --undo cannot be combined with --config "
                "(undo does not use classification rules)."
            )
            return 1
        if args.recursive:
            print(
                "Error: --undo cannot be combined with --recursive "
                "(undo does not rescan any directory)."
            )
            return 1
        return _run_undo()

    if args.directory is None:
        print("Error: a directory argument is required unless --undo is given.")
        return 1

    root = Path(args.directory)

    if args.by == "date" and args.config:
        print(
            "Error: --config cannot be combined with --by date "
            "(date mode does not use classification rules)."
        )
        return 1

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

    exclude_dir = None
    if args.recursive:
        if args.by == "date":
            exclude_dir = is_date_destination_dir
        else:
            excluded_categories = category_names(rules)

            def exclude_dir(relative_path: Path) -> bool:
                parts = relative_path.parts
                return len(parts) == 1 and parts[0] in excluded_categories

    try:
        files = scan_directory(root, recursive=args.recursive, exclude_dir=exclude_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {exc}")
        return 1

    if not files:
        print("No files to organize.")
        return 0

    try:
        if args.by == "date":
            plan = plan_moves_by_date(files, root)
        else:
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
    history.record_operation(results, root)
    return _print_results(root, results)


if __name__ == "__main__":
    raise SystemExit(main())
