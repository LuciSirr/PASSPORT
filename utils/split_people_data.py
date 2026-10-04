import argparse
import json
from pathlib import Path


SUPPORTED_COUNTRIES = ("cz", "uk", "de")


def infer_country_from_filename(input_path: Path) -> str:
    filename = input_path.name.lower()
    for country in SUPPORTED_COUNTRIES:
        if f"_{country}" in filename:
            return country
    raise ValueError(
        f"Could not infer target directory from filename '{input_path.name}'. "
        f"Expected one of: {', '.join(SUPPORTED_COUNTRIES)}."
    )


def split_people_file(input_path: Path, output_root: Path) -> int:
    with input_path.open("r", encoding="utf-8") as handle:
        people = json.load(handle)

    if not isinstance(people, list):
        raise ValueError(f"Expected a JSON array in '{input_path}'.")

    country = infer_country_from_filename(input_path)
    output_dir = output_root / country
    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for index, person in enumerate(people):
        if not isinstance(person, dict):
            raise ValueError(
                f"Expected each item to be an object in '{input_path}', "
                f"but item {index} is {type(person).__name__}."
            )

        person_id = person.get("id")
        if not person_id:
            raise ValueError(f"Missing 'id' for item {index} in '{input_path}'.")

        output_path = output_dir / f"{person_id}.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(person, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Split a people_data_1000_*.json file into one JSON file per person. "
            "The output directory is inferred from the filename suffix: cz, uk, or de."
        )
    )
    parser.add_argument("input_file", help="Path to a people_data_1000_*.json file")
    parser.add_argument(
        "--output-root",
        default="data/testing",
        help="Base directory where cz/uk/de folders will be created",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_root = Path(args.output_root)

    written = split_people_file(input_path, output_root)
    print(f"Wrote {written} people to {output_root / infer_country_from_filename(input_path)}")


if __name__ == "__main__":
    main()
