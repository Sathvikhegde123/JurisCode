import os
import re
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import Counter

from dotenv import load_dotenv
from tqdm import tqdm
from google import genai
from google.genai import types


# =========================
# CONFIG
# =========================

MODEL_NAME = "gemini-2.5-flash"
TARGET_ROWS = 3000
ROWS_PER_CALL = 40

OUTPUT_FILE = Path("property_litigation_opposing_counsel_dataset_3000.jsonl")
REJECTED_FILE = Path("property_litigation_rejected_rows.jsonl")
STATS_FILE = Path("property_litigation_validation_summary.json")
SAMPLE_FILE = Path("legal_dataset_v2.txt")

SYSTEM_PROMPT = (
    "You are a senior Indian courtroom advocate acting as opposing counsel in a property litigation training simulation. "
    "Your task is to critically challenge the user's property-law argument using title analysis, possession analysis, "
    "civil procedure, evidentiary scrutiny, document authentication, limitation, burden-of-proof analysis, "
    "contradiction exposure, and strategic courtroom questioning. "
    "Maintain a professional courtroom tone. Do not invent case citations. "
    "Do not use generic legal-sounding rhetoric. "
    "Respond with precise adversarial reasoning tied to the facts, documents, and legal issue raised."
)

DOMAIN_PLAN = [
    ("Core Property Law, Title, Ownership, and Possession", 590),
    ("Real Estate, Tenancy, RERA, and Builder Disputes", 386),
    ("Civil Procedure, Injunction, Limitation, and Jurisdiction", 429),
    ("Evidence Law, Document Proof, and Electronic Evidence", 514),
    ("Cross-Examination and Trial Strategy", 513),
    ("Contract, Consumer, and Real Estate Agreements", 257),
    ("Limited Property-Related Criminal Overlap", 86),
    ("Limited Administrative and Municipal Land Matters", 86),
]

DOMAIN_DETAILS = {
    "Core Property Law, Title, Ownership, and Possession": """
Include title disputes, sale deed validity, chain of title, root of title, possession, co-owner rights, partition, ancestral property, family settlement, gift deed, release deed, adverse possession, boundary disputes, encroachment, easement rights, mutation entries, revenue records, khata entries, RTC/pahani records, tax receipts, and ownership vs possession distinction.
""",
    "Real Estate, Tenancy, RERA, and Builder Disputes": """
Include landlord-tenant disputes, lease termination, eviction, rent arrears, illegal occupation, redevelopment disputes, apartment association disputes, builder delay, possession delay, RERA complaints, promised amenities, occupancy certificate issues, refund claims, maintenance charges, parking disputes, and flat allotment disputes.
""",
    "Civil Procedure, Injunction, Limitation, and Jurisdiction": """
Include temporary injunction, permanent injunction, prima facie case, balance of convenience, irreparable injury, limitation, jurisdiction, cause of action, res judicata, non-joinder, misjoinder, pleadings, amendment of pleadings, declaratory relief, specific performance suits, execution proceedings, interim stay, alternative remedy, and burden of proof.
""",
    "Evidence Law, Document Proof, and Electronic Evidence": """
Include sale deed proof, registered documents, unregistered documents, stamp duty issues, forged documents, suspicious signatures, handwriting expert evidence, revenue records, mutation records, certified copies, secondary evidence, witness testimony, hostile witnesses, contradictions, omissions, WhatsApp/email/payment records, CCTV, electronic evidence certificates, chain of custody, metadata, and document authenticity.
""",
    "Cross-Examination and Trial Strategy": """
Include witness credibility, timeline contradiction, documentary inconsistency, improvements in testimony, missing independent witnesses, biased witnesses, admissions, contradiction between sale deed and possession records, revenue record mismatch, payment proof gaps, site inspection inconsistency, burden shifting, and strategic narrowing of issues during trial.
""",
    "Contract, Consumer, and Real Estate Agreements": """
Include agreement to sell, specific performance, breach of contract, advance payment disputes, refund disputes, builder-buyer agreement, unfair clauses, force majeure in construction delay, service deficiency, warranty of title, misrepresentation, non-disclosure of encumbrance, cancellation clauses, notice requirements, and liquidated damages.
""",
    "Limited Property-Related Criminal Overlap": """
Keep this strictly limited. Include only property-related forgery, cheating in sale transaction, forged power of attorney, trespass, criminal intimidation linked to possession disputes, fraudulent sale deed, impersonation in registration, and fake document use. Do not make the dataset criminal-law heavy.
""",
    "Limited Administrative and Municipal Land Matters": """
Include land acquisition, municipal demolition, building plan sanction, illegal construction notice, revenue authority orders, conversion order, zoning violation, khata transfer refusal, land-use disputes, non-speaking orders, natural justice, and administrative appeal. Keep this related to land/property only.
""",
}

BAD_USER_OPENINGS = [
    "your present submission",
    "the position you now advance",
    "this new proposition undermines",
    "your argument ignores",
    "your contention fails",
    "your reasoning proceeds",
    "what your submission omits",
    "your submission",
    "your reliance",
    "your case theory",
    "your present case",
    "counsel's argument",
    "opposing counsel",
]

BAD_PHRASES = [
    "section 65b bsa",
    "as per xyz",
    "2021 scc 9999",
    "clearly this fails",
    "the court will reject this",
]

BANNED_ASSISTANT_OPENINGS = [
    "while",
    "although",
    "though",
    "it is true that",
    "that said",
    "even if",
    "even assuming",
]

CONSTITUTIONAL_STRICT_DOMAINS = {
    "Core Property Law, Title, Ownership, and Possession",
    "Real Estate, Tenancy, RERA, and Builder Disputes",
    "Civil Procedure, Injunction, Limitation, and Jurisdiction",
    "Evidence Law, Document Proof, and Electronic Evidence",
    "Cross-Examination and Trial Strategy",
    "Contract, Consumer, and Real Estate Agreements",
    "Limited Property-Related Criminal Overlap",
}

CONSTITUTIONAL_USER_TRIGGERS = re.compile(
    r"\b(article\s*\d|constitution|fundamental\s*right|writ|natural\s*justice)\b",
    re.IGNORECASE,
)

CONSTITUTIONAL_ASSISTANT_MARKERS = re.compile(
    r"\b(article\s*14|article\s*19|article\s*21|fundamental\s*right|constitutional|writ\s*petition)\b",
    re.IGNORECASE,
)

OVERUSED_OPENINGS: Dict[str, int] = {}

total_assistant_accepted = 0
question_ending_accepted = 0


# =========================
# UTILS
# =========================

def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def first_words(text: str, n: int = 8) -> str:
    words = re.findall(r"\b[\w'-]+\b", text.lower())
    return " ".join(words[:n])


def load_sample() -> str:
    if not SAMPLE_FILE.exists():
        return ""
    lines = SAMPLE_FILE.read_text(encoding="utf-8").splitlines()
    good_lines = [line for line in lines if line.strip().startswith("{")]
    return "\n".join(good_lines[:6])


def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:jsonl|json)?", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"```$", "", text.strip())
    return text.strip()


def parse_model_output(text: str) -> List[Dict[str, Any]]:
    text = strip_code_fences(text)
    rows = []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
        if isinstance(parsed, dict):
            return [parsed]
    except Exception:
        pass

    for line in text.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            continue

    return rows


def valid_role_order(messages: List[Dict[str, str]]) -> bool:
    roles = [m.get("role") for m in messages]
    return roles == ["system", "user", "assistant"]


# =========================
# RESUME LOADER
# =========================

def load_existing_rows(output_file: Path) -> Tuple[
    set, set, set, Dict[str, int], int, int, int, int, int, int
]:
    seen_conversations: set = set()
    seen_opening_users: set = set()
    seen_assistants: set = set()
    overused: Dict[str, int] = {}
    single_turn = 0
    two_turn = 0
    three_turn = 0
    other = 0
    total_asst = 0
    question_asst = 0

    if not output_file.exists():
        return (seen_conversations, seen_opening_users, seen_assistants,
                overused, single_turn, two_turn, three_turn, other,
                total_asst, question_asst)

    with output_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue

            messages = row.get("messages", [])
            length = len(messages)
            if length == 3:
                single_turn += 1
            elif length == 5:
                two_turn += 1
            elif length == 7:
                three_turn += 1
            else:
                other += 1

            conv_key = normalize_text(json.dumps(row, ensure_ascii=False, sort_keys=True))
            seen_conversations.add(conv_key)

            if len(messages) > 1 and messages[1].get("role") == "user":
                seen_opening_users.add(normalize_text(messages[1]["content"]))

            for msg in messages:
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    seen_assistants.add(normalize_text(content))
                    opening = first_words(content, 8)
                    overused[opening] = overused.get(opening, 0) + 1
                    total_asst += 1
                    if content.strip().endswith("?"):
                        question_asst += 1

    return (seen_conversations, seen_opening_users, seen_assistants,
            overused, single_turn, two_turn, three_turn, other,
            total_asst, question_asst)


# =========================
# VALIDATION
# =========================

def validate_and_normalize_row(
    row: Dict[str, Any],
    seen_conversations: set,
    seen_opening_users: set,
    seen_assistants: set,
    domain: str = "",
) -> Tuple[bool, Dict[str, Any], str]:
    global total_assistant_accepted, question_ending_accepted

    if set(row.keys()) != {"messages"}:
        return False, row, "invalid_top_level_keys"

    messages = row.get("messages")
    if not isinstance(messages, list):
        return False, row, "messages_not_list"

    if not valid_role_order(messages):
        return False, row, "invalid_role_order"

    for msg in messages:
        if set(msg.keys()) != {"role", "content"}:
            return False, row, "invalid_message_keys"
        if not isinstance(msg.get("content"), str) or not msg["content"].strip():
            return False, row, "empty_content"

    messages[0]["content"] = SYSTEM_PROMPT

    for msg in messages:
        if msg["role"] == "user":
            low = msg["content"].strip().lower()
            if any(low.startswith(x) for x in BAD_USER_OPENINGS):
                return False, row, "user_role_contamination"

    for msg in messages:
        if msg["role"] == "assistant":
            content = msg["content"]
            wc = word_count(content)
            if wc < 45:
                return False, row, "assistant_too_short"
            if wc > 150:
                return False, row, "assistant_too_long"

            low = content.lower()
            if any(p in low for p in BAD_PHRASES):
                return False, row, "bad_phrase_or_wrong_law"

            stripped_low = content.strip().lower()
            if any(stripped_low.startswith(b) for b in BANNED_ASSISTANT_OPENINGS):
                return False, row, "banned_assistant_opening"

            opening = first_words(content, 8)
            if OVERUSED_OPENINGS.get(opening, 0) >= 5:
                return False, row, "overused_assistant_opening"

            norm_assistant = normalize_text(content)
            if norm_assistant in seen_assistants:
                return False, row, "repeated_assistant_response"

    new_question_enders = sum(
        1 for m in messages
        if m["role"] == "assistant" and m["content"].strip().endswith("?")
    )
    if new_question_enders > 0 and total_assistant_accepted > 0:
        current_pct = question_ending_accepted / total_assistant_accepted
        if current_pct > 0.30:
            return False, row, "question_ending_ratio_too_high"

    if domain in CONSTITUTIONAL_STRICT_DOMAINS:
        user_texts = " ".join(m["content"] for m in messages if m["role"] == "user")
        user_triggers = bool(CONSTITUTIONAL_USER_TRIGGERS.search(user_texts))
        if not user_triggers:
            for msg in messages:
                if msg["role"] == "assistant":
                    hits = CONSTITUTIONAL_ASSISTANT_MARKERS.findall(msg["content"])
                    if len(hits) >= 2:
                        return False, row, "unnecessary_constitutional_framing"

    opening_user = normalize_text(messages[1]["content"])
    if opening_user in seen_opening_users:
        return False, row, "repeated_opening_user"

    conv_key = normalize_text(json.dumps(row, ensure_ascii=False, sort_keys=True))
    if conv_key in seen_conversations:
        return False, row, "duplicate_conversation"

    seen_opening_users.add(opening_user)
    seen_conversations.add(conv_key)

    for msg in messages:
        if msg["role"] == "assistant":
            seen_assistants.add(normalize_text(msg["content"]))
            opening = first_words(msg["content"], 8)
            OVERUSED_OPENINGS[opening] = OVERUSED_OPENINGS.get(opening, 0) + 1
            total_assistant_accepted += 1
            if msg["content"].strip().endswith("?"):
                question_ending_accepted += 1

    return True, row, "ok"


# =========================
# PROMPT BUILDING
# =========================

def batch_structure_instruction(n_rows: int) -> str:
    return (
        f"\nFor this batch of {n_rows} rows, generate exactly {n_rows} single-turn rows.\n"
        f"Every row must have exactly 3 messages:\n"
        f"system -> user -> assistant\n"
        f"Do not generate multi-turn rows.\n"
        f"Do not generate 5-message rows.\n"
        f"Do not generate 7-message rows.\n"
        f"Do not generate 9-message rows.\n"
    )


def build_prompt(domain: str, details: str, n_rows: int, sample: str, batch_no: int) -> str:
    return f"""
You are generating synthetic fine-tuning data for an Indian property litigation AI project.

Task:
Generate exactly {n_rows} JSONL rows for the domain:

{domain}

Domain details:
{details}

The model being trained is Qwen2.5-3B-Instruct using LoRA/QLoRA.
The assistant must act as senior Indian courtroom opposing counsel specializing in property litigation.

Use the attached-style sample below only to understand JSONL structure and quality.
Do not copy, paraphrase, or reuse the sample facts.

SAMPLE JSONL:
{sample}

STRICT OUTPUT FORMAT:
- Output JSONL only.
- Do not output a JSON array.
- Each line must be one complete JSON object.
- No markdown.
- No numbering.
- No explanation.
- No comments.
- No code fence.
- Top-level structure must be exactly: {{"messages":[...]}}
- No extra keys.

Allowed structure only:
system -> user -> assistant

Every row must contain:
1. system message with the exact system prompt
2. user message containing factual premise + legal argument
3. assistant message containing opposing counsel challenge

{batch_structure_instruction(n_rows)}

USER PROMPT FACT-RICHNESS RULE:
The dataset must not consist only of abstract legal claims. Most user prompts must contain factual background inside the user message.

Use this approximate distribution:
- 65% fact-rich litigation prompts:
  Include facts, documents, timeline, party positions, and legal claim.
- 25% medium factual prompts:
  Include at least one document/evidence reference and one legal claim.
- 10% short student-style legal prompts:
  Simple legal argument, but still connected to property litigation.

Do not create a separate "premise" field.
Do not create a separate "background" field.
The factual premise must be inside the user message content.

Good user prompt examples:
- "My client purchased the property through a registered sale deed in 2018. Mutation was changed in his name, and he has paid property tax since then. The defendant says the vendor had no title because the land was ancestral. We argue that the registered sale deed and mutation records prove ownership."
- "The tenant has occupied the shop for twelve years and paid rent regularly. The landlord issued an eviction notice without mentioning any breach of lease terms. We argue that the eviction is invalid."
- "The buyer paid 80% of the apartment price under the builder-buyer agreement, but possession was delayed by three years. We argue that the buyer is entitled to refund and compensation."
- "The plaintiff seeks temporary injunction based on possession, but the defendant disputes the sale deed and says the vendor had no transferable title."
- "The mutation entry is in my client's name, so we argue that ownership should be presumed."

ASSISTANT RESPONSE RULE:
The assistant must act as opposing counsel and directly attack the user's factual/legal claim. The response should challenge one or more of:
- title proof, root of title, vendor's transferable title
- possession, mutation/revenue records
- registered document vs ownership
- document authenticity, forged document allegations
- limitation, injunction requirements
- jurisdiction, maintainability
- burden of proof, witness credibility
- contradictions between documents, evidentiary gaps
- procedural defects, notice requirements
- contract clauses, RERA/builder obligations
- tenancy proof
The assistant should not merely explain law like a textbook. It must attack the weakness in the user's argument as opposing counsel.

BANNED ASSISTANT OPENINGS:
Assistant responses must not start with "While", "Although", "Though", "It is true that", "That said", or "Even assuming".

QUESTION ENDING CONTROL:
Only around 30% of assistant responses may end with a question. Most responses must end with a clear adversarial conclusion, legal consequence, evidentiary insufficiency, or procedural objection.
Good endings:
- "The claim therefore cannot survive without independent proof."
- "The maintainability objection arises before the merits."
- "The evidentiary gap remains fatal to your submission."
- "Registration proves execution, not title."
- "The burden remains on your client."

DOMAIN-SPECIFIC REASONING RULE:
Do not force constitutional framing into property litigation rows. For property, contract, consumer, evidence, civil procedure, tenancy, RERA, and builder disputes, use ordinary legal reasoning such as title, possession, root of title, registered document, mutation entry, limitation, injunction tests, jurisdiction, admissibility, chain of custody, burden of proof, document authenticity, witness credibility, contradiction in records, and procedural maintainability. Mention Article 14, Article 19, Article 21, fundamental rights, proportionality, or writ jurisdiction only when the user explicitly raises a constitutional or public-law issue.

DIVERSE OPENING RULE:
Assistant responses must start in varied ways. Do not use a predictable "acknowledge user point then cite law then ask question" template.
Use diverse openings like:
- "Registration proves execution, not title."
- "Mutation records are fiscal entries, not conclusive ownership proof."
- "The threshold difficulty is the absence of root-of-title evidence."
- "Possession alone does not answer the question of lawful entitlement."
- "The injunction claim fails unless prima facie title and possession are shown."
- "The burden remains on your client to prove the vendor's transferable title."
- "The evidentiary record does not support the alleged chain of title."
- "The tenancy defence depends on proof of lawful possession, not mere occupation."
- "The builder's delay must be tested against the contractual schedule and notice clauses."
- "The document authenticity issue cannot be cured by registration alone."

LENGTH VARIATION:
Assistant responses must remain between 45 and 150 words, but vary naturally:
- some concise responses: 50-70 words
- most responses: 75-115 words
- some deeper responses: 120-145 words
Do not keep every response in the same narrow word-count band.

Use this exact system prompt in every row:
{SYSTEM_PROMPT}

Dataset quality rules:
- User must sound like trainee counsel, junior advocate, law student, or simulated party.
- User must not sound like opposing counsel.
- Assistant must directly challenge the exact user argument.
- Assistant must identify weakness, missing element, evidentiary gap, procedural flaw, overstatement, or contradiction.
- Assistant must use Indian legal reasoning rooted in property, civil, and evidence law.
- Assistant must avoid fake case citations.
- Assistant must avoid invented statutory sections.
- Assistant must avoid generic rhetoric.
- Assistant must avoid dramatic courtroom language.
- Assistant must not always end with a question.
- Assistant length must be between 45 and 150 words, ideally 70-120 words.
- Avoid repetition in openings, facts, arguments, and responses.
- Do not force BNS/BNSS/BSA into property, civil, tenancy, RERA, or consumer matters unless directly relevant.

Batch number: {batch_no}

Generate exactly {n_rows} valid JSONL rows now.
"""


# =========================
# MAIN GENERATION
# =========================

def main():
    global total_assistant_accepted, question_ending_accepted

    load_dotenv(override=True)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found. Put it inside .env file.")

    client = genai.Client(api_key=api_key)
    sample = load_sample()

    accepted_rows = []
    rejected_rows = []

    (seen_conversations, seen_opening_users, seen_assistants,
     loaded_overused, single_existing, two_existing,
     three_existing, other_existing,
     loaded_total_asst, loaded_question_asst) = load_existing_rows(OUTPUT_FILE)

    OVERUSED_OPENINGS.update(loaded_overused)
    total_assistant_accepted = loaded_total_asst
    question_ending_accepted = loaded_question_asst

    existing_total = single_existing + two_existing + three_existing + other_existing
    q_pct = (loaded_question_asst / loaded_total_asst * 100) if loaded_total_asst > 0 else 0.0
    print(f"\n--- Resume Status ---")
    print(f"Existing rows loaded:   {existing_total}")
    print(f"  Single-turn existing: {single_existing}")
    print(f"  Two-turn existing:    {two_existing}")
    print(f"  Three-turn existing:  {three_existing}")
    print(f"  Other structures:     {other_existing}")
    print(f"  Assistant turns:      {loaded_total_asst}")
    print(f"  Question-ending:      {loaded_question_asst} ({q_pct:.1f}%)")
    print(f"Continuing generation without deleting existing rows.\n")

    #OUTPUT_FILE.write_text("", encoding="utf-8")
    #REJECTED_FILE.write_text("", encoding="utf-8")

    batch_no = 1
    running_file_total = existing_total

    for domain, target_count in DOMAIN_PLAN:
        accepted_for_domain = 0

        with tqdm(total=target_count, desc=domain[:35]) as pbar:
            while accepted_for_domain < target_count:
                need = min(ROWS_PER_CALL, target_count - accepted_for_domain)
                prompt = build_prompt(domain, DOMAIN_DETAILS[domain], need, sample, batch_no)

                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.75,
                            top_p=0.9,
                            max_output_tokens=16000,
                        ),
                    )
                    text = response.text or ""
                except Exception as e:
                    print("\nFULL API ERROR:", repr(e))
                    err_str = str(e).lower()
                    if "429" in err_str or "resource_exhausted" in err_str:
                        print(f"\nQuota/rate limit hit. Waiting before retry...")
                        time.sleep(60)
                    elif "503" in err_str or "unavailable" in err_str:
                        print(f"\nGemini high demand. Waiting before retry...")
                        time.sleep(30)
                    else:
                        print(f"\nAPI error: {e}")
                        time.sleep(20)
                    continue

                parsed_rows = parse_model_output(text)

                if not parsed_rows:
                    print(f"\nNo parseable rows in batch {batch_no}. Retrying...")
                    time.sleep(5)
                    batch_no += 1
                    continue

                batch_single = sum(1 for r in parsed_rows if len(r.get("messages", [])) == 3)
                batch_invalid = len(parsed_rows) - batch_single
                print(f"\n  Parsed batch structures: single={batch_single}, invalid={batch_invalid}")

                accepted_this_call = 0
                reject_reasons: Counter = Counter()

                for row in parsed_rows:
                    ok, cleaned_row, reason = validate_and_normalize_row(
                        row,
                        seen_conversations,
                        seen_opening_users,
                        seen_assistants,
                        domain=domain,
                    )

                    if ok and accepted_for_domain < target_count:
                        with OUTPUT_FILE.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(cleaned_row, ensure_ascii=False) + "\n")
                        accepted_rows.append(cleaned_row)
                        accepted_for_domain += 1
                        accepted_this_call += 1
                        running_file_total += 1
                        pbar.update(1)
                    else:
                        reject_reasons[reason] += 1
                        rejected_rows.append({"reason": reason, "row": row})
                        with REJECTED_FILE.open("a", encoding="utf-8") as f:
                            f.write(json.dumps({"reason": reason, "row": row}, ensure_ascii=False) + "\n")

                q_pct_now = (question_ending_accepted / total_assistant_accepted * 100) if total_assistant_accepted > 0 else 0.0
                print(f"  Accepted: {accepted_this_call} | Total file rows: {running_file_total} | Q-end%: {q_pct_now:.1f}%")
                if reject_reasons:
                    top_rejects = reject_reasons.most_common(5)
                    parts = [f"{r}={c}" for r, c in top_rejects]
                    print(f"  Rejections: {', '.join(parts)}")

                if accepted_this_call == 0:
                    print(f"\nBatch {batch_no} accepted 0 rows. Retrying with stricter generation.")
                    time.sleep(5)

                batch_no += 1
                time.sleep(3)

    stats = validate_final_file(OUTPUT_FILE)
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nDONE")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Rejected: {REJECTED_FILE}")
    print(f"Stats: {STATS_FILE}")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


# =========================
# FINAL VALIDATION
# =========================

DOMAIN_KEYWORD_GROUPS = {
    "property_title_possession": re.compile(
        r"\b(title|possession|sale\s*deed|gift\s*deed|partition|ancestral|"
        r"adverse\s*possession|encroachment|easement|mutation|khata|"
        r"revenue\s*record|boundary|co-?owner|release\s*deed)\b", re.IGNORECASE),
    "tenancy_rera_builder": re.compile(
        r"\b(tenant|tenancy|landlord|eviction|rent|lease|rera|builder|"
        r"redevelopment|occupancy\s*certificate|flat\s*allotment|"
        r"maintenance\s*charge|parking)\b", re.IGNORECASE),
    "civil_procedure_injunction": re.compile(
        r"\b(injunction|limitation|jurisdiction|cause\s*of\s*action|"
        r"res\s*judicata|specific\s*performance|declaratory|"
        r"prima\s*facie|balance\s*of\s*convenience|irreparable|"
        r"maintainability|pleading|execution)\b", re.IGNORECASE),
    "evidence_document_proof": re.compile(
        r"\b(evidence|document|registered|unregistered|forged|forgery|"
        r"stamp\s*duty|handwriting|certified\s*copy|secondary\s*evidence|"
        r"hostile\s*witness|chain\s*of\s*custody|authenticity|admissib)\b", re.IGNORECASE),
    "cross_examination_trial": re.compile(
        r"\b(cross.?examin|trial|witness\s*credib|testimony|improvement|"
        r"contradiction|admission|site\s*inspection|burden\s*shift|"
        r"strategic|narrowing)\b", re.IGNORECASE),
    "contract_consumer": re.compile(
        r"\b(contract|agreement\s*to\s*sell|breach|advance\s*payment|"
        r"refund|builder.?buyer|unfair\s*clause|force\s*majeure|"
        r"service\s*deficiency|warranty\s*of\s*title|misrepresentation|"
        r"encumbrance|cancellation\s*clause|liquidated\s*damages)\b", re.IGNORECASE),
    "criminal_overlap": re.compile(
        r"\b(forgery|cheating|trespass|criminal\s*intimidation|"
        r"fraudulent|impersonation|fake\s*document|power\s*of\s*attorney)\b", re.IGNORECASE),
    "administrative_municipal": re.compile(
        r"\b(land\s*acquisition|municipal|demolition|building\s*plan|"
        r"illegal\s*construction|revenue\s*authority|conversion\s*order|"
        r"zoning|khata\s*transfer|land.?use)\b", re.IGNORECASE),
}


def validate_final_file(path: Path) -> Dict[str, Any]:
    stats: Dict[str, Any] = {
        "total_rows": 0,
        "invalid_json_lines": 0,
        "single_turn_rows": 0,
        "two_turn_rows": 0,
        "three_turn_rows": 0,
        "other_structure_rows": 0,
        "estimated_single_turn_percentage": 0.0,
        "estimated_multi_turn_percentage": 0.0,
        "assistant_below_45_words": 0,
        "assistant_above_150_words": 0,
        "unique_opening_user_prompts": 0,
        "unique_assistant_responses": 0,
        "duplicate_conversations": 0,
        "exact_system_prompt_matches": 0,
        "total_assistant_turns": 0,
        "average_assistant_word_count": 0.0,
        "min_assistant_word_count": None,
        "max_assistant_word_count": None,
        "question_ending_count": 0,
        "question_ending_percentage": 0.0,
        "banned_opening_count": 0,
        "structure_validity_passed": 0,
        "ready_for_training_basic_structure": False,
    }

    domain_hits: Dict[str, int] = {k: 0 for k in DOMAIN_KEYWORD_GROUPS}

    seen_conv: set = set()
    opening_users: set = set()
    assistants: set = set()
    all_assistant_wcs: List[int] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            stats["total_rows"] += 1
            try:
                row = json.loads(line)
            except Exception:
                stats["invalid_json_lines"] += 1
                continue

            messages = row.get("messages", [])
            length = len(messages)

            if length == 3:
                stats["single_turn_rows"] += 1
            elif length == 5:
                stats["two_turn_rows"] += 1
            elif length == 7:
                stats["three_turn_rows"] += 1
            else:
                stats["other_structure_rows"] += 1

            if valid_role_order(messages):
                stats["structure_validity_passed"] += 1

            if messages and messages[0].get("role") == "system":
                if messages[0].get("content", "").strip() == SYSTEM_PROMPT.strip():
                    stats["exact_system_prompt_matches"] += 1

            if len(messages) > 1 and messages[1].get("role") == "user":
                opening_users.add(normalize_text(messages[1].get("content", "")))

            row_text = " ".join(m.get("content", "") for m in messages if m.get("role") != "system")
            for group_name, pattern in DOMAIN_KEYWORD_GROUPS.items():
                if pattern.search(row_text):
                    domain_hits[group_name] += 1

            for msg in messages:
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    stats["total_assistant_turns"] += 1
                    wc = word_count(content)
                    all_assistant_wcs.append(wc)
                    if wc < 45:
                        stats["assistant_below_45_words"] += 1
                    if wc > 150:
                        stats["assistant_above_150_words"] += 1
                    assistants.add(normalize_text(content))
                    if content.strip().endswith("?"):
                        stats["question_ending_count"] += 1
                    stripped_low = content.strip().lower()
                    if any(stripped_low.startswith(b) for b in BANNED_ASSISTANT_OPENINGS):
                        stats["banned_opening_count"] += 1

            key = normalize_text(json.dumps(row, ensure_ascii=False, sort_keys=True))
            if key in seen_conv:
                stats["duplicate_conversations"] += 1
            seen_conv.add(key)

    stats["unique_opening_user_prompts"] = len(opening_users)
    stats["unique_assistant_responses"] = len(assistants)

    total = stats["total_rows"]
    if total > 0:
        multi = stats["two_turn_rows"] + stats["three_turn_rows"]
        stats["estimated_multi_turn_percentage"] = round(multi / total * 100, 2)
        stats["estimated_single_turn_percentage"] = round(stats["single_turn_rows"] / total * 100, 2)

    asst_total = stats["total_assistant_turns"]
    if asst_total > 0:
        stats["question_ending_percentage"] = round(stats["question_ending_count"] / asst_total * 100, 2)

    if all_assistant_wcs:
        stats["average_assistant_word_count"] = round(
            sum(all_assistant_wcs) / len(all_assistant_wcs), 2
        )
        stats["min_assistant_word_count"] = min(all_assistant_wcs)
        stats["max_assistant_word_count"] = max(all_assistant_wcs)

    stats["single_turn_only_passed"] = (
        stats["single_turn_rows"] == total
        and stats["two_turn_rows"] == 0
        and stats["three_turn_rows"] == 0
        and stats["other_structure_rows"] == 0
    )

    stats["ready_for_training_basic_structure"] = (
        stats["invalid_json_lines"] == 0
        and stats["other_structure_rows"] == 0
        and stats["two_turn_rows"] == 0
        and stats["three_turn_rows"] == 0
        and stats["duplicate_conversations"] == 0
        and stats["structure_validity_passed"] == total
    )

    stats["domain_keyword_estimates"] = domain_hits

    return stats


if __name__ == "__main__":
    main()
