from pathlib import Path
import json
import sys
import re
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
INPUT_JSON = BASE / "data" / "coliee" / "coliee_articles.json"


V3 = BASE / "benchmark_coliee_v3"
PROMPT_DIR = V3 / "prompts"
RAW_DIR = V3 / "raw_outputs"
OUT_DIR = V3 / "final_outputs"
REPORT_DIR = V3 / "reports"

for p in [
    RAW_DIR / "variables",
    RAW_DIR / "predicates",
    RAW_DIR / "rules",
    OUT_DIR / "units",
    REPORT_DIR,
]:
    p.mkdir(parents=True, exist_ok=True)

sys.path.append(str(BASE / "src"))

try:
    from llm_client import call_llm
except ImportError:
    try:
        from llm_client import generate as call_llm
    except ImportError:
        from llm_client import query_llm as call_llm


TEST_UNITS = None

def read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def render_prompt(template: str, **kwargs) -> str:
    for key, value in kwargs.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def extract_json(text: str):
    text = str(text).strip()
    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")

    text = text[start:]

    try:
        return json.loads(text)
    except Exception:
        pass

    for end in range(len(text) - 1, 0, -1):
        if text[end] == "}":
            candidate = text[: end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue

    raise ValueError("Could not parse JSON")

def is_valid_logic(logic):
    if not isinstance(logic, dict):
        return False

    keys = set(logic.keys())

    if "atom" in logic:
        return isinstance(logic["atom"], str) and bool(logic["atom"].strip())

    if "AND" in logic:
        return (
            isinstance(logic["AND"], list)
            and len(logic["AND"]) > 0
            and all(is_valid_logic(x) for x in logic["AND"])
        )

    if "OR" in logic:
        return (
            isinstance(logic["OR"], list)
            and len(logic["OR"]) > 0
            and all(is_valid_logic(x) for x in logic["OR"])
        )

    if "NOT" in logic:
        return is_valid_logic(logic["NOT"])

    return False

def is_valid_symbol_name(name: str):
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(name).strip()))

def validate_stage_json(stage: str, parsed: dict):
    if not isinstance(parsed, dict):
        raise ValueError(f"{stage}: output is not JSON object")

    if stage == "variables":
        key = "variables"
        required = {"variable_name", "description", "supporting_span"}

    elif stage == "predicates":
        key = "predicates"
        required = {
            "predicate_name",
            "predicate_type",
            "arguments",
            "description",
            "supporting_span",
            "constants",
        }

    elif stage == "rules":
        key = "rules"
        required = {
            "rule_id",
            "conditions",
            "conclusion",
            "constants",
            "supporting_span",
            "explanation",
        }

    else:
        return parsed

    items = parsed.get(key, [])

    if not isinstance(items, list):
        raise ValueError(f"{stage}: {key} is not a list")

    cleaned = []

    for item in items:
        if not isinstance(item, dict):
            continue

        if not required.issubset(set(item.keys())):
            continue

        if stage == "variables":
            if not is_valid_symbol_name(item.get("variable_name", "")):
                continue

        if stage == "predicates":
            if not is_valid_symbol_name(item.get("predicate_name", "")):
                continue

            if not isinstance(item.get("arguments"), list):
                continue

            bad_arg = False
            for arg in item.get("arguments", []):
                if arg not in ["integer", "decimal", "date", "string", "boolean"] and not is_valid_symbol_name(arg):
                    bad_arg = True

            if bad_arg:
                continue

            if item.get("predicate_type") not in [
                "status",
                "relationship",
                "datatype",
                "definition",
                "cross_reference",
                "exception",
            ]:
                continue

        if stage == "rules":
            if not isinstance(item.get("conditions"), list):
                continue

            if not item.get("conclusion"):
                continue

            item["conditions"] = [
                str(c).strip()
                for c in item["conditions"]
                if str(c).strip()
            ]

            item["conclusion"] = str(item["conclusion"]).strip()

            if not item["conditions"]:
                continue

            if item["conclusion"] in item["conditions"]:
                continue

            bad_text = json.dumps(item).lower()
            if "per_son" in bad_text or "undersigned by" in bad_text:
                continue

        cleaned.append(item)

    parsed[key] = cleaned
    return parsed

def save_raw(stage: str, name: str, raw: str):
    path = RAW_DIR / stage / f"{name}_{stage}_raw.txt"
    path.write_text(str(raw), encoding="utf-8")


def repair_json(stage: str, unit_id: str, raw: str):
    repair_prompt = f"""
Return ONLY valid JSON.
No markdown.
No explanation.
No comments.
No reasoning.

Repair the broken output into valid JSON for stage "{stage}".

For variables:
{{
  "unit_id": "{unit_id}",
  "variables": [
    {{
      "variable_name": "",
      "description": "",
      "supporting_span": ""
    }}
  ]
}}

For predicates:
{{
  "unit_id": "{unit_id}",
  "predicates": [
    {{
      "predicate_name": "",
      "predicate_type": "status|relationship|datatype|definition|cross_reference|exception",
      "arguments": [],
      "description": "",
      "supporting_span": "",
      "constants": {{}}
    }}
  ]
}}

For rules:
{{
  "unit_id": "{unit_id}",
  "rules": [
    {{
      "rule_id": "{unit_id}_rule_1",
      "conditions": [],
      "conclusion": "",
      "constants": {{}},
      "supporting_span": "",
      "explanation": ""
    }}
  ]
}}
Broken output:
{raw}
"""
    fixed = call_llm(repair_prompt)
    save_raw(stage, f"{unit_id}_repair", fixed)
    parsed = extract_json(fixed)
    return validate_stage_json(stage, parsed)


def call_stage(stage: str, unit_id: str, prompt: str, max_attempts: int = 2):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        print(f"Calling LLM for {stage}... attempt {attempt}")
        raw = call_llm(prompt)
        save_raw(stage, f"{unit_id}_attempt{attempt}", raw)

        try:
            parsed = extract_json(raw)
            return validate_stage_json(stage, parsed)
        except Exception as e:
            last_error = e
            print(f"Parse/validation failed for {unit_id}/{stage}, trying repair...")
            try:
                return repair_json(stage, unit_id, raw)
            except Exception as repair_error:
                last_error = repair_error
                print(f"Repair failed for {unit_id}/{stage}: {repair_error}")

    raise ValueError(f"Failed {stage} for {unit_id}: {last_error}")


def extract_predicate_names(expr: str):
    return re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", str(expr))

def logic_to_strings(logic):
    """
    Converts nested condition_logic into a flat list of atom strings.
    Used only for validation, not for final output.
    """
    atoms = []

    if isinstance(logic, str):
        atoms.extend(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*\([^()]*\)", logic))
        return atoms

    if not isinstance(logic, dict):
        return atoms

    if "atom" in logic:
        atom = str(logic.get("atom", "")).strip()
        if atom:
            atoms.append(atom)

    elif "AND" in logic:
        for child in logic.get("AND", []):
            atoms.extend(logic_to_strings(child))

    elif "OR" in logic:
        for child in logic.get("OR", []):
            atoms.extend(logic_to_strings(child))

    elif "NOT" in logic:
        atoms.extend(logic_to_strings(logic.get("NOT")))

    return atoms

def validate_rule_predicates(unit_id, rules, defined_predicates):
    allowed_builtin = {"min", "max", "not", "NOT"}
    issues = []

    for rule in rules:
        names = []

        for c in rule.get("conditions", []):
            names.extend(extract_predicate_names(c))

        names.extend(extract_predicate_names(rule.get("conclusion", "")))

        bad = sorted(set(
            n for n in names
            if n not in defined_predicates and n not in allowed_builtin
        ))

        if bad:
            issues.append({
                "unit_id": unit_id,
                "rule_id": rule.get("rule_id"),
                "undefined_predicates": bad,
                "rule": rule,
            })

    return issues

def extract_args(expr: str):
    args = []
    for inside in re.findall(r"\(([^()]*)\)", str(expr)):
        for x in inside.split(","):
            x = x.strip()
            if x:
                args.append(x)
    return args


def is_literal_arg(x: str):
    x = str(x).strip()

    if x in {"true", "false", "True", "False"}:
        return True

    try:
        float(x)
        return True
    except Exception:
        return False


def validate_rule_variable_binding(unit_id, rules):
    issues = []

    for rule in rules:
        lhs_args = set()
        rhs_args = set()

        for condition in rule.get("conditions", []):
            lhs_args.update(extract_args(condition))

        rhs_args.update(extract_args(rule.get("conclusion", "")))

        lhs_args = {x for x in lhs_args if not is_literal_arg(x)}
        rhs_args = {x for x in rhs_args if not is_literal_arg(x)}

        if rhs_args and lhs_args and not (rhs_args & lhs_args):
            issues.append({
                "unit_id": unit_id,
                "rule_id": rule.get("rule_id"),
                "issue": "No shared argument between conditions and conclusion",
                "lhs_args": sorted(lhs_args),
                "rhs_args": sorted(rhs_args),
                "rule": rule,
            })

    return issues

def validate_supporting_spans(unit_id, items, statute_text, stage):
    issues = []

    for idx, item in enumerate(items):
        span = str(item.get("supporting_span", "")).strip()

        if span and span not in statute_text:
            issues.append({
                "unit_id": unit_id,
                "stage": stage,
                "index": idx,
                "supporting_span": span,
                "issue": "supporting_span not found exactly in statute_text",
            })

    return issues


def validate_rule_quality(unit_id, rules):
    issues = []

    bad_tokens = [
        "P_S_R_E_D_I_C_A_T_E",
        "PREDICATE_",
        "CONDITION_",
        "UNKNOWN",
        "undefined",
    ]

    for rule in rules:
        conclusion = str(rule.get("conclusion", "")).strip()
        conditions = [str(c).strip() for c in rule.get("conditions", [])]

        for token in bad_tokens:
            if token.lower() in conclusion.lower():
                issues.append({
                    "unit_id": unit_id,
                    "rule_id": rule.get("rule_id"),
                    "issue": "Placeholder or invalid conclusion",
                    "conclusion": conclusion,
                })

        if conclusion in conditions:
            issues.append({
                "unit_id": unit_id,
                "rule_id": rule.get("rule_id"),
                "issue": "Tautological rule P -> P",
                "conclusion": conclusion,
            })

    return issues

def reconcile_rule_predicates(unit_id, statute_text, variables, predicates, rules, issues):
    prompt = f"""
Return ONLY valid JSON.
No markdown.
No explanation.
No reasoning.
No notes.
No self-correction.
No text outside JSON.

Task:
Fix undefined predicates in legal rules.

For each undefined predicate:
1. If an existing predicate means the same thing, rewrite the rule to use the existing predicate.
2. If no existing predicate means the same thing, add that predicate to the predicate list.

Rules:
- Predicate names in conditions and conclusion must exactly match the final predicates list.
- Do not remove all rules.
- Do not return empty rules.
- Added predicates must use only approved variables or primitives: integer, decimal, date, string, boolean.
- supporting_span should be copied exactly from statute.
- The conclusion should share at least one symbolic argument with the conditions.
- conditions must be a list of strings.
- conditions array means AND.
- Use NOT as a string: "NOT predicate_name(X)".
- Use OR as a string: "(predicate_a(X) OR predicate_b(X))".
- Do not create tautological rules where condition equals conclusion.

APPROVED_VARIABLES:
{json.dumps(variables, indent=2)}

CURRENT_PREDICATES:
{json.dumps(predicates, indent=2)}

CURRENT_RULES:
{json.dumps(rules, indent=2)}

VALIDATION_ISSUES:
{json.dumps(issues, indent=2)}

STATUTE:
{statute_text}

Return this JSON:
{{
  "unit_id": "{unit_id}",
  "predicates": [
    {{
      "predicate_name": "",
      "predicate_type": "status|relationship|datatype|definition|cross_reference|exception",
      "arguments": [],
      "description": "",
      "supporting_span": "",
      "constants": {{}}
    }}
  ],
  "rules": [
    {{
      "rule_id": "{unit_id}_rule_1",
      "conditions": [],
      "conclusion": "",
      "constants": {{}},
      "supporting_span": "",
      "explanation": ""
    }}
  ]
}}
"""
    raw = call_llm(prompt)
    save_raw("rules", f"{unit_id}_predicate_reconcile", raw)

    try:
        parsed = extract_json(raw)
    except Exception:
        print("Predicate reconciliation JSON invalid. Trying rule-only repair...")
        try:
            repaired = repair_json("rules", unit_id, raw)
            return {
                "unit_id": unit_id,
                "predicates": predicates,
                "rules": repaired.get("rules", []),
            }
        except Exception as e:
            print(f"Predicate reconciliation JSON repair failed: {e}")
            return {
                "unit_id": unit_id,
                "predicates": predicates,
                "rules": [],
            }

    predicate_part = {
        "unit_id": unit_id,
        "predicates": parsed.get("predicates", []),
    }

    rule_part = {
        "unit_id": unit_id,
        "rules": parsed.get("rules", []),
    }

    try:
        predicate_part = validate_stage_json("predicates", predicate_part)
        rule_part = validate_stage_json("rules", rule_part)
    except Exception as e:
        print(f"Predicate reconciliation schema invalid: {e}")
        return {
            "unit_id": unit_id,
            "predicates": predicates,
            "rules": [],
        }

    new_predicates = predicate_part.get("predicates", [])

    if not new_predicates:
        new_predicates = predicates

    return {
        "unit_id": unit_id,
        "predicates": new_predicates,
        "rules": rule_part.get("rules", []),
    }

def process_unit(row):
    unit_id = row["unit_id"]
    statute_text = row["statute_text"]

    warnings = []

    print("\n" + "=" * 70)
    print(f"Processing {unit_id}")
    print("=" * 70)

    variable_prompt = render_prompt(
        read_prompt("variable_prompt.txt"),
        unit_id=unit_id,
        statute_text=statute_text,
    )

    variable_json = call_stage("variables", unit_id, variable_prompt)
    variables = variable_json.get("variables", [])

    print("Variables:", len(variables))

    predicate_prompt = render_prompt(
        read_prompt("predicate_prompt.txt"),
        unit_id=unit_id,
        statute_text=statute_text,
        variables_json=json.dumps(variables, indent=2),
    )

    predicate_json = call_stage("predicates", unit_id, predicate_prompt)
    predicates = predicate_json.get("predicates", [])
    approved_vars = {v["variable_name"] for v in variables}
    primitive_types = {"integer", "decimal", "date", "string", "boolean"}

    predicates = [
        p for p in predicates
        if all(arg in approved_vars or arg in primitive_types for arg in p.get("arguments", []))
    ]
    print("Predicates:", len(predicates))
    if len(predicates) < 2:
        print("Predicate count too low. Retrying predicate generation...")

        stronger_predicate_prompt = predicate_prompt + """

        IMPORTANT:
        The predicate list is too small.
    Return at least 3 useful predicates if supported by the statute.
    Include:
    1. subject/status predicate
    2. input amount/property predicate
    3. resulting definition/calculation predicate
    """

        predicate_json = call_stage("predicates", unit_id, stronger_predicate_prompt, max_attempts=2)
        predicates = predicate_json.get("predicates", [])
        print("Predicates after retry:", len(predicates))

    if not predicates:
        raise ValueError("No predicates generated. Cannot generate rules safely.")

    rule_prompt = render_prompt(
        read_prompt("rule_prompt.txt"),
        unit_id=unit_id,
        statute_text=statute_text,
        variables_json=json.dumps(variables, indent=2),
        predicates_json=json.dumps(predicates, indent=2),
    )

    rules = []
    defined_predicates = {p["predicate_name"] for p in predicates}
    
    for attempt in range(4):
        rule_json = call_stage("rules", unit_id, rule_prompt, max_attempts=1)
        rules = rule_json.get("rules", [])

        if not rules:
            print("No rules generated. Retrying...")
            continue

        predicate_issues = validate_rule_predicates(
            unit_id,
            rules,
            defined_predicates,
        )

        if predicate_issues:
            print("Reconciling undefined predicates...")

            reconciled = reconcile_rule_predicates(
                unit_id,
                statute_text,
                variables,
                predicates,
                rules,
                predicate_issues,
            )

            predicates = reconciled.get("predicates", predicates)
            rules = reconciled.get("rules", rules)

            if not predicates:
                print("Predicate reconciliation returned 0 predicates. Retrying...")
                continue

            if not rules:
                print("Predicate reconciliation returned 0 rules. Retrying...")
                continue

            defined_predicates = {p["predicate_name"] for p in predicates}

            predicate_issues = validate_rule_predicates(
                unit_id,
                rules,
                defined_predicates,
            )

            if predicate_issues:
                print("Predicate reconciliation unsuccessful. Retrying...")
                continue

        binding_issues = validate_rule_variable_binding(unit_id, rules)
        if binding_issues:
            print("Binding issues found. Retrying:", len(binding_issues))
            continue

        quality_issues = validate_rule_quality(unit_id, rules)
        if quality_issues:
            print("Rule quality warning:", len(quality_issues))
            warnings.extend(quality_issues)

        span_issues = []
        span_issues += validate_supporting_spans(unit_id, variables, statute_text, "variables")
        span_issues += validate_supporting_spans(unit_id, predicates, statute_text, "predicates")
        span_issues += validate_supporting_spans(unit_id, rules, statute_text, "rules")

        if span_issues:
            print("Supporting span issues found. Retrying:", len(span_issues))
            continue

        break

    else:
        raise ValueError("Failed to generate valid rules after all attempts.")

    print("Rules:", len(rules))

    result = {
        "unit_id": unit_id,
        "article_number": row.get("article_number", ""),
        "unit_label": row.get("unit_label", unit_id),
        "title": row.get("title", ""),
        "statute_text": statute_text,
        "variables": variables,
        "predicates": predicates,
        "rules": rules,
        "warnings": warnings,
    }

    out_path = OUT_DIR / "units" / f"{unit_id}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def main():
    units = json.loads(INPUT_JSON.read_text(encoding="utf-8"))

    outputs = []
    failed_units = []

    selected_units = units if TEST_UNITS is None else [
        u for u in units if u.get("unit_id") in TEST_UNITS
    ]

    for idx, row in enumerate(selected_units, start=1):
        unit_id = row["unit_id"]
        print(f"\nProcessing unit {idx}/{len(selected_units)}: {unit_id}")

        try:
            outputs.append(process_unit(row))
        except Exception as e:
            print(f"FAILED {unit_id}: {e}")
            failed_units.append({
                "unit_id": unit_id,
                "error": str(e)
            })

    pilot_path = OUT_DIR / "pilot_outputs.json"
    pilot_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")

    failed_path = REPORT_DIR / "failed_units.json"
    failed_path.write_text(json.dumps(failed_units, indent=2), encoding="utf-8")

    print("\nPilot complete.")
    print("Failed units:", len(failed_units))
    print("Failed report:", failed_path)
    print("Successful units:", len(outputs), "/", len(selected_units))
    print("Output:", pilot_path)

if __name__ == "__main__":
    main()