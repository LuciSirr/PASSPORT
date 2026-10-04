from __future__ import annotations

import unicodedata
from collections import Counter
from datetime import datetime
from statistics import mean


def _normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text).lower())
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return "".join(ch for ch in stripped if ch.isalnum())


def _non_empty_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _collect_text_variants(value) -> set[str]:
    variants: set[str] = set()

    if isinstance(value, list):
        for item in value:
            variants.update(_collect_text_variants(item))
        return variants

    text = _non_empty_text(value)
    if not text:
        return variants

    normalized = _normalize_for_match(text)
    if normalized:
        variants.add(normalized)

    words = [part for part in text.replace("-", " ").replace("_", " ").split() if part]
    if len(words) > 1:
        joined = _normalize_for_match("".join(words))
        if joined:
            variants.add(joined)
        for word in words:
            normalized_word = _normalize_for_match(word)
            if len(normalized_word) >= 3:
                variants.add(normalized_word)

    return variants


def _birth_components(profile: dict) -> dict[str, list[str]]:
    birth_date = _non_empty_text(profile.get("birth_date")) or _non_empty_text(profile.get("birthday"))
    if not birth_date:
        return {}
    try:
        parsed = datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        return {}

    return {
        "birthdate": [
            parsed.strftime("%Y%m%d"),
            parsed.strftime("%d%m%Y"),
            parsed.strftime("%m%d%Y"),
            parsed.strftime("%Y%d%m"),
            parsed.strftime("%d%Y%m"),
            parsed.strftime("%m%Y%d"),
        ],
        "birth_year": [parsed.strftime("%Y")],
        "birth_month": [
            parsed.strftime("%m"),
            str(parsed.month),
            parsed.strftime("%B"),
            parsed.strftime("%b"),
        ],
        "birth_day": [
            parsed.strftime("%d"),
            str(parsed.day),
        ],
    }


def build_personal_token_catalog(profile: dict) -> dict[str, list[str]]:
    catalog: dict[str, set[str]] = {
        "self_first_name": set(),
        "self_last_name": set(),
        "partner_first_name": set(),
        "partner_last_name": set(),
        "child_first_name": set(),
        "child_last_name": set(),
        "pet_name": set(),
        "pet_type": set(),
        "interest": set(),
        "favorite_hobby": set(),
        "region": set(),
        "nationality": set(),
        "company": set(),
        "car_brand": set(),
        "age": set(),
        "birthdate": set(),
        "birth_year": set(),
        "birth_month": set(),
        "birth_day": set(),
    }

    scalar_fields = [
        "self_first_name",
        "self_last_name",
        "partner_first_name",
        "partner_last_name",
        "favorite_hobby",
        "region",
        "nationality",
        "company",
        "car_brand",
    ]
    for field in scalar_fields:
        catalog[field].update(_collect_text_variants(profile.get(field)))

    for interest in profile.get("interests", []) if isinstance(profile.get("interests"), list) else []:
        catalog["interest"].update(_collect_text_variants(interest))

    children = profile.get("children", []) if isinstance(profile.get("children"), list) else []
    for child in children:
        if not isinstance(child, dict):
            continue
        catalog["child_first_name"].update(_collect_text_variants(child.get("first_name")))
        catalog["child_last_name"].update(_collect_text_variants(child.get("last_name")))

    pets = profile.get("pets", []) if isinstance(profile.get("pets"), list) else []
    for pet in pets:
        if not isinstance(pet, dict):
            continue
        catalog["pet_name"].update(_collect_text_variants(pet.get("pet_name")))
        catalog["pet_type"].update(_collect_text_variants(pet.get("pet_type")))

    age = profile.get("age")
    if age is not None:
        catalog["age"].update(_collect_text_variants(age))

    for field, values in _birth_components(profile).items():
        for value in values:
            catalog[field].update(_collect_text_variants(value))

    return {
        field: sorted(values, key=lambda item: (-len(item), item))
        for field, values in catalog.items()
        if values
    }


class PersonalDataMatcher:
    def __init__(self, profile: dict):
        self.catalog = build_personal_token_catalog(profile)
        self.tokens: list[tuple[str, str]] = []
        for field, values in self.catalog.items():
            for value in values:
                self.tokens.append((field, value))
        self.tokens.sort(key=lambda item: (-len(item[1]), item[0], item[1]))

    def analyze_password(self, password: str) -> dict:
        normalized_password = _normalize_for_match(password)
        if not normalized_password:
            return {
                "has_personal_data": False,
                "personal_char_ratio": 0.0,
                "matched_fields": [],
            }

        covered = [False] * len(normalized_password)
        matched_fields: set[str] = set()

        for field, token in self.tokens:
            start = normalized_password.find(token)
            if start == -1:
                continue
            matched_fields.add(field)
            search_from = start
            while search_from != -1:
                end = search_from + len(token)
                for index in range(search_from, end):
                    covered[index] = True
                search_from = normalized_password.find(token, search_from + 1)

        covered_count = sum(covered)
        return {
            "has_personal_data": bool(matched_fields),
            "personal_char_ratio": covered_count / len(normalized_password),
            "matched_fields": sorted(matched_fields),
        }


def summarize_personal_data_usage(results: list[dict], top_n: int) -> dict:
    total = len(results)
    passwords_with_personal_data = sum(1 for item in results if item["has_personal_data"])
    field_counts = Counter()
    for item in results:
        for field in item["matched_fields"]:
            field_counts[field] += 1

    ratios = [item["personal_char_ratio"] for item in results]

    return {
        "passwords_with_personal_data": passwords_with_personal_data,
        "share_of_passwords_with_personal_data": round(
            passwords_with_personal_data / total, 4
        ) if total else 0.0,
        "average_personal_char_ratio": round(mean(ratios), 4) if ratios else 0.0,
        "average_personal_char_ratio_when_present": round(
            mean([item["personal_char_ratio"] for item in results if item["has_personal_data"]]),
            4,
        ) if passwords_with_personal_data else 0.0,
        "top_personal_fields": [
            {"value": value, "count": count}
            for value, count in field_counts.most_common(top_n)
        ],
    }
