from pathlib import Path
import re
import json

INPUT_FILE = Path("data/sara/sara_statute_clean.txt")
OUTPUT_FILE = Path("data/sara/sara_sections.json")

SECTION_PATTERN = re.compile(
    r"(?=^§\s*(\d+[A-Za-z0-9\-]*)\.\s*)",
    re.MULTILINE
)

# Split ONLY on top-level subsections:
# (a) Title
# (b) Title
# NOT on (i), (ii), (iii), (A), (B), etc.
SUBSECTION_PATTERN = re.compile(
    r"(?=^\(([a-z])\)\s+[A-Z])",
    re.MULTILINE
)


def clean_id(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def split_sections(text: str):
    parts = SECTION_PATTERN.split(text)

    sections = []

    i = 1
    while i < len(parts):
        section_number = parts[i].strip()
        section_text = parts[i + 1].strip()

        first_line = section_text.splitlines()[0].strip()

        title_match = re.match(
            r"^§\s*\d+[A-Za-z0-9\-]*\.\s*(.*)$",
            first_line
        )

        title = title_match.group(1).strip() if title_match else ""

        sections.append({
            "section_number": section_number,
            "section_id": f"section_{clean_id(section_number)}",
            "title": title,
            "statute_text": section_text
        })

        i += 2

    return sections


def split_subsections(section):
    text = section["statute_text"]

    lines = text.splitlines()

    header = lines[0].strip()
    body = "\n".join(lines[1:]).strip()

    matches = list(SUBSECTION_PATTERN.finditer(body))

    # No (a), (b), (c) structure
    if not matches:
        return [{
            "section_id": section["section_id"],
            "section_number": section["section_number"],
            "unit_id": section["section_id"] + "_full",
            "unit_label": section["section_number"],
            "title": section["title"],
            "statute_text": text
        }]

    units = []

    for idx, match in enumerate(matches):
        start = match.start()

        if idx + 1 < len(matches):
            end = matches[idx + 1].start()
        else:
            end = len(body)

        subsection_text = body[start:end].strip()

        letter_match = re.match(
            r"^\(([a-z])\)",
            subsection_text
        )

        if not letter_match:
            continue

        subsection_letter = letter_match.group(1)

        unit_id = (
            f"{section['section_id']}_{subsection_letter}"
        )

        unit_label = (
            f"{section['section_number']}({subsection_letter})"
        )

        units.append({
            "section_id": section["section_id"],
            "section_number": section["section_number"],
            "unit_id": unit_id,
            "unit_label": unit_label,
            "title": section["title"],
            "statute_text": header + "\n\n" + subsection_text
        })

    return units


def main():
    text = INPUT_FILE.read_text(
        encoding="utf-8"
    )

    sections = split_sections(text)

    all_units = []

    for section in sections:
        units = split_subsections(section)
        all_units.extend(units)

    OUTPUT_FILE.write_text(
        json.dumps(
            all_units,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(f"Sections found: {len(sections)}")
    print(f"Units found: {len(all_units)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nFirst 20 units:\n")

    for unit in all_units[:20]:
        print(
            f"{unit['unit_id']} "
            f"({unit['unit_label']})"
        )


if __name__ == "__main__":
    main()