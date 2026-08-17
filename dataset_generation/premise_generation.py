import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ============================================
# CONFIG
# ============================================

MODEL_NAME = "gemini-2.5-flash"

TARGET_ROWS = 3000
ROWS_PER_CALL = 100

RAW_OUTPUT_FILE = Path("raw_premises.jsonl")
FINAL_OUTPUT_FILE = Path("property_premise_dataset.jsonl")

SYSTEM_PROMPT = (
    "Generate realistic legal premises for Indian property law topics."
)

TOPICS = [
    "title dispute",
    "adverse possession",
    "partition suit",
    "coparcenary dispute",
    "forged sale deed",
    "mutation dispute",
    "boundary dispute",
    "encroachment",
    "inheritance dispute",
    "family settlement",
    "gift deed challenge",
    "tenant eviction",
    "builder possession delay",
    "RERA complaint",
    "specific performance",
    "injunction dispute",
    "landlord tenant conflict",
    "revenue record dispute",
    "fraudulent transfer",
    "easement rights"
]

GENERATION_MODES = [
    "clean law-school style hypotheticals",
    "messy real-world property disputes",
    "highly ambiguous ownership conflicts",
    "document-heavy evidentiary disputes",
    "family inheritance conflicts",
    "emotionally tense family property fights",
    "oral agreement disputes",
    "weak documentation cases",
    "contradictory timeline disputes",
    "tenant possession ambiguity disputes"
]

# ============================================
# PROMPT
# ============================================

def build_prompt(n_rows: int, mode: str) -> str:

    topic_text = ", ".join(TOPICS)

    return f"""
Generate exactly {n_rows} realistic Indian property-law legal premises.

Generation style:
{mode}

A premise means:
- a short legal backstory
- a factual dispute scenario
- realistic litigation background

NOT legal issues.
NOT 'Whether...' statements.

The premises must involve:
{topic_text}

STRICT REQUIREMENTS:

- Each premise must be 80-220 words.
- Make them realistic and fact-rich.
- Include parties, timelines, ownership disputes, possession disputes, family conflicts, forged documents, oral agreements, missing evidence, contradictory records, tenancy conflicts, inheritance claims, mutation issues, builder disputes, and procedural confusion.
- Use Indian legal/property-law context.
- Some premises should contain ambiguity or incomplete evidence.
- Some disputes should feel emotionally tense and realistic.
- Do NOT include legal analysis.
- Do NOT include judgments.
- Do NOT include bullet points.
- Do NOT include numbering.
- Do NOT include explanations.
- Avoid repetitive structure.
- Avoid textbook tone.

Output STRICT JSONL.

Each line must be:

{{"premise":"text here","topic":"topic name"}}

Output ONLY valid JSONL.
"""


# ============================================
# PARSER
# ============================================

def parse_jsonl(text: str):

    rows = []

    for line in text.splitlines():

        line = line.strip()

        if not line.startswith("{"):
            continue

        try:
            obj = json.loads(line)

            if "premise" in obj and "topic" in obj:
                rows.append(obj)

        except Exception:
            continue

    return rows


# ============================================
# RESUME + DEDUP
# ============================================

def load_existing_rows():

    existing_rows = []
    seen_premises = set()

    if not RAW_OUTPUT_FILE.exists():
        return existing_rows, seen_premises

    with RAW_OUTPUT_FILE.open("r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)

                if "premise" in row and "topic" in row:

                    existing_rows.append(row)

                    normalized = row["premise"].strip().lower()

                    seen_premises.add(normalized)

            except Exception:
                continue

    return existing_rows, seen_premises


# ============================================
# CONVERT TO FINAL DATASET
# ============================================

def convert_to_training_dataset():

    final_rows = []

    if not RAW_OUTPUT_FILE.exists():
        return

    with RAW_OUTPUT_FILE.open("r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)

                topic = row["topic"]
                premise = row["premise"]

                formatted = {
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": topic
                        },
                        {
                            "role": "assistant",
                            "content": premise
                        }
                    ]
                }

                final_rows.append(formatted)

            except Exception:
                continue

    with FINAL_OUTPUT_FILE.open("w", encoding="utf-8") as f:

        for row in final_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nTraining dataset updated.")
    print(f"Rows in final dataset: {len(final_rows)}")


# ============================================
# MAIN
# ============================================

def main():

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in .env")

    client = genai.Client(api_key=api_key)

    existing_rows, seen_premises = load_existing_rows()

    total_generated = len(existing_rows)

    batch_no = (total_generated // ROWS_PER_CALL) + 1

    total_input_tokens = 0
    total_output_tokens = 0

    print("\n====================================")
    print("PROPERTY LAW PREMISE GENERATOR")
    print("====================================")

    print(f"\nResuming generation...")
    print(f"Existing rows found: {total_generated}")
    print(f"Starting batch: {batch_no}")
    print(f"Target rows: {TARGET_ROWS}")

    while total_generated < TARGET_ROWS:

        needed = min(ROWS_PER_CALL, TARGET_ROWS - total_generated)

        mode = GENERATION_MODES[batch_no % len(GENERATION_MODES)]

        prompt = build_prompt(needed, mode)

        print(f"\n------------------------------------")
        print(f"Batch {batch_no}")
        print(f"Mode: {mode}")
        print(f"Generating: {needed} rows")
        print("------------------------------------")

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.95,
                    top_p=0.95,
                    max_output_tokens=32000,
                ),
            )

            text = response.text or ""

            if getattr(response, "usage_metadata", None):

                total_input_tokens += (
                    response.usage_metadata.prompt_token_count
                )

                total_output_tokens += (
                    response.usage_metadata.candidates_token_count
                )

        except Exception as e:

            print(f"\nAPI Error: {e}")

            err = str(e).lower()

            if "429" in err:
                print("Rate limit hit. Waiting 60s...")
                time.sleep(60)

            else:
                print("Waiting 20s...")
                time.sleep(20)

            continue

        rows = parse_jsonl(text)

        if not rows:

            print("No valid rows parsed.")
            time.sleep(10)
            continue

        accepted = 0
        rejected = 0

        with RAW_OUTPUT_FILE.open("a", encoding="utf-8") as f:

            for row in rows:

                try:

                    premise = row["premise"].strip()

                    topic = row["topic"].strip()

                    normalized = premise.lower()

                    # dedup
                    if normalized in seen_premises:
                        rejected += 1
                        continue

                    wc = len(premise.split())

                    # quality filters
                    if wc < 60:
                        rejected += 1
                        continue

                    if wc > 260:
                        rejected += 1
                        continue

                    if len(topic) < 3:
                        rejected += 1
                        continue

                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

                    seen_premises.add(normalized)

                    accepted += 1

                except Exception:
                    rejected += 1
                    continue

        total_generated += accepted

        print(f"\nAccepted rows : {accepted}")
        print(f"Rejected rows : {rejected}")
        print(f"Total dataset : {total_generated}")

        print(
            f"Tokens so far: "
            f"Input={total_input_tokens}, "
            f"Output={total_output_tokens}"
        )

        # checkpoint dataset conversion
        if total_generated % 500 == 0:

            print("\nCreating checkpoint training dataset...")
            convert_to_training_dataset()

        batch_no += 1

        time.sleep(90)

    print("\n====================================")
    print("FINAL DATASET CONVERSION")
    print("====================================")

    convert_to_training_dataset()

    print("\nDONE")
    print(f"\nRaw dataset file   : {RAW_OUTPUT_FILE}")
    print(f"Training dataset   : {FINAL_OUTPUT_FILE}")

    print(f"\nTotal Input Tokens : {total_input_tokens}")
    print(f"Total Output Tokens: {total_output_tokens}")


if __name__ == "__main__":
    main()