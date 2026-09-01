import json
from pathlib import Path

from src.llm_client import call_llm

INPUT_FILE = Path("outputs/sara/final/sara_workflow_full.json")
PROMPT_FILE = Path("prompts/sara_rules_repair_prompt.txt")

RAW_DIR = Path("outputs/sara/raw/rules_repair")
FINAL_DIR = Path("outputs/sara/final")

REPAIRED_RULES_FILE = FINAL_DIR / "sara_rules_repaired.json"
REPAIRED_WORKFLOW_FILE = FINAL_DIR / "sara_workflow_repaired.json"


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


def build_prompt(template: str, unit: dict) -> str:
    return (
        template
        .replace("{unit_id}", unit["unit_id"])
        .replace("{statute_text}", unit.get("statute_text", ""))
        .replace(
            "{predicates}",
            json.dumps(unit.get("predicates", []), indent=2, ensure_ascii=False)
        )
    )


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    template = PROMPT_FILE.read_text(encoding="utf-8")

    repaired_rules_outputs = []
    repaired_workflow = []

    print(f"Total units: {len(data)}")

    for i, unit in enumerate(data, start=1):
        unit_id = unit["unit_id"]

        print("=" * 80)
        print(f"[REPAIR RULES] {i}/{len(data)} {unit_id}")
        print("=" * 80)

        predicates = unit.get("predicates", [])

        if not predicates:
            print("Skipping: no predicates")
            repaired_workflow.append(unit)
            continue

        prompt = build_prompt(template, unit)

        raw = call_with_retry(prompt, max_tokens=4096)

        raw_path = RAW_DIR / f"{unit_id}_rules_repair_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        print("Raw length:", len(raw))

        if not raw.strip():
            print("FAILED: empty output")
            repaired_workflow.append(unit)
            continue

        try:
            parsed = safe_json_parse(raw)

            new_predicates = parsed.get("new_predicates", [])
            repaired_rules = parsed.get("rules", [])

            if isinstance(new_predicates, list):
                unit["predicates"].extend(new_predicates)

            if isinstance(repaired_rules, list):
                unit["rules"] = repaired_rules

            parsed["_unit_id"] = unit_id
            parsed["_raw_file"] = str(raw_path)
            repaired_rules_outputs.append(parsed)

            print("JSON OK")
            print(f"New predicates: {len(new_predicates)}")
            print(f"Rules: {len(repaired_rules)}")

        except Exception as e:
            print("JSON FAILED:", e)
            print("Keeping old rules.")
            print("Raw saved:", raw_path)

        repaired_workflow.append(unit)

    REPAIRED_RULES_FILE.write_text(
        json.dumps(repaired_rules_outputs, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    REPAIRED_WORKFLOW_FILE.write_text(
        json.dumps(repaired_workflow, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nDONE")
    print(f"Saved repaired rules: {REPAIRED_RULES_FILE}")
    print(f"Saved repaired workflow: {REPAIRED_WORKFLOW_FILE}")
    print(f"Repaired units: {len(repaired_rules_outputs)} / {len(data)}")


if __name__ == "__main__":
    main()