import argparse
import json
import random
from datetime import date, datetime
from pathlib import Path


def parse_reference_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def random_birth_date_for_age(age: int, reference_date: date, rng: random.Random) -> date:
    had_birthday = rng.choice([True, False])
    birth_year = reference_date.year - age if had_birthday else reference_date.year - age - 1

    if had_birthday:
        start_ordinal = date(birth_year, 1, 1).toordinal()
        end_ordinal = date(birth_year, reference_date.month, reference_date.day).toordinal()
    else:
        if reference_date.month == 12 and reference_date.day == 31:
            start_ordinal = date(birth_year, 1, 1).toordinal()
            end_ordinal = date(birth_year, 12, 31).toordinal()
        else:
            next_day = reference_date.toordinal() + 1
            start_month_day = date.fromordinal(next_day)
            start_ordinal = date(birth_year, start_month_day.month, start_month_day.day).toordinal()
            end_ordinal = date(birth_year, 12, 31).toordinal()

    chosen = rng.randint(start_ordinal, end_ordinal)
    return date.fromordinal(chosen)


def add_birth_dates(
    input_dir: Path,
    field_name: str,
    reference_date: date,
    seed: int,
    overwrite: bool,
) -> tuple[int, int]:
    rng = random.Random(seed)
    updated = 0
    skipped = 0

    for path in sorted(input_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if field_name in data and not overwrite:
            skipped += 1
            continue

        age = data.get("age")
        if not isinstance(age, int):
            skipped += 1
            continue

        birth_date = random_birth_date_for_age(age, reference_date, rng)
        data[field_name] = birth_date.isoformat()

        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

        updated += 1

    return updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a random birth date to each clone JSON based on the clone's age."
    )
    parser.add_argument("input_dir", help="Directory containing clone JSON files")
    parser.add_argument(
        "--field-name",
        default="birth_date",
        help="Field name to write into each JSON file",
    )
    parser.add_argument(
        "--reference-date",
        default="2026-03-28",
        help="Reference date used to interpret the stored age, format YYYY-MM-DD",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible birth dates",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing birth date values if the field already exists",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    reference_date = parse_reference_date(args.reference_date)
    updated, skipped = add_birth_dates(
        input_dir=input_dir,
        field_name=args.field_name,
        reference_date=reference_date,
        seed=args.seed,
        overwrite=args.overwrite,
    )

    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Reference date: {reference_date.isoformat()}")
    print(f"Field name: {args.field_name}")


if __name__ == "__main__":
    main()
