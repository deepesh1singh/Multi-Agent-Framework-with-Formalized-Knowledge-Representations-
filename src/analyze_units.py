import json
from pathlib import Path

INPUT_FILE = Path("data/sara/sara_sections.json")

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def main():
    units = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    print(f"Total units: {len(units)}")
    print("\nUnit sizes:\n")

    for unit in units:
        text = unit["statute_text"]
        chars = len(text)
        tokens = estimate_tokens(text)

        print(f"{unit['unit_id']:20} chars={chars:5} est_tokens={tokens:5}")

if __name__ == "__main__":
    main()