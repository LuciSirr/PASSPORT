import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from personal_data_analysis import PersonalDataMatcher, summarize_personal_data_usage


def load_passwords(wordlist_path: Path) -> list[str]:
    passwords = []
    with wordlist_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            password = line.strip()
            if password:
                passwords.append(password)
    return passwords


def password_shape(password: str) -> str:
    chunks = []
    current_type = None
    current_len = 0

    for char in password:
        if char.isalpha():
            char_type = "L"
        elif char.isdigit():
            char_type = "D"
        else:
            char_type = "S"

        if char_type == current_type:
            current_len += 1
        else:
            if current_type is not None:
                chunks.append(f"{current_type}{current_len}")
            current_type = char_type
            current_len = 1

    if current_type is not None:
        chunks.append(f"{current_type}{current_len}")

    return "+".join(chunks)


def password_case_mask(password: str) -> str:
    chunks = []
    current_type = None
    current_len = 0

    for char in password:
        if char.isupper():
            char_type = "U"
        elif char.islower():
            char_type = "L"
        elif char.isdigit():
            char_type = "D"
        else:
            char_type = "S"

        if char_type == current_type:
            current_len += 1
        else:
            if current_type is not None:
                chunks.append(f"{current_type}{current_len}")
            current_type = char_type
            current_len = 1

    if current_type is not None:
        chunks.append(f"{current_type}{current_len}")

    return "+".join(chunks)


def analyze_passwords(
    passwords: list[str],
    top_n: int,
    profile: dict | None = None,
) -> dict:
    lengths = []
    shapes = Counter()
    case_masks = Counter()
    contains_digit = 0
    contains_symbol = 0
    all_lower = 0
    personal_results = []
    matcher = PersonalDataMatcher(profile) if profile else None

    for password in passwords:
        lengths.append(len(password))
        shapes[password_shape(password)] += 1
        case_masks[password_case_mask(password)] += 1

        if any(char.isdigit() for char in password):
            contains_digit += 1
        if any(not char.isalnum() for char in password):
            contains_symbol += 1

        letters = [char for char in password if char.isalpha()]
        if letters and all(char.islower() for char in letters):
            all_lower += 1
        if matcher:
            personal_results.append(matcher.analyze_password(password))

    def top(counter: Counter) -> list[dict]:
        return [{"value": value, "count": count} for value, count in counter.most_common(top_n)]

    summary = {
        "count": len(passwords),
        "length": {
            "min": min(lengths) if lengths else None,
            "max": max(lengths) if lengths else None,
            "mean": round(mean(lengths), 2) if lengths else None,
        },
        "composition": {
            "contains_digit": contains_digit,
            "contains_symbol": contains_symbol,
            "all_lower_letters": all_lower,
        },
        "top_shapes": top(shapes),
        "top_case_masks": top(case_masks),
    }
    if matcher:
        summary["personal_data_usage"] = summarize_personal_data_usage(personal_results, top_n=top_n)
    return summary


def print_summary(summary: dict, dataset_name: str) -> None:
    print(f"Dataset: {dataset_name}")
    print(f"Passwords: {summary['count']}")
    print(
        "Password length: "
        f"{summary['length']['min']} - {summary['length']['max']} "
        f"(mean {summary['length']['mean']})"
    )
    print(
        "Contains digit: "
        f"{summary['composition']['contains_digit']}/{summary['count']}"
    )
    print(
        "Contains symbol: "
        f"{summary['composition']['contains_symbol']}/{summary['count']}"
    )
    print(
        "All lower letters: "
        f"{summary['composition']['all_lower_letters']}/{summary['count']}"
    )
    personal_usage = summary.get("personal_data_usage")
    if personal_usage:
        print(
            "Contains personal data: "
            f"{personal_usage['passwords_with_personal_data']}/{summary['count']} "
            f"({personal_usage['share_of_passwords_with_personal_data'] * 100:.2f}%)"
        )
        print(
            "Average personal-data character share: "
            f"{personal_usage['average_personal_char_ratio'] * 100:.2f}% "
            f"(when present {personal_usage['average_personal_char_ratio_when_present'] * 100:.2f}%)"
        )

    sections = [
        ("Top password shapes", "top_shapes"),
        ("Top uppercase/lowercase case masks", "top_case_masks"),
    ]
    if personal_usage:
        sections.append(("Top personal-data fields", "top_personal_fields"))

    for title, key in sections:
        print(f"\n{title}:")
        if key in summary:
            items = summary[key]
        else:
            items = personal_usage[key]
        if not items:
            print("  (none)")
            continue
        for item in items:
            print(f"  {item['value']}: {item['count']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a plain-text password wordlist."
    )
    parser.add_argument("wordlist", help="Path to a text file containing one password per line")
    parser.add_argument(
        "--top-n",
        type=int,
        default=15,
        help="How many top values to show for each category",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to save the analysis summary as JSON",
    )
    parser.add_argument(
        "--profile",
        help="Optional profile JSON used to estimate how much personal data appears in the passwords",
    )
    args = parser.parse_args()

    wordlist_path = Path(args.wordlist)
    if not wordlist_path.is_file():
        raise FileNotFoundError(f"Wordlist file not found: {wordlist_path}")

    passwords = load_passwords(wordlist_path)
    if not passwords:
        raise ValueError(f"No passwords found in: {wordlist_path}")

    profile = None
    if args.profile:
        profile_path = Path(args.profile)
        if not profile_path.is_file():
            raise FileNotFoundError(f"Profile file not found: {profile_path}")
        with profile_path.open("r", encoding="utf-8") as handle:
            profile = json.load(handle)

    summary = analyze_passwords(passwords, top_n=args.top_n, profile=profile)
    print_summary(summary, wordlist_path.name)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
            handle.write("\n")


if __name__ == "__main__":
    main()
