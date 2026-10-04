import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from personal_data_analysis import PersonalDataMatcher, summarize_personal_data_usage


def load_profiles(input_dir: Path) -> list[dict]:
    profiles = []
    for path in sorted(input_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            profiles.append(data)
    return profiles


def non_empty_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def add_counter_value(counter: Counter, value) -> None:
    text = non_empty_str(value)
    if text:
        counter[text] += 1


def add_counter_values(counter: Counter, values) -> None:
    if not isinstance(values, list):
        return
    for value in values:
        add_counter_value(counter, value)


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


def password_analysis(passwords: list[str], top_n: int) -> dict:
    lengths = []
    shapes = Counter()
    case_masks = Counter()
    contains_digit = 0
    contains_symbol = 0
    all_lower = 0

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

    def top(counter: Counter) -> list[dict]:
        return [{"value": value, "count": count} for value, count in counter.most_common(top_n)]

    total = len(passwords)

    return {
        "count": total,
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


def aggregate_personal_data_usage(profiles: list[dict], top_n: int) -> dict:
    results = []

    for profile in profiles:
        matcher = PersonalDataMatcher(profile)
        passwords = profile.get("previous_passwords")
        if not isinstance(passwords, list):
            continue
        for password in passwords:
            text = non_empty_str(password)
            if text:
                results.append(matcher.analyze_password(text))

    return summarize_personal_data_usage(results, top_n=top_n)


def summarize_profiles(profiles: list[dict], top_n: int) -> dict:
    first_names = Counter()
    last_names = Counter()
    partner_first_names = Counter()
    partner_last_names = Counter()
    interests = Counter()
    favorite_hobbies = Counter()
    pet_names = Counter()
    pet_types = Counter()
    regions = Counter()
    nationalities = Counter()
    companies = Counter()
    car_brands = Counter()
    employments = Counter()
    sectors = Counter()
    education = Counter()
    marital_status = Counter()
    genders = Counter()

    ages = []
    people_with_children = 0
    total_children = 0
    people_with_pets = 0
    total_pets = 0
    people_with_passwords = 0
    total_passwords = 0
    missing_birth = 0
    all_passwords = []

    for profile in profiles:
        add_counter_value(first_names, profile.get("self_first_name"))
        add_counter_value(last_names, profile.get("self_last_name"))
        add_counter_value(partner_first_names, profile.get("partner_first_name"))
        add_counter_value(partner_last_names, profile.get("partner_last_name"))
        add_counter_values(interests, profile.get("interests"))
        add_counter_value(favorite_hobbies, profile.get("favorite_hobby"))
        add_counter_value(regions, profile.get("region"))
        add_counter_value(nationalities, profile.get("nationality"))
        add_counter_value(companies, profile.get("company"))
        add_counter_value(car_brands, profile.get("car_brand"))
        add_counter_value(employments, profile.get("employment"))
        add_counter_value(sectors, profile.get("sector"))
        add_counter_value(education, profile.get("education"))
        add_counter_value(marital_status, profile.get("marital_status"))
        add_counter_value(genders, profile.get("gender"))

        age = profile.get("age")
        if isinstance(age, (int, float)):
            ages.append(age)

        birth = non_empty_str(profile.get("birth_date")) or non_empty_str(profile.get("birthday"))
        if not birth:
            missing_birth += 1

        children = profile.get("children") if isinstance(profile.get("children"), list) else []
        if children:
            people_with_children += 1
            total_children += len(children)

        pets = profile.get("pets") if isinstance(profile.get("pets"), list) else []
        if pets:
            people_with_pets += 1
            total_pets += len(pets)
        for pet in pets:
            if isinstance(pet, dict):
                add_counter_value(pet_names, pet.get("pet_name"))
                add_counter_value(pet_types, pet.get("pet_type"))

        passwords = profile.get("previous_passwords")
        if isinstance(passwords, list) and passwords:
            people_with_passwords += 1
            total_passwords += len(passwords)
            all_passwords.extend(
                str(password) for password in passwords if non_empty_str(password)
            )

    def top(counter: Counter) -> list[dict]:
        return [{"value": value, "count": count} for value, count in counter.most_common(top_n)]

    total_profiles = len(profiles)

    return {
        "totals": {
            "profiles": total_profiles,
            "people_with_children": people_with_children,
            "total_children": total_children,
            "people_with_pets": people_with_pets,
            "total_pets": total_pets,
            "people_with_previous_passwords": people_with_passwords,
            "total_previous_passwords": total_passwords,
            "profiles_missing_birth_date": missing_birth,
        },
        "age": {
            "count": len(ages),
            "min": min(ages) if ages else None,
            "max": max(ages) if ages else None,
            "mean": round(mean(ages), 2) if ages else None,
        },
        "password_patterns": password_analysis(all_passwords, top_n=top_n),
        "password_personal_data_usage": aggregate_personal_data_usage(profiles, top_n=top_n),
        "top_first_names": top(first_names),
        "top_last_names": top(last_names),
        "top_partner_first_names": top(partner_first_names),
        "top_partner_last_names": top(partner_last_names),
        "top_interests": top(interests),
        "top_favorite_hobbies": top(favorite_hobbies),
        "top_pet_names": top(pet_names),
        "top_pet_types": top(pet_types),
        "top_regions": top(regions),
        "top_nationalities": top(nationalities),
        "top_companies": top(companies),
        "top_car_brands": top(car_brands),
        "employment_distribution": top(employments),
        "sector_distribution": top(sectors),
        "education_distribution": top(education),
        "marital_status_distribution": top(marital_status),
        "gender_distribution": top(genders),
    }


def print_summary(summary: dict, dataset_name: str) -> None:
    print(f"Dataset: {dataset_name}")
    print(f"Profiles: {summary['totals']['profiles']}")
    print(
        "Birth date missing: "
        f"{summary['totals']['profiles_missing_birth_date']}"
    )
    print(
        "Age range: "
        f"{summary['age']['min']} - {summary['age']['max']} "
        f"(mean {summary['age']['mean']})"
    )
    print(
        "People with children: "
        f"{summary['totals']['people_with_children']} "
        f"(total children {summary['totals']['total_children']})"
    )
    print(
        "People with pets: "
        f"{summary['totals']['people_with_pets']} "
        f"(total pets {summary['totals']['total_pets']})"
    )
    print(
        "People with previous passwords: "
        f"{summary['totals']['people_with_previous_passwords']} "
        f"(total passwords {summary['totals']['total_previous_passwords']})"
    )
    print(
        "Password length: "
        f"{summary['password_patterns']['length']['min']} - "
        f"{summary['password_patterns']['length']['max']} "
        f"(mean {summary['password_patterns']['length']['mean']})"
    )
    print(
        "Previous passwords with personal data: "
        f"{summary['password_personal_data_usage']['passwords_with_personal_data']}/"
        f"{summary['password_patterns']['count']} "
        f"({summary['password_personal_data_usage']['share_of_passwords_with_personal_data'] * 100:.2f}%)"
    )
    print(
        "Average personal-data character share in previous passwords: "
        f"{summary['password_personal_data_usage']['average_personal_char_ratio'] * 100:.2f}% "
        f"(when present "
        f"{summary['password_personal_data_usage']['average_personal_char_ratio_when_present'] * 100:.2f}%)"
    )

    sections = [
        ("Top password shapes", "top_shapes"),
        ("Top uppercase/lowercase case masks", "top_case_masks"),
        ("Top personal-data fields in previous passwords", "top_personal_fields"),
        ("Top first names", "top_first_names"),
        ("Top last names", "top_last_names"),
        ("Top interests", "top_interests"),
        ("Top favorite hobbies", "top_favorite_hobbies"),
        ("Top pet names", "top_pet_names"),
        ("Top pet types", "top_pet_types"),
        ("Top regions", "top_regions"),
        ("Employment distribution", "employment_distribution"),
        ("Sector distribution", "sector_distribution"),
    ]

    for title, key in sections:
        print(f"\n{title}:")
        if key in summary["password_patterns"]:
            items = summary["password_patterns"][key]
        elif key in summary["password_personal_data_usage"]:
            items = summary["password_personal_data_usage"][key]
        else:
            items = summary[key]
        if not items:
            print("  (none)")
            continue
        for item in items:
            print(f"  {item['value']}: {item['count']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a directory of clone profile JSON files."
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing one normalized clone JSON file per profile",
    )
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
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {input_dir}")

    profiles = load_profiles(input_dir)
    if not profiles:
        raise ValueError(f"No JSON profiles found in: {input_dir}")

    summary = summarize_profiles(profiles, top_n=args.top_n)
    print_summary(summary, input_dir.name)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
            handle.write("\n")


if __name__ == "__main__":
    main()
