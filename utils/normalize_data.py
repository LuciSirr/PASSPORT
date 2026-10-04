import argparse
import json
import re
from pathlib import Path


def safe_int(value, default=0):
    """Safely convert any value to int, even if it's None or text like '6 and more'."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r'\d+', str(value))
    return int(match.group()) if match else default

def safe_bool(value):
    """Convert None/False/True or string-like to int 0/1"""
    if value in [True, "True", "true", 1]:
        return 1
    return 0


def safe_lower(value, default=""):
    if value is None:
        return default
    return str(value).lower()


def safe_string(value, default=""):
    if value is None:
        return default
    return str(value)


def safe_float(value, default=0):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"-?\d+(\.\d+)?", str(value))
        return float(match.group()) if match else default


def parse_important_attributes(raw_value):
    result = {
        "self": {},
        "birth_date": "",
        "partner": {},
        "children": [],
        "interests": [],
        "pets": [],
        "company": "",
        "previous_passwords": []
    }

    if isinstance(raw_value, dict):
        data = raw_value
    elif isinstance(raw_value, str) and raw_value.strip():
        try:
            data = json.loads(raw_value)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    if not isinstance(data, dict):
        data = {}

    result["self"] = {
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", "")
    }
    result["birth_date"] = safe_string(
        data.get("birth_date") or data.get("birthday") or data.get("birth_day")
    )
    result["partner"] = {
        "first_name": data.get("partner_first_name", ""),
        "last_name": data.get("partner_last_name", "")
    }

    children = data.get("children") or []
    if isinstance(children, list):
        result["children"] = [
            {
                "first_name": child.get("first_name", child.get("child_first_name", "")),
                "last_name": child.get("last_name", child.get("child_last_name", ""))
            }
            for child in children
            if isinstance(child, dict)
        ]

    hobbies = data.get("hobbies") or []
    if isinstance(hobbies, list):
        result["interests"] = [item for item in hobbies if isinstance(item, str) and item]

    pets = data.get("pets") or []
    if isinstance(pets, list):
        result["pets"] = [
            {
                "pet_type": pet.get("pet_type", ""),
                "pet_name": pet.get("pet_name", "")
            }
            for pet in pets
            if isinstance(pet, dict)
        ]

    result["company"] = safe_string(data.get("company"))
    previous_passwords = data.get("previous_passwords") or []
    if isinstance(previous_passwords, list):
        result["previous_passwords"] = [
            password for password in previous_passwords if isinstance(password, str) and password
        ]

    return {k: v for k, v in result.items() if v}


def normalize_important_attributes(raw_str: str):
    return parse_important_attributes(raw_str)


def normalize_person_data(data, birth_key: str = "birth_date"):
    normalized = {}
    normalized['id'] = data.get('id', '')
    normalized['gender'] = safe_lower(data.get('gender'))
    normalized['age'] = data.get('age', 0)
    normalized['education'] = safe_lower(data.get('education'))
    normalized['marital_status'] = safe_lower(data.get('marital_status'))

    econ = data.get('economic_status') or {}
    normalized['employment'] = safe_lower(econ.get('employment'))
    normalized['sector'] = safe_lower(econ.get('sector'))

    res = data.get('residence') or {}
    normalized['region'] = safe_lower(res.get('region'))
    normalized['nationality'] = safe_lower(res.get('nationality'))

    car_use = data.get('car_use') or {}
    owned_cars = car_use.get('owned_cars') or []
    primary_car = owned_cars[0] if owned_cars and isinstance(owned_cars[0], dict) else {}
    normalized['car_brand'] = safe_string(primary_car.get('brand'))

    important_raw = data.get("important_attributes", {}).get("important_attributes", "")
    important_attrs = normalize_important_attributes(important_raw)
    self_info = important_attrs.get('self', {})
    partner_info = important_attrs.get('partner', {})
    interests = important_attrs.get('interests', [])
    pets = important_attrs.get('pets', [])
    children = important_attrs.get('children', [])
    previous_passwords = important_attrs.get('previous_passwords', [])

    normalized['self_first_name'] = self_info.get('first_name', '')
    normalized['self_last_name'] = self_info.get('last_name', '')
    normalized[birth_key] = safe_string(important_attrs.get('birth_date'))
    normalized['partner_first_name'] = partner_info.get('first_name', '')
    normalized['partner_last_name'] = partner_info.get('last_name', '')
    normalized['children'] = children
    normalized['interests'] = interests
    normalized['pets'] = pets
    normalized['company'] = safe_string(important_attrs.get('company'))
    normalized['previous_passwords'] = previous_passwords

    if interests:
        normalized['favorite_hobby'] = interests[0]

    return normalized


def normalize_file(input_file: str | Path, output_file: str | Path, birth_key: str = "birth_date") -> None:
    input_path = Path(input_file)
    output_path = Path(output_file)

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    normalized_data = normalize_person_data(data, birth_key=birth_key)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(normalized_data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a person JSON file")
    parser.add_argument("input_file", help="Path to the JSON file to normalize")
    parser.add_argument("output_file", help="Path to save normalized JSON")
    parser.add_argument(
        "--birth-key",
        default="birth_date",
        choices=["birth_date", "birthday"],
        help="Output field name for the normalized birth date",
    )
    args = parser.parse_args()

    normalize_file(args.input_file, args.output_file, birth_key=args.birth_key)


if __name__ == "__main__":
    main()
