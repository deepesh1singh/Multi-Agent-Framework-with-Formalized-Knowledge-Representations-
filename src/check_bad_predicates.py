import json

with open(
    "outputs/sara/final/sara_workflow_full.json",
    encoding="utf-8"
) as f:
    data = json.load(f)

for unit in data:
    uid = unit["unit_id"]

    for pred in unit.get("predicates", []):
        if not isinstance(pred, dict):
            print("BAD PREDICATE")
            print(uid)
            print(type(pred))
            print(pred)
            print("-" * 50)