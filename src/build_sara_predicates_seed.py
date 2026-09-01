import json
from pathlib import Path

from src.llm_client import call_llm

UNITS_FILE = Path("data/sara/sara_sections.json")
PROMPT_FILE = Path("prompts/sara_predicates_prompt.txt")

RAW_DIR = Path("outputs/sara/raw/predicates")
DEBUG_DIR = Path("outputs/sara/debug")
FINAL_FILE = Path("outputs/sara/final/sara_predicates_seed.json")


def extract_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        return text[start:end + 1]

    return text


def build_prompt(template: str, unit: dict) -> str:
    return (
        template
        .replace("{unit_id}", unit["unit_id"])
        .replace("{statute_text}", unit["statute_text"])
    )


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_FILE.parent.mkdir(parents=True, exist_ok=True)

    units = json.loads(UNITS_FILE.read_text(encoding="utf-8"))
    template = PROMPT_FILE.read_text(encoding="utf-8")

    selected = [
        unit for unit in units
        if unit["unit_id"] in {
            "section_3301_full",
            "section_63_a",
            "section_7703_a",
            "section_68_a",
        }
    ]

    results = []

    for unit in selected:
        unit_id = unit["unit_id"]
        print(f"Processing: {unit_id}")

        prompt = build_prompt(template, unit)

        (DEBUG_DIR / "last_predicate_prompt.txt").write_text(prompt, encoding="utf-8")

        raw = call_llm(prompt, temperature=0.1, max_tokens=10000)

        raw_path = RAW_DIR / f"{unit_id}_predicates_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        print("Raw length:", len(raw))
        print("Raw preview:", repr(raw[:300]))

        if not raw.strip():
            print("Still empty. Raw saved.")
            continue

        try:
            parsed = json.loads(extract_json(raw))
            parsed["_unit_id"] = unit_id
            parsed["_raw_file"] = str(raw_path)
            results.append(parsed)
            print("JSON OK")
        except Exception as e:
            print("JSON FAILED:", e)
            print("Raw saved to:", raw_path)

    FINAL_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("Saved:", FINAL_FILE)
    print("Valid outputs:", len(results))


if __name__ == "__main__":
    main()