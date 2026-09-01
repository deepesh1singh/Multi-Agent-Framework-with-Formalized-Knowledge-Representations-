import json
import re
from pathlib import Path

INPUT_FILE = Path("prompts/sara_fewshot_examples.json")
OUTPUT_FILE = Path("prompts/sara_fewshot_examples_clean.json")


def proposition_keys(rule):
    if not isinstance(rule, dict):
        return set()

    propositions = rule.get("propositions", {})
    if not isinstance(propositions, dict):
        return set()

    return set(propositions.keys())


def logic_uses_only_defined_props(rule):
    keys = proposition_keys(rule)
    logic = rule.get("logic", "")

    if not isinstance(logic, str):
        return False

    used = set(re.findall(r"\bP\d+\b", logic))
    return used.issubset(keys)


def logic_has_no_bad_words(rule):
    logic = rule.get("logic", "")

    if not isinstance(logic, str):
        return False

    bad_phrases = [
        "something else",
        "MINUS",
        "PLUS",
        "->",
        "reasoning_code"
    ]

    return not any(bad in logic for bad in bad_phrases)


def clean_constants(constants):
    if not isinstance(constants, dict):
        return {}

    constants.pop("reasoning_code", None)
    return constants


def clean_rule(rule):
    if not isinstance(rule, dict):
        return None

    rule["constants"] = clean_constants(rule.get("constants", {}))

    if not logic_uses_only_defined_props(rule):
        return None

    if not logic_has_no_bad_words(rule):
        return None

    return rule


def main():
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    cleaned_examples = []

    for ex in data:
        if not isinstance(ex, dict):
            continue

        cleaned_rules = []

        for rule in ex.get("rules", []):
            cleaned = clean_rule(rule)

            if cleaned is not None:
                cleaned_rules.append(cleaned)

        if cleaned_rules:
            ex["rules"] = cleaned_rules
            cleaned_examples.append(ex)

    OUTPUT_FILE.write_text(
        json.dumps(cleaned_examples, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Original examples: {len(data)}")
    print(f"Clean examples: {len(cleaned_examples)}")
    print(f"Saved: {OUTPUT_FILE}")

    for ex in cleaned_examples:
        print(ex["unit_id"], "rules:", len(ex["rules"]))


if __name__ == "__main__":
    main()