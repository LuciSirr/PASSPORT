import argparse
import random
import shutil
from pathlib import Path


def collect_json_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix == ".json")


def split_files(files: list[Path], train_ratio: float, seed: int) -> tuple[list[Path], list[Path]]:
    shuffled = files[:]
    random.Random(seed).shuffle(shuffled)

    train_count = int(len(shuffled) * train_ratio)
    if shuffled and train_count == 0:
        train_count = 1
    if len(shuffled) > 1 and train_count == len(shuffled):
        train_count -= 1

    return shuffled[:train_count], shuffled[train_count:]


def recreate_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_files(files: list[Path], output_dir: Path) -> None:
    for file_path in files:
        shutil.copy2(file_path, output_dir / file_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a random train/test split for one dataset directory."
    )
    parser.add_argument(
        "dataset",
        help="Dataset directory name inside data/clones, for example: normalized_cz, normalized_uk, normalized_de",
    )
    parser.add_argument(
        "--input-root",
        default="data/clones",
        help="Root directory that contains the dataset folder",
    )
    parser.add_argument(
        "--output-root",
        default="data/clones_split",
        help="Root directory where train/test split folders will be created",
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
        help="Random seed for reproducible splits",
    )
    args = parser.parse_args()

    if not 0 < args.train_ratio < 1:
        raise ValueError("--train-ratio must be between 0 and 1.")

    input_dir = Path(args.input_root) / args.dataset
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {input_dir}")

    files = collect_json_files(input_dir)
    if not files:
        raise ValueError(f"No JSON files found in: {input_dir}")

    train_files, test_files = split_files(files, args.train_ratio, args.seed)

    split_root = Path(args.output_root) / args.dataset
    train_dir = split_root / "train"
    test_dir = split_root / "test"

    recreate_dir(train_dir)
    recreate_dir(test_dir)

    copy_files(train_files, train_dir)
    copy_files(test_files, test_dir)

    print(f"Input directory: {input_dir}")
    print(f"Train files: {len(train_files)} -> {train_dir}")
    print(f"Test files: {len(test_files)} -> {test_dir}")
    print(f"Seed: {args.seed}")


if __name__ == "__main__":
    main()
