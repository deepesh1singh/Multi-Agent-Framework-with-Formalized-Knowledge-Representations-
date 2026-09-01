import json
from pathlib import Path

articles = json.loads(
    Path("data/coliee/coliee_articles.json")
    .read_text(encoding="utf-8")
)

sample = articles[:5]

Path(
    "data/coliee/coliee_articles_sample.json"
).write_text(
    json.dumps(sample, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("Saved sample:", len(sample))