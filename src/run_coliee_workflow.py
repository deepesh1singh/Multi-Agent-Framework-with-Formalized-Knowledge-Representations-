import json
from pathlib import Path

from src.llm_client import call_llm

CLASSES_PROMPT = Path("prompts/coliee_classes_prompt.txt")
PREDICATES_PROMPT = Path("prompts/coliee_predicates_prompt.txt")
RULES_PROMPT = Path("prompts/coliee_rules_prompt.txt")
FEWSHOT_FILE = Path("prompts/sara_fewshot_examples_clean.json")

UNITS_FILE = Path("data/coliee/coliee_articles_sample.json")

RAW_BASE = Path("outputs/coliee/raw/workflow")
FINAL_DIR = Path("outputs/coliee/final")

CLASSES_OUT = FINAL_DIR / "coliee_classes_sample.json"
PREDICATES_OUT = FINAL_DIR / "coliee_predicates_sample.json"
RULES_OUT = FINAL_DIR / "coliee_rules_sample.json"
COMBINED_OUT = FINAL_DIR / "coliee_workflow_sample.json"


def get_id(item: dict):
    return item.get("unit_id") or item.get("_unit_id")


def extract_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        return text[start:end + 1]

    return text


def safe_json_parse(raw: str):
    return json.loads(extract_json(raw))


def call_with_retry(prompt: str, max_tokens: int = 4096, retries: int = 2):
    for attempt in range(1, retries + 2):
        raw = call_llm(prompt, temperature=0.1, max_tokens=max_tokens)

        if raw.strip():
            return raw

        print(f"Empty output, retrying... attempt {attempt}")

    return ""


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def build_classes_prompt(template: str, unit: dict) -> str:
    return (
        template
        .replace("{unit_id}", unit["unit_id"])
        .replace("{statute_text}", unit["statute_text"])
    )


def build_predicates_prompt(template: str, unit: dict, classes: list) -> str:
    return (
        template
        .replace("{unit_id}", unit["unit_id"])
        .replace("{statute_text}", unit["statute_text"])
        .replace("{classes}", json.dumps(classes, indent=2, ensure_ascii=False))
    )


def build_rules_prompt(
    template: str,
    unit: dict,
    predicates: list,
    fewshot_examples: str
) -> str:
    return (
        "Here are high-quality examples to follow:\n"
        + fewshot_examples
        + "\n\nNow process the new statute unit below.\n\n"
        + template
        .replace("{unit_id}", unit["unit_id"])
        .replace("{statute_text}", unit["statute_text"])
        .replace("{predicates}", json.dumps(predicates, indent=2, ensure_ascii=False))
    )


def run_classes(units, template):
    results = []
    raw_dir = RAW_BASE / "classes"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for i, unit in enumerate(units, start=1):
        unit_id = unit["unit_id"]

        print("=" * 80)
        print(f"[CLASSES] {i}/{len(units)} {unit_id}")
        print("=" * 80)

        prompt = build_classes_prompt(template, unit)
        raw = call_with_retry(prompt, max_tokens=2048)

        raw_path = raw_dir / f"{unit_id}_classes_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        print("Raw length:", len(raw))

        if not raw.strip():
            print("FAILED: empty output")
            continue

        try:
            parsed = safe_json_parse(raw)
            parsed["_unit_id"] = unit_id
            parsed["_raw_file"] = str(raw_path)
            results.append(parsed)
            print("JSON OK")
        except Exception as e:
            print("JSON FAILED:", e)
            print("Raw saved:", raw_path)

    return results


def run_predicates(units, template, classes_map):
    results = []
    raw_dir = RAW_BASE / "predicates"
    raw_dir.mkdir(parents=True, exist_ok=True)

    selected = [
        unit for unit in units
        if unit["unit_id"] in classes_map
        and isinstance(classes_map[unit["unit_id"]], list)
        and len(classes_map[unit["unit_id"]]) > 0
    ]

    for i, unit in enumerate(selected, start=1):
        unit_id = unit["unit_id"]

        print("=" * 80)
        print(f"[PREDICATES] {i}/{len(selected)} {unit_id}")
        print("=" * 80)

        prompt = build_predicates_prompt(
            template,
            unit,
            classes_map[unit_id]
        )

        raw = call_with_retry(prompt, max_tokens=4096)

        raw_path = raw_dir / f"{unit_id}_predicates_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        print("Raw length:", len(raw))

        if not raw.strip():
            print("FAILED: empty output")
            continue

        try:
            parsed = safe_json_parse(raw)
            parsed["_unit_id"] = unit_id
            parsed["_raw_file"] = str(raw_path)
            results.append(parsed)
            print("JSON OK")
        except Exception as e:
            print("JSON FAILED:", e)
            print("Raw saved:", raw_path)

    return results


def run_rules(units, template, predicates_map, fewshot_examples):
    results = []
    raw_dir = RAW_BASE / "rules"
    raw_dir.mkdir(parents=True, exist_ok=True)

    selected = [
        unit for unit in units
        if unit["unit_id"] in predicates_map
        and isinstance(predicates_map[unit["unit_id"]], list)
        and len(predicates_map[unit["unit_id"]]) > 0
    ]

    for i, unit in enumerate(selected, start=1):
        unit_id = unit["unit_id"]

        print("=" * 80)
        print(f"[RULES] {i}/{len(selected)} {unit_id}")
        print("=" * 80)

        prompt = build_rules_prompt(
            template,
            unit,
            predicates_map[unit_id],
            fewshot_examples
        )

        raw = call_with_retry(prompt, max_tokens=4096)

        raw_path = raw_dir / f"{unit_id}_rules_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        print("Raw length:", len(raw))

        if not raw.strip():
            print("FAILED: empty output")
            continue

        try:
            parsed = safe_json_parse(raw)
            parsed["_unit_id"] = unit_id
            parsed["_raw_file"] = str(raw_path)
            results.append(parsed)
            print("JSON OK")
        except Exception as e:
            print("JSON FAILED:", e)
            print("Raw saved:", raw_path)

    return results


def main():
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    units = json.loads(UNITS_FILE.read_text(encoding="utf-8"))

    classes_template = CLASSES_PROMPT.read_text(encoding="utf-8")
    predicates_template = PREDICATES_PROMPT.read_text(encoding="utf-8")
    rules_template = RULES_PROMPT.read_text(encoding="utf-8")
    fewshot_examples = FEWSHOT_FILE.read_text(encoding="utf-8")

    print(f"Total COLIEE units: {len(units)}")

    classes_results = run_classes(units, classes_template)
    save_json(CLASSES_OUT, classes_results)

    classes_map = {
        get_id(item): item.get("classes", [])
        for item in classes_results
        if get_id(item)
    }

    predicates_results = run_predicates(
        units,
        predicates_template,
        classes_map
    )
    save_json(PREDICATES_OUT, predicates_results)

    predicates_map = {
        get_id(item): item.get("predicates", [])
        for item in predicates_results
        if get_id(item)
    }

    rules_results = run_rules(
        units,
        rules_template,
        predicates_map,
        fewshot_examples
    )
    save_json(RULES_OUT, rules_results)

    rules_map = {
        get_id(item): item.get("rules", [])
        for item in rules_results
        if get_id(item)
    }

    combined = []

    for unit in units:
        unit_id = unit["unit_id"]

        combined.append({
            "unit_id": unit_id,
            "section_id": unit.get("section_id"),
            "unit_label": unit.get("unit_label"),
            "statute_text": unit["statute_text"],
            "classes": classes_map.get(unit_id, []),
            "predicates": predicates_map.get(unit_id, []),
            "rules": rules_map.get(unit_id, []),
        })

    save_json(COMBINED_OUT, combined)

    print("\nDONE")
    print(f"Classes:    {len(classes_results)} / {len(units)}")
    print(f"Predicates: {len(predicates_results)} / {len(units)}")
    print(f"Rules:      {len(rules_results)} / {len(units)}")
    print(f"Combined:   {COMBINED_OUT}")


if __name__ == "__main__":
    main()