import json
import pandas as pd
from pathlib import Path

INPUT_FILE = Path("outputs/sara/final/sara_workflow_full.json")
OUTPUT_FILE = Path("outputs/sara/final/sara_dataset.xlsx")


def to_json_string(value):
    if value is None:
        return ""

    return json.dumps(value, ensure_ascii=False)


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    summary_rows = []
    classes_rows = []
    predicates_rows = []
    rules_rows = []

    bad_classes = 0
    bad_predicates = 0
    bad_rules = 0

    for unit in data:
        unit_id = unit.get("unit_id", "")
        section_id = unit.get("section_id", "")
        unit_label = unit.get("unit_label", "")
        statute_text = unit.get("statute_text", "")

        classes = unit.get("classes", [])
        predicates = unit.get("predicates", [])
        rules = unit.get("rules", [])

        clean_classes_count = 0
        clean_predicates_count = 0
        clean_rules_count = 0

        for cls in classes:
            if not isinstance(cls, dict):
                bad_classes += 1
                continue

            clean_classes_count += 1

            classes_rows.append({
                "unit_id": unit_id,
                "section_id": section_id,
                "unit_label": unit_label,
                "class_name": cls.get("name", ""),
                "description": cls.get("description", ""),
                "supporting_span": cls.get("supporting_span", ""),
                "statute_text": statute_text
            })

        for pred in predicates:
            if not isinstance(pred, dict):
                bad_predicates += 1
                continue

            clean_predicates_count += 1

            predicates_rows.append({
                "unit_id": unit_id,
                "section_id": section_id,
                "unit_label": unit_label,
                "predicate_name": pred.get("name", ""),
                "predicate_type": pred.get("predicate_type", ""),
                "arguments": to_json_string(pred.get("arguments", [])),
                "description": pred.get("description", ""),
                "source_spans": to_json_string(pred.get("source_spans", [])),
                "constants": to_json_string(pred.get("constants", {})),
                "statute_text": statute_text
            })

        for rule in rules:
            if not isinstance(rule, dict):
                bad_rules += 1
                continue

            clean_rules_count += 1

            rules_rows.append({
                "unit_id": unit_id,
                "section_id": section_id,
                "unit_label": unit_label,
                "rule_id": rule.get("rule_id", ""),
                "predicates_used": to_json_string(rule.get("predicates_used", [])),
                "propositions": to_json_string(rule.get("propositions", {})),
                "logic": rule.get("logic", ""),
                "source_spans": to_json_string(rule.get("source_spans", [])),
                "constants": to_json_string(rule.get("constants", {})),
                "statute_text": statute_text
            })

        summary_rows.append({
            "unit_id": unit_id,
            "section_id": section_id,
            "unit_label": unit_label,
            "classes_count": clean_classes_count,
            "predicates_count": clean_predicates_count,
            "rules_count": clean_rules_count,
            "has_classes": clean_classes_count > 0,
            "has_predicates": clean_predicates_count > 0,
            "has_rules": clean_rules_count > 0,
            "statute_text": statute_text
        })

    summary_df = pd.DataFrame(summary_rows)
    classes_df = pd.DataFrame(classes_rows)
    predicates_df = pd.DataFrame(predicates_rows)
    rules_df = pd.DataFrame(rules_rows)

    stats_df = pd.DataFrame([
        {
            "total_units": len(data),
            "units_with_classes": int(summary_df["has_classes"].sum()),
            "units_with_predicates": int(summary_df["has_predicates"].sum()),
            "units_with_rules": int(summary_df["has_rules"].sum()),
            "total_classes": len(classes_rows),
            "total_predicates": len(predicates_rows),
            "total_rules": len(rules_rows),
            "bad_class_entries_skipped": bad_classes,
            "bad_predicate_entries_skipped": bad_predicates,
            "bad_rule_entries_skipped": bad_rules
        }
    ])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        stats_df.to_excel(writer, sheet_name="Stats", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        classes_df.to_excel(writer, sheet_name="Classes", index=False)
        predicates_df.to_excel(writer, sheet_name="Predicates", index=False)
        rules_df.to_excel(writer, sheet_name="Rules", index=False)

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Units: {len(data)}")
    print(f"Classes: {len(classes_rows)}")
    print(f"Predicates: {len(predicates_rows)}")
    print(f"Rules: {len(rules_rows)}")
    print(f"Bad classes skipped: {bad_classes}")
    print(f"Bad predicates skipped: {bad_predicates}")
    print(f"Bad rules skipped: {bad_rules}")


if __name__ == "__main__":
    main()