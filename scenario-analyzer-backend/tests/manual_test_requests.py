"""
Manual smoke test against a running local server.

Start the API first:
    python run_server.py

Then run:
    python tests/manual_test_requests.py
"""

import httpx

BASE = "http://127.0.0.1:8001"

SCENARIOS = [
    "My landlord is forcing me to leave before the agreement ends.",
    "My brother changed mutation records after my father died.",
    "I bought land through a registered sale deed but seller's brother disputes it.",
    "Builder delayed my flat possession for two years.",
    "My uncle sold ancestral property without informing us.",
]


def main() -> None:
    for scenario in SCENARIOS:
        r = httpx.post(
            f"{BASE}/api/scenario/analyze",
            json={"scenario": scenario, "user_context": {"state": "Karnataka", "language": "English"}},
            timeout=120.0,
        )
        r.raise_for_status()
        data = r.json()
        print("---")
        print("scenario:", scenario)
        print("session_id:", data.get("session_id"))
        cv = data.get("compact_view") or {}
        print("detected_issue:", cv.get("detected_issue"))
        print("confidence:", cv.get("confidence"))
        lw = cv.get("lawyer_warning") or {}
        print("lawyer_warning.required:", lw.get("required"))
        print("short_summary:", cv.get("short_summary"))
        print("suggested_follow_up_questions:", data.get("suggested_follow_up_questions"))


if __name__ == "__main__":
    main()
