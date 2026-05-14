from typing import Any

ISSUE_KEYWORDS: dict[str, list[str]] = {
    "tenant_eviction": [
        "landlord",
        "tenant",
        "rent",
        "lease",
        "eviction",
        "vacate",
        "lockout",
        "shop",
        "rented",
        "agreement ends",
        "rental agreement",
    ],
    "mutation_vs_title": [
        "mutation",
        "khata",
        "patta",
        "rtc",
        "revenue record",
        "record of rights",
        "name changed",
        "property records",
        "municipal records",
    ],
    "sale_deed_dispute": [
        "sale deed",
        "registered deed",
        "buyer",
        "seller",
        "vendor",
        "title",
        "registration",
        "sub-registrar",
        "forged deed",
    ],
    "rera_delay": [
        "builder",
        "developer",
        "flat",
        "apartment",
        "possession delay",
        "rera",
        "project",
        "allotment",
        "emi",
        "construction",
    ],
    "partition_ancestral_property": [
        "ancestral",
        "partition",
        "father died",
        "mother died",
        "brother",
        "sister",
        "uncle",
        "legal heir",
        "will",
        "inheritance",
        "share",
        "family property",
        "co-sharer",
    ],
}


def _normalize(text: str) -> str:
    return text.lower()


def classify_scenario(scenario: str) -> dict[str, Any]:
    """Keyword-score scenario; apply tie-breakers; return classification metadata."""
    text = _normalize(scenario)
    all_scores: dict[str, int] = {}
    matched_by_issue: dict[str, list[str]] = {}

    for issue_type, keywords in ISSUE_KEYWORDS.items():
        matched: list[str] = []
        score = 0
        for kw in keywords:
            if kw in text:
                matched.append(kw)
                score += 1
        all_scores[issue_type] = score
        matched_by_issue[issue_type] = matched

    total = sum(all_scores.values())
    if total == 0:
        return {
            "issue_type": "general_property_dispute",
            "score": 0,
            "matched_keywords": [],
            "all_scores": all_scores,
        }

    max_score = max(all_scores.values())
    mutation_score = all_scores["mutation_vs_title"]
    partition_score = all_scores["partition_ancestral_property"]

    strong_partition = partition_score >= 2

    # Prefer mutation when mutation-related terms appear; literal "mutation" beats a higher partition-only score.
    if mutation_score > 0 and ("mutation" in text or mutation_score == max_score):
        issue_type = "mutation_vs_title"
        matched = matched_by_issue[issue_type]
    elif strong_partition and partition_score == max_score:
        issue_type = "partition_ancestral_property"
        matched = matched_by_issue[issue_type]
    else:
        issue_type = max(all_scores, key=lambda k: all_scores[k])
        matched = matched_by_issue[issue_type]

    return {
        "issue_type": issue_type,
        "score": all_scores[issue_type],
        "matched_keywords": matched,
        "all_scores": all_scores,
    }
