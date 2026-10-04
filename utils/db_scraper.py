from SPARQLWrapper import SPARQLWrapper, JSON
import json
import time

ENDPOINT = "https://dbpedia.org/sparql"

sparql = SPARQLWrapper(ENDPOINT)
sparql.setReturnFormat(JSON)


# ------------------------------
# Safe query with retry + backoff
# ------------------------------
def run_query(query, retries=5):
    sparql.setQuery(query)

    for i in range(retries):
        try:
            return sparql.query().convert()["results"]["bindings"]
        except Exception as e:
            print(f"SPARQL error (attempt {i+1}):", e)
            sleep_time = 2 ** i
            print(f"Sleeping {sleep_time}s...")
            time.sleep(sleep_time)

    return []


# ------------------------------
# Find DBpedia entity from label
# ------------------------------
def find_entity(seed, lang="cs"):
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?entity ?label WHERE {{
        ?entity rdfs:label ?label .
        FILTER(lang(?label) = "{lang}")
        FILTER(CONTAINS(LCASE(?label), "{seed.lower()}"))
    }}
    LIMIT 5
    """

    results = run_query(query)

    if not results:
        return None

    # pick best match (shortest label = usually best)
    results.sort(key=lambda r: len(r["label"]["value"]))
    return results[0]["entity"]["value"]


# ------------------------------
# Get categories
# ------------------------------
def get_categories(entity):
    query = f"""
    PREFIX dct: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?cat WHERE {{
        <{entity}> dct:subject ?cat .
    }}
    """
    results = run_query(query)
    return [r["cat"]["value"] for r in results]


# ------------------------------
# Get types
# ------------------------------
def get_types(entity):
    query = f"""
    SELECT DISTINCT ?type WHERE {{
        <{entity}> a ?type .
    }}
    """
    results = run_query(query)
    return [r["type"]["value"] for r in results]


# ------------------------------
# Get label (Czech preferred)
# ------------------------------
def get_label(entity):
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?label WHERE {{
        <{entity}> rdfs:label ?label .
        FILTER(lang(?label)="cs")
    }}
    LIMIT 1
    """
    results = run_query(query)
    return results[0]["label"]["value"] if results else entity.split("/")[-1]


# ------------------------------
# Expand via category
# ------------------------------
def get_entities_from_category(category, lang="cs", limit=15):
    query = f"""
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?entity ?entityLabel WHERE {{
        ?entity dct:subject <{category}> .
        ?entity rdfs:label ?entityLabel .
        FILTER(lang(?entityLabel)="{lang}")
    }}
    LIMIT {limit}
    """
    results = run_query(query)
    return [(r["entity"]["value"], r["entityLabel"]["value"]) for r in results]


# ------------------------------
# Batch categories + types
# ------------------------------
def batch_get_categories_and_types(entities):
    if not entities:
        return {}

    entity_values = " ".join(f"<{e}>" for e in entities)

    query = f"""
    PREFIX dct: <http://purl.org/dc/terms/>

    SELECT ?entity ?cat ?type WHERE {{
        VALUES ?entity {{ {entity_values} }}
        OPTIONAL {{ ?entity dct:subject ?cat }}
        OPTIONAL {{ ?entity a ?type }}
    }}
    """

    results = run_query(query)

    data = {e: {"categories": set(), "types": set()} for e in entities}

    for r in results:
        e = r["entity"]["value"]

        if "cat" in r:
            data[e]["categories"].add(r["cat"]["value"])
        if "type" in r:
            data[e]["types"].add(r["type"]["value"])

    return data


# ------------------------------
# MAIN extraction
# ------------------------------
def extract(seed, lang="cs"):
    print(f"\n[EXTRACT] {seed}")

    entity = find_entity(seed, lang=lang)

    if not entity:
        print("⚠️ No entity found")
        return {}

    print("Entity:", entity)

    categories = get_categories(entity)
    types = get_types(entity)

    if not categories:
        print("⚠️ No categories found")
        return {}

    print(f"Categories: {len(categories)}, Types: {len(types)}")

    dataset = {}

    # seed entity
    dataset[entity] = {
        "label": get_label(entity),
        "categories": categories,
        "types": types
    }

    # expand via categories
    for cat in categories[:5]:  # limit explosion
        entities = get_entities_from_category(cat, lang=lang, limit=15)

        for e_uri, e_label in entities:
            if e_uri not in dataset:
                dataset[e_uri] = {
                    "label": e_label,
                    "categories": [],
                    "types": []
                }

        time.sleep(0.3)

    # ------------------------------
    # Batch fetch categories/types
    # ------------------------------
    print("Batch fetching categories/types...")

    batch_data = batch_get_categories_and_types(list(dataset.keys()))

    for e in dataset:
        dataset[e]["categories"] = list(batch_data[e]["categories"])
        dataset[e]["types"] = list(batch_data[e]["types"])

    return dataset


# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    seeds = [
        "Naruto_Uzumaki",
    ]

    full_data = {}

    for seed in seeds:
        data = extract(seed, lang="en")
        full_data.update(data)
        time.sleep(1)

    with open("dbpedia_entities.json", "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)

    print("\n✅ Saved dbpedia_entities.json")