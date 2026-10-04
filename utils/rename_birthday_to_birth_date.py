import argparse
import json
from pathlib import Path


def iter_json_files(paths: list[str], recursive: bool):
    seen: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file() and path.suffix.lower() == ".json":
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path
            continue

        if path.is_dir():
            pattern = "**/*.json" if recursive else "*.json"
            for json_path in sorted(path.glob(pattern)):
                if json_path.is_file():
                    resolved = json_path.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        yield json_path


def migrate_file(path: Path, dry_run: bool) -> str:
    with path.open("r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            return f"ERROR  {path}: invalid JSON ({exc})"

    if not isinstance(data, dict):
        return f"SKIP   {path}: top-level JSON is not an object"

    has_birthday = "birthday" in data
    has_birth_date = "birth_date" in data

    if not has_birthday:
        return f"SKIP   {path}: no birthday field"

    if has_birth_date:
        return f"SKIP   {path}: both birthday and birth_date exist"

    data["birth_date"] = data.pop("birthday")

    if not dry_run:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    action = "WOULD " if dry_run else "DONE  "
    return f"{action}{path}: renamed birthday -> birth_date"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename top-level JSON field 'birthday' to 'birth_date'."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="JSON files or directories to process.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively process JSON files in directories.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without rewriting files.",
    )
    args = parser.parse_args()

    processed = 0
    changed = 0

    for json_file in iter_json_files(args.paths, recursive=args.recursive):
        processed += 1
        result = migrate_file(json_file, dry_run=args.dry_run)
        print(result)
        if result.startswith("WOULD ") or result.startswith("DONE  "):
            changed += 1

    print(f"\nProcessed {processed} JSON files; {'would change' if args.dry_run else 'changed'} {changed}.")


if __name__ == "__main__":
    main()
