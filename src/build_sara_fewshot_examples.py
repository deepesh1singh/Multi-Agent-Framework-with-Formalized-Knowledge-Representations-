import json
from pathlib import Path

UNITS_FILE = Path("data/sara/sara_sections.json")
CLASSES_FILE = Path("outputs/sara/final/sara_classes_seed.json")
PREDICATES_FILE = Path("outputs/sara/final/sara_predicates_seed.json")
RULES_FILE = Path("outputs/sara/final/sara_rules_seed.json")

OUTPUT_FILE = Path("prompts/sara_fewshot_examples.json")


def main():
    units = json.loads(UNITS_FILE.read_text(encoding="utf-8"))
    classes = json.loads(CLASSES_FILE.read_text(encoding="utf-8"))
    predicates = json.loads(PREDICATES_FILE.read_text(encoding="utf-8"))
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))

    unit_map = {u["unit_id"]: u for u in units}
    class_map = {c["unit_id"]: c.get("classes", []) for c in classes}
    predicate_map = {p["unit_id"]: p.get("predicates", []) for p in predicates}
    rule_map = {r["unit_id"]: r.get("rules", []) for r in rules}

    common_ids = (
        set(class_map.keys())
        & set(predicate_map.keys())
        & set(rule_map.keys())
    )

    examples = []

    for unit_id in sorted(common_ids):
        examples.append({
            "unit_id": unit_id,
            "statute_text": unit_map[unit_id]["statute_text"],
            "classes": class_map[unit_id],
            "predicates": predicate_map[unit_id],
            "rules": rule_map[unit_id],
        })

    OUTPUT_FILE.write_text(
        json.dumps(examples, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Few-shot examples created: {len(examples)}")
    print(f"Saved to: {OUTPUT_FILE}")

    for ex in examples:
        print("-", ex["unit_id"])


if __name__ == "__main__":
    main()