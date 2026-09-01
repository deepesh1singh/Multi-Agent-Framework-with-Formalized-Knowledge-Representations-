from pathlib import Path
import json
import pandas as pd
import re

BASE = Path(__file__).resolve().parents[1]
V3 = BASE / "benchmark_v3"

UNITS_DIR = V3 / "final_outputs" / "units"
REPORT_DIR = V3 / "reports"
OUT_DIR = V3 / "final_outputs"

OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FAILED_PATH = REPORT_DIR / "failed_units.json"
EXCEL_PATH = OUT_DIR / "sara_benchmark_v3_baseline.xlsx"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def make_readable_conditions(conditions, constants):
    text = " AND ".join(str(c) for c in conditions)

    if not isinstance(constants, dict):
        return text

    if "threshold" in constants:
        text += f" AND income <= {constants['threshold']}"

    if "threshold_low" in constants:
        text += f" AND income > {constants['threshold_low']}"

    if "threshold_high" in constants:
        text += f" AND income <= {constants['threshold_high']}"

    if "lower_income_limit" in constants:
        text += f" AND income > {constants['lower_income_limit']}"

    if "upper_income_limit" in constants:
        text += f" AND income <= {constants['upper_income_limit']}"

    if "rate_1" in constants and "threshold_1" in constants:
        text += f" AND tiered tax brackets apply"

    return text


def make_readable_conclusion(conclusion, constants):
    if not isinstance(constants, dict):
        return conclusion

    if "rate" in constants and "base_amount" in constants and "threshold_low" in constants:
        return (
            f"TaxAmount = {constants['base_amount']} + "
            f"({constants['rate']} * (income - {constants['threshold_low']}))"
        )

    if "rate" in constants and "base_tax" in constants and "threshold_1" in constants:
        return (
            f"TaxAmount = {constants['base_tax']} + "
            f"({constants['rate']} * (income - {constants['threshold_1']}))"
        )

    if "rate" in constants and "threshold" in constants:
        return f"TaxAmount = {constants['rate']} * income"

    if "rate" in constants:
        return f"{conclusion} with rate = {constants['rate']}"

    if "rate_1" in constants:
        rates = [
            str(v)
            for k, v in constants.items()
            if str(k).startswith("rate")
        ]
        thresholds = [
            str(v)
            for k, v in constants.items()
            if "threshold" in str(k)
        ]
        return (
            f"{conclusion} using tiered rates "
            f"({', '.join(rates)}) over thresholds ({', '.join(thresholds)})"
        )

    return conclusion


ARG_MAP = {
    "T": "Taxpayer",
    "M": "MarriedIndividual",
    "S": "SurvivingSpouse",
    "I": "TaxableIncome",
    "D": "Dependent",
    "P": "Person",
    "E": "Employer",
    "W": "Wages",
    "Y": "TaxableYear",
    "False": "",
    "True": "",
    "decimal": "Amount",
    "amount": "Amount",
    "income": "Income",
}


def clean_expr(expr):
    expr = str(expr)

    for old, new in ARG_MAP.items():
        expr = re.sub(rf"\b{re.escape(old)}\b", new, expr)

    expr = expr.replace("(, ", "(").replace(", )", ")")
    expr = expr.replace("( )", "()").replace("()", "")
    expr = re.sub(r",\s*,", ",", expr)
    expr = re.sub(r"\(\s*,\s*", "(", expr)
    expr = re.sub(r",\s*\)", ")", expr)

    return expr.strip()


def infer_formula(conclusion, constants):
    if not isinstance(constants, dict):
        return clean_expr(conclusion)

    rate = constants.get("rate") or constants.get("tax_rate")
    base = constants.get("base_amount") or constants.get("base_tax")
    low = (
        constants.get("threshold_low")
        or constants.get("lower_income_limit")
        or constants.get("threshold_1")
    )

    if rate is not None and base is not None and low is not None:
        return f"TaxAmount = {base} + {rate} × (TaxableIncome - {low})"

    if rate is not None:
        return f"TaxAmount = {rate} × TaxableIncome"

    if "rate_1" in constants:
        return "TaxAmount = tiered tax formula using listed rates and thresholds"

    return clean_expr(conclusion)


def infer_rule_type(conclusion, constants):
    text = str(conclusion).lower()

    if constants and any("rate" in str(k).lower() or "threshold" in str(k).lower() for k in constants):
        return "calculation"
    if "exclusion" in text or "exception" in text or "not_" in text:
        return "exception"
    if "definition" in text or "defined" in text:
        return "definition"
    if "dependent" in text or "status" in text or "eligible" in text:
        return "status"
    return "general"


def infer_review_status(conditions, conclusion):
    condition_texts = [clean_expr(c) for c in conditions]
    conclusion_text = clean_expr(conclusion)

    if conclusion_text in condition_texts:
        return "REVIEW: tautological"

    bad = ["P_S_R_E_D_I_C_A_T_E", "UNKNOWN", "undefined", "False"]
    if any(b.lower() in str(conclusion).lower() for b in bad):
        return "REVIEW: unclear arguments"

    return "OK"


def main():
    unit_files = sorted(UNITS_DIR.glob("*.json"))

    summary_rows = []
    variable_rows = []
    predicate_rows = []
    rule_rows = []
    warning_rows = []

    for path in unit_files:
        unit = load_json(path)

        unit_id = unit.get("unit_id", "")
        section_id = unit.get("section_id", "")
        unit_label = unit.get("unit_label", "")
        statute_text = unit.get("statute_text", "")

        variables = unit.get("variables", [])
        predicates = unit.get("predicates", [])
        rules = unit.get("rules", [])
        warnings = unit.get("warnings", [])

        summary_rows.append({
            "unit_id": unit_id,
            "section_id": section_id,
            "unit_label": unit_label,
            "variables_count": len(variables),
            "predicates_count": len(predicates),
            "rules_count": len(rules),
            "warnings_count": len(warnings),
            "statute_text": statute_text,
        })

        for idx, v in enumerate(variables, start=1):
            variable_rows.append({
                "unit_id": unit_id,
                "variable_index": idx,
                "variable_name": v.get("variable_name", ""),
                "description": v.get("description", ""),
                "supporting_span": v.get("supporting_span", ""),
            })

        for idx, p in enumerate(predicates, start=1):
            predicate_rows.append({
                "unit_id": unit_id,
                "predicate_index": idx,
                "predicate_name": p.get("predicate_name", ""),
                "predicate_type": p.get("predicate_type", ""),
                "arguments": json.dumps(p.get("arguments", []), ensure_ascii=False),
                "description": p.get("description", ""),
                "supporting_span": p.get("supporting_span", ""),
                "constants": json.dumps(p.get("constants", {}), ensure_ascii=False),
            })

        for idx, r in enumerate(rules, start=1):
            conditions = r.get("conditions", [])
            constants = r.get("constants", {})

            condition_text = " AND ".join(clean_expr(c) for c in conditions)
            conclusion_text = infer_formula(r.get("conclusion", ""), constants)

            rule_rows.append({
                "unit_id": unit_id,
                "rule_id": r.get("rule_id", ""),
                "rule_type": infer_rule_type(r.get("conclusion", ""), constants),
                "condition": condition_text,
                "conclusion": conclusion_text,
                "constants": json.dumps(constants, ensure_ascii=False),
                "supporting_span": r.get("supporting_span", ""),
                "review_status": infer_review_status(conditions, r.get("conclusion", "")),
                "explanation": r.get("explanation", ""),
            })

        for idx, w in enumerate(warnings, start=1):
            warning_rows.append({
                "unit_id": unit_id,
                "warning_index": idx,
                "issue": w.get("issue", ""),
                "stage": w.get("stage", ""),
                "rule_id": w.get("rule_id", ""),
                "warning_json": json.dumps(w, ensure_ascii=False),
            })

    failed_rows = []

    if FAILED_PATH.exists():
        failed = load_json(FAILED_PATH)

        for item in failed:
            failed_rows.append({
                "unit_id": item.get("unit_id", ""),
                "error": item.get("error", ""),
            })

    stats_rows = [{
        "total_successful_units": len(summary_rows),
        "total_failed_units": len(failed_rows),
        "total_variables": len(variable_rows),
        "total_predicates": len(predicate_rows),
        "total_rules": len(rule_rows),
        "total_warnings": len(warning_rows),
        "avg_variables_per_unit": round(len(variable_rows) / len(summary_rows), 2) if summary_rows else 0,
        "avg_predicates_per_unit": round(len(predicate_rows) / len(summary_rows), 2) if summary_rows else 0,
        "avg_rules_per_unit": round(len(rule_rows) / len(summary_rows), 2) if summary_rows else 0,
    }]

    sheets = {
        "Stats": pd.DataFrame(stats_rows),
        "Summary": pd.DataFrame(summary_rows),
        "Variables": pd.DataFrame(variable_rows),
        "Predicates": pd.DataFrame(predicate_rows),
        "Rules": pd.DataFrame(rule_rows),
        "Warnings": pd.DataFrame(warning_rows),
        "FailedUnits": pd.DataFrame(failed_rows),
    }

    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            ws = writer.sheets[sheet_name]
            ws.freeze_panes = "A2"

            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter

                for cell in col:
                    value = "" if cell.value is None else str(cell.value)
                    max_len = max(max_len, min(len(value), 80))

                ws.column_dimensions[col_letter].width = max(12, min(max_len + 2, 60))

    print("Export complete.")
    print("Units exported:", len(summary_rows))
    print("Failed units:", len(failed_rows))
    print("Excel saved at:", EXCEL_PATH)


if __name__ == "__main__":
    main()