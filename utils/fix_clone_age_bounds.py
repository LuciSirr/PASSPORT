import argparse
import json
from pathlib import Path


def clamp_age(age: int, min_age: int, max_age: int) -> int:
    return max(min_age, min(max_age, age))


def shift_birth_year(date_text: str, year_delta: int) -> str:
    parts = date_text.split("-")
    if len(parts) != 3:
        return date_text

    try:
        year = int(parts[0])
    except ValueError:
        return date_text

    parts[0] = f"{year + year_delta:04d}"
    return "-".join(parts)


def update_profile(profile: dict, min_age: int, max_age: int) -> bool:
    age = profile.get("age")
    if not isinstance(age, int):
        return False

    new_age = clamp_age(age, min_age, max_age)
    if new_age == age:
        return False

    year_delta = age - new_age
    profile["age"] = new_age

    for birth_key in ("birth_date", "birthday"):
        birth_value = profile.get(birth_key)
        if isinstance(birth_value, str) and birth_value.strip():
            profile[birth_key] = shift_birth_year(birth_value, year_delta)

    return True


def process_root(root: Path, min_age: int, max_age: int) -> tuple[int, int]:
    scanned = 0
    changed = 0

    for path in root.rglob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        scanned += 1
        if not update_profile(data, min_age, max_age):
            continue

        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        changed += 1

    return scanned, changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clamp clone ages into a target interval and shift birth years to match."
    )
    parser.add_argument(
        "roots",
        nargs="+",
        help="One or more directories that contain clone JSON files",
    )
    parser.add_argument("--min-age", type=int, default=6)
    parser.add_argument("--max-age", type=int, default=85)
    args = parser.parse_args()

    if args.min_age > args.max_age:
        raise ValueError("--min-age must be less than or equal to --max-age")

    total_scanned = 0
    total_changed = 0
    for root_text in args.roots:
        root = Path(root_text)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root}")
        scanned, changed = process_root(root, args.min_age, args.max_age)
        total_scanned += scanned
        total_changed += changed
        print(f"{root}: scanned={scanned} changed={changed}")

    print(f"Total scanned: {total_scanned}")
    print(f"Total changed: {total_changed}")


if __name__ == "__main__":
    main()
