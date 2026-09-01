import re
import json
from pathlib import Path

INPUT_FILE = Path("data/coliee/coliee_statute.txt")
OUTPUT_FILE = Path("data/coliee/coliee_articles.json")


ARTICLE_PATTERN = re.compile(
    r"(?=^Article\s+(\d+(?:-\d+)?)\s+)",
    re.MULTILINE
)


def clean_id(article_no: str) -> str:
    return "article_" + article_no.replace("-", "_")


def split_articles(text: str):
    parts = ARTICLE_PATTERN.split(text)

    articles = []

    i = 1
    while i < len(parts):
        article_no = parts[i].strip()
        article_text = parts[i + 1].strip()

        full_text = f"Article {article_no} {article_text}".strip()

        first_line = full_text.splitlines()[0].strip()

        articles.append({
            "unit_id": clean_id(article_no),
            "article_number": article_no,
            "unit_label": f"Article {article_no}",
            "title": first_line,
            "statute_text": full_text
        })

        i += 2

    return articles


def main():
    text = INPUT_FILE.read_text(encoding="utf-8", errors="ignore")

    articles = split_articles(text)

    OUTPUT_FILE.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Articles found: {len(articles)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nFirst 20 articles:")
    for article in articles[:20]:
        print(article["unit_id"], "|", article["unit_label"])


if __name__ == "__main__":
    main()