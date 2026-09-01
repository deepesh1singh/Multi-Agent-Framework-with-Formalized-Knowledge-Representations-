import json

units = json.load(open("data/sara/sara_sections.json", encoding="utf-8"))
classes = json.load(open("outputs/sara/final/sara_classes_full.json", encoding="utf-8"))
preds = json.load(open("outputs/sara/final/sara_predicates_full.json", encoding="utf-8"))
rules = json.load(open("outputs/sara/final/sara_rules_full.json", encoding="utf-8"))

all_ids = {x["unit_id"] for x in units}
class_ids = {x["unit_id"] for x in classes}
pred_ids = {x["unit_id"] for x in preds}
rule_ids = {x["unit_id"] for x in rules}

print("\nMissing Classes:")
print(sorted(all_ids - class_ids))

print("\nMissing Predicates:")
print(sorted(all_ids - pred_ids))

print("\nMissing Rules:")
print(sorted(all_ids - rule_ids))