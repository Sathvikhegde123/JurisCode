import json

INPUT_FILE = "property_litigation_opposing_counsel_dataset_3000.jsonl"
OUTPUT_FILE = "property_litigation_opposing_counsel_dataset_3000_updated.jsonl"

# NEW_SYSTEM_PROMPT = (
#     "You are adversarial Indian legal counsel in a courtroom training simulation. "
#     "Critically challenge the user’s argument using procedural scrutiny, "
#     "evidentiary analysis, burden-of-proof evaluation, contradiction exposure, "
#     "and precise legal reasoning tied directly to the presented facts."
# )

NEW_SYSTEM_PROMPT = (
    "You are adversarial Indian opposing counsel in a property-litigation training simulation. "
    "Critically challenge the user's argument using title analysis, possession analysis, "
    "civil procedure, evidentiary scrutiny, burden-of-proof evaluation, contradiction exposure, "
    "and fact-specific legal reasoning. Do not invent case citations."
)

updated_count = 0

with open(INPUT_FILE, "r", encoding="utf-8") as infile, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

    for line in infile:
        if not line.strip():
            continue

        data = json.loads(line)

        # Replace all system prompts
        if "messages" in data:
            for msg in data["messages"]:
                if msg.get("role") == "system":
                    msg["content"] = NEW_SYSTEM_PROMPT
                    updated_count += 1

        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

print("=" * 50)
print("SYSTEM PROMPT REPLACEMENT COMPLETE")
print("=" * 50)
print(f"Updated system prompts: {updated_count}")
print(f"Saved updated dataset to: {OUTPUT_FILE}")