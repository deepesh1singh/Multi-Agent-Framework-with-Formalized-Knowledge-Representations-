from pathlib import Path
import re

INPUT_FILE = Path("data/sara/sara_statute.txt")
OUTPUT_FILE = Path("data/sara/sara_statute_clean.txt")


def clean_text(text: str) -> str:
    # remove html breaks
    text = text.replace("<br>", "\n")

    # fix encoding artifacts
    text = text.replace("Â§", "§")
    text = text.replace("Â", "")

    # collapse excessive whitespace
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # trim lines
    lines = [line.strip() for line in text.splitlines()]

    return "\n".join(lines)


def main():
    raw_text = INPUT_FILE.read_text(encoding="utf-8", errors="ignore")

    cleaned = clean_text(raw_text)

    OUTPUT_FILE.write_text(cleaned, encoding="utf-8")

    print(f"Saved cleaned file to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()