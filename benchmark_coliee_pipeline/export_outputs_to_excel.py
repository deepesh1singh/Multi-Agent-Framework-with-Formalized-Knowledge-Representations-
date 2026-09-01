from pathlib import Path
import json
import re
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
V3 = BASE / "benchmark_coliee_v3"

UNITS_DIR = V3 / "final_outputs" / "units"
REPORT_DIR = V3 / "reports"
OUT_XLSX = V3 / "final_outputs" / "coliee_v3_outputs.xlsx"

summary_rows = []
variable_rows = []
predicate_rows = []
rule_rows = []
warning_rows = []


def parse_condition(cond):
    cond = cond.strip()

    # NOT ...
    if cond.startswith("NOT "):
        inner = cond[4:].strip()

        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1].strip()

        return {
            "NOT": parse_condition(inner)
        }

    # (A OR B OR C)
    if cond.startswith("(") and cond.endswith(")") and " OR " in cond:
        inner = cond[1:-1]

        parts = re.split(r"\s+OR\s+", inner)

        return {
            "OR": [
                parse_condition(p.strip())
                for p in parts
            ]
        }

    return {
        "atom": cond
    }


def build_condition_logic(conditions):
    nodes = [parse_condition(c) for c in conditions]

    if len(nodes) == 0:
        return {}

    if len(nodes) == 1:
        return nodes[0]

    return {
        "AND": nodes
    }


for path in sorted(UNITS_DIR.glob("*.json")):

    data = json.loads(path.read_text(encoding="utf-8"))

    unit_id = data.get("unit_id", "")

    summary_rows.append({
        "unit_id": unit_id,
        "article_number": data.get("article_number", ""),
        "unit_label": data.get("unit_label", ""),
        "title": data.get("title", ""),
        "variables_count": len(data.get("variables", [])),
        "predicates_count": len(data.get("predicates", [])),
        "rules_count": len(data.get("rules", [])),
        "warnings_count": len(data.get("warnings", [])),
        "statute_text": data.get("statute_text", "")
    })

    for v in data.get("variables", []):
        variable_rows.append({
            "unit_id": unit_id,
            **v
        })

    for p in data.get("predicates", []):

        predicate_rows.append({
            "unit_id": unit_id,
            "predicate_name": p.get("predicate_name", ""),
            "predicate_type": p.get("predicate_type", ""),
            "arguments": json.dumps(
                p.get("arguments", []),
                ensure_ascii=False
            ),
            "description": p.get("description", ""),
            "supporting_span": p.get("supporting_span", ""),
            "constants": json.dumps(
                p.get("constants", {}),
                ensure_ascii=False
            )
        })

    for r in data.get("rules", []):

        rule_rows.append({
            "unit_id": unit_id,
            "rule_id": r.get("rule_id", ""),

            "condition_logic": json.dumps(
                build_condition_logic(
                    r.get("conditions", [])
                ),
                indent=2,
                ensure_ascii=False
            ),

            "conclusion": r.get("conclusion", ""),

            "constants": json.dumps(
                r.get("constants", {}),
                ensure_ascii=False
            ),

            "supporting_span": r.get("supporting_span", ""),

            "explanation": r.get("explanation", "")
        })

    for w in data.get("warnings", []):

        warning_rows.append({
            "unit_id": unit_id,
            "warning": json.dumps(
                w,
                ensure_ascii=False
            )
        })

failed_path = REPORT_DIR / "failed_units.json"
failed_rows = []

if failed_path.exists():
    failed_rows = json.loads(
        failed_path.read_text(encoding="utf-8")
    )

with pd.ExcelWriter(
    OUT_XLSX,
    engine="openpyxl"
) as writer:

    pd.DataFrame(summary_rows).to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

    pd.DataFrame(variable_rows).to_excel(
        writer,
        sheet_name="Variables",
        index=False
    )

    pd.DataFrame(predicate_rows).to_excel(
        writer,
        sheet_name="Predicates",
        index=False
    )

    pd.DataFrame(rule_rows).to_excel(
        writer,
        sheet_name="Rules",
        index=False
    )

    pd.DataFrame(warning_rows).to_excel(
        writer,
        sheet_name="Warnings",
        index=False
    )

    pd.DataFrame(failed_rows).to_excel(
        writer,
        sheet_name="FailedUnits",
        index=False
    )

print("Export complete:")
print(OUT_XLSX)
print("Successful units:", len(summary_rows))
print("Failed units:", len(failed_rows))