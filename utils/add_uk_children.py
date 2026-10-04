import argparse
import hashlib
import json
from pathlib import Path


CHILD_NAME_POOL = [
    "Oliver",
    "Amelia",
    "George",
    "Isla",
    "Noah",
    "Ava",
    "Leo",
    "Mia",
    "Arthur",
    "Freya",
    "Oscar",
    "Lily",
    "Harry",
    "Ivy",
    "Jack",
    "Rosie",
    "Charlie",
    "Evie",
]


def stable_number(seed_text: str) -> int:
    return int(hashlib.md5(seed_text.encode("utf-8")).hexdigest(), 16)


def choose_name(profile_id: str, index: int) -> str:
    seed = stable_number(f"{profile_id}:child:{index}")
    return CHILD_NAME_POOL[seed % len(CHILD_NAME_POOL)]


def should_add_children(profile: dict, threshold: int) -> bool:
    if not isinstance(profile.get("children"), list) or profile.get("children"):
        return False

    age = profile.get("age")
    if not isinstance(age, int) or age < 28 or age > 55:
        return False

    if not profile.get("self_last_name"):
        return False

    relationship_hint = str(profile.get("marital_status") or "").strip().lower()
    has_partner = bool(profile.get("partner_first_name") or profile.get("partner_last_name"))

    if not has_partner and "married" not in relationship_hint and "relationship" not in relationship_hint:
        return False

    profile_id = str(profile.get("id") or "")
    if not profile_id:
        return False

    return stable_number(f"{profile_id}:eligible") % 100 < threshold


def build_children(profile: dict) -> list[dict]:
    profile_id = str(profile["id"])
    count = 1 + (stable_number(f"{profile_id}:count") % 3)
    last_name = profile.get("self_last_name") or profile.get("partner_last_name") or "Smith"

    children = []
    for index in range(count):
        children.append(
            {
                "first_name": choose_name(profile_id, index),
                "last_name": last_name,
            }
        )
    return children


def process_dir(root: Path, threshold: int) -> tuple[int, int]:
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
        if not should_add_children(data, threshold):
            continue

        data["children"] = build_children(data)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        changed += 1

    return scanned, changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add deterministic child entries to a subset of UK clone profiles."
    )
    parser.add_argument("roots", nargs="+", help="Directories containing UK clone JSON files")
    parser.add_argument(
        "--threshold",
        type=int,
        default=18,
        help="Percentage of eligible profiles that should receive children",
    )
    args = parser.parse_args()

    total_scanned = 0
    total_changed = 0
    for root_text in args.roots:
        root = Path(root_text)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root}")
        scanned, changed = process_dir(root, args.threshold)
        total_scanned += scanned
        total_changed += changed
        print(f"{root}: scanned={scanned} changed={changed}")

    print(f"Total scanned: {total_scanned}")
    print(f"Total changed: {total_changed}")


if __name__ == "__main__":
    main()
