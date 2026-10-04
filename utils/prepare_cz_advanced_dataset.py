import argparse
import json
from pathlib import Path

from normalize_data import normalize_file
from split_train_test import collect_json_files, copy_files, recreate_dir, split_files


def write_raw_profiles(input_file: Path, output_dir: Path) -> int:
    with input_file.open("r", encoding="utf-8") as handle:
        people = json.load(handle)

    if not isinstance(people, list):
        raise ValueError(f"Expected a JSON array in '{input_file}'.")

    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for index, person in enumerate(people):
        if not isinstance(person, dict):
            raise ValueError(
                f"Expected each item to be an object in '{input_file}', "
                f"but item {index} is {type(person).__name__}."
            )

        person_id = person.get("id")
        if not person_id:
            raise ValueError(f"Missing 'id' for item {index} in '{input_file}'.")

        output_path = output_dir / f"{person_id}.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(person, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        written += 1

    return written


def normalize_profiles(raw_dir: Path, normalized_dir: Path) -> int:
    recreate_dir(normalized_dir)

    normalized = 0
    for raw_file in collect_json_files(raw_dir):
        output_file = normalized_dir / raw_file.name
        normalize_file(raw_file, output_file, birth_key="birth_date")
        normalized += 1

    return normalized


def create_train_test_split(
    normalized_dir: Path,
    split_root: Path,
    dataset_name: str,
    train_ratio: float,
    seed: int,
) -> tuple[int, int]:
    files = collect_json_files(normalized_dir)
    if not files:
        raise ValueError(f"No JSON files found in: {normalized_dir}")

    train_files, test_files = split_files(files, train_ratio, seed)

    dataset_root = split_root / dataset_name
    train_dir = dataset_root / "train"
    test_dir = dataset_root / "test"

    recreate_dir(train_dir)
    recreate_dir(test_dir)

    copy_files(train_files, train_dir)
    copy_files(test_files, test_dir)

    return len(train_files), len(test_files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the CZ advanced dataset by splitting the source file into individual "
            "profiles, normalizing them, and creating a train/test split."
        )
    )
    parser.add_argument(
        "--input-file",
        default="people_data_1000_de_advanced.json",
        help="Source people_data JSON file",
    )
    parser.add_argument(
        "--raw-output-dir",
        default="data/testing/de_advanced",
        help="Directory for one raw JSON file per profile",
    )
    parser.add_argument(
        "--normalized-output-dir",
        default="data/clones/normalized_de_advanced",
        help="Directory for normalized profile JSON files",
    )
    parser.add_argument(
        "--split-output-root",
        default="data/clones_split",
        help="Root directory for train/test split datasets",
    )
    parser.add_argument(
        "--dataset-name",
        default="de_advanced",
        help="Dataset directory name inside the split output root",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Train split ratio between 0 and 1",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible train/test split",
    )
    args = parser.parse_args()

    if not 0 < args.train_ratio < 1:
        raise ValueError("--train-ratio must be between 0 and 1.")

    input_file = Path(args.input_file)
    raw_output_dir = Path(args.raw_output_dir)
    normalized_output_dir = Path(args.normalized_output_dir)
    split_output_root = Path(args.split_output_root)

    recreate_dir(raw_output_dir)
    raw_count = write_raw_profiles(input_file, raw_output_dir)
    normalized_count = normalize_profiles(raw_output_dir, normalized_output_dir)
    train_count, test_count = create_train_test_split(
        normalized_output_dir,
        split_output_root,
        args.dataset_name,
        args.train_ratio,
        args.seed,
    )

    print(f"Raw profiles: {raw_count} -> {raw_output_dir}")
    print(f"Normalized profiles: {normalized_count} -> {normalized_output_dir}")
    print(f"Train files: {train_count} -> {split_output_root / args.dataset_name / 'train'}")
    print(f"Test files: {test_count} -> {split_output_root / args.dataset_name / 'test'}")
    print(f"Seed: {args.seed}")


if __name__ == "__main__":
    main()
