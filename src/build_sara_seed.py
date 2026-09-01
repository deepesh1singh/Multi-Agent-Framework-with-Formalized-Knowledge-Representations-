import json
from pathlib import Path

from src.llm_client import call_llm

UNITS_FILE = Path("data/sara/sara_sections.json")
PROMPT_FILE = Path("prompts/sara_seed_prompt.txt")

RAW_DIR = Path("outputs/sara/raw/classes")
FINAL_FILE = Path("outputs/sara/final/sara_classes_seed.json")

SEED_UNIT_IDS = {
    "section_3301_full",
    "section_63_a",
    "section_7703_a",
    "section_68_a",
    "section_151_d",
}


def build_prompt(template: str, unit: dict) -> str:
    return (
        template
        .replace("{unit_id}", unit["unit_id"])
        .replace("{statute_text}", unit["statute_text"])
    )


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_FILE.parent.mkdir(parents=True, exist_ok=True)

    units = json.loads(UNITS_FILE.read_text(encoding="utf-8"))
    template = PROMPT_FILE.read_text(encoding="utf-8")

    selected = [u for u in units if u["unit_id"] in SEED_UNIT_IDS]

    print(f"Selected units: {len(selected)}")

    results = []

    for i, unit in enumerate(selected, start=1):
        unit_id = unit["unit_id"]

        print("=" * 80)
        print(f"Processing {i}/{len(selected)}: {unit_id}")
        print("=" * 80)

        prompt = build_prompt(template, unit)

        raw = call_llm(prompt, temperature=0.0, max_tokens=1200)

        raw_path = RAW_DIR / f"{unit_id}_classes_raw.txt"
        raw_path.write_text(raw, encoding="utf-8")

        try:
            parsed = json.loads(raw)
            parsed["_unit_id"] = unit_id
            parsed["_raw_file"] = str(raw_path)
            results.append(parsed)
            print("JSON OK")
        except json.JSONDecodeError as e:
            print(f"JSON FAILED: {e}")
            print(f"Raw saved to: {raw_path}")

    FINAL_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\nSaved: {FINAL_FILE}")
    print(f"Valid outputs: {len(results)}")


if __name__ == "__main__":
    main()