import json
import logging
from pathlib import Path
from typing import Any

from app.config import project_root

logger = logging.getLogger(__name__)

SOURCE_PACKS_DIR = project_root() / "source_packs"
FALLBACK_ISSUE_TYPE = "sale_deed_dispute"


def _minimal_pack(requested: str, reason: str) -> dict[str, Any]:
    return {
        "issue_type": FALLBACK_ISSUE_TYPE,
        "display_name": "Fallback pack",
        "domain": "property_law",
        "official_sources": [],
        "safety_triggers": [],
        "_load_error": reason,
        "_requested_issue_type": requested,
    }


def list_available_source_packs() -> list[str]:
    if not SOURCE_PACKS_DIR.is_dir():
        return []
    names: list[str] = []
    for p in sorted(SOURCE_PACKS_DIR.glob("*.json")):
        names.append(p.stem)
    return names


def source_packs_dir_exists() -> bool:
    return SOURCE_PACKS_DIR.is_dir()


def load_source_pack(issue_type: str) -> dict[str, Any]:
    """Load JSON source pack from project root ``source_packs/``; never raises."""
    try:
        path = SOURCE_PACKS_DIR / f"{issue_type}.json"
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                return json.load(f)

        fallback_path = SOURCE_PACKS_DIR / f"{FALLBACK_ISSUE_TYPE}.json"
        if not fallback_path.is_file():
            logger.error("Missing fallback source pack at %s", fallback_path)
            return _minimal_pack(
                issue_type,
                f"Neither {path.name} nor fallback {fallback_path.name} found.",
            )

        with fallback_path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        data["_fallback_used"] = True
        data["_requested_issue_type"] = issue_type
        return data
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.exception("load_source_pack failed for issue_type=%s", issue_type)
        return _minimal_pack(issue_type, f"{type(e).__name__}: {e}")
