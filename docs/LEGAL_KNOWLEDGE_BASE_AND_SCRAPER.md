# Legal Knowledge Base and Scraper Documentation

## 1. Purpose

A **legal knowledge base** supports future **retrieval-augmented** answers, **citations**, and **hallucination reduction**. A **scraper/parser pipeline** turns raw legal sources into structured JSON for storage and later normalization.

**Repository scan (May 2026):** No `property_rights/` directory (with `acts/`, `articles/`, etc.) was found at the repository root or shallow subtree. **Scraper implementation** (e.g. Selenium, BeautifulSoup) was **not** found in Python source under the scanned paths—**To be verified** if it lives elsewhere or is not yet committed.

This document therefore defines the **intended** layout and schemas for when that work lands.

---

## 2. Folder Structure (Target)

```text
property_rights/
├── acts/
├── articles/
├── cases/
├── constitution/
└── sections/
```

---

## 3. Folder Details

| Folder | Intended content |
|--------|------------------|
| **acts/** | Full or chunked legislative text (e.g. property-related Acts). |
| **articles/** | Constitutional articles relevant to property, equality, remedies, etc. |
| **cases/** | Judgments / headnotes / extracted holdings (as permitted). |
| **constitution/** | Constitutional documents or PDF-derived extracts. |
| **sections/** | Section-level extracts (strong fit for future retrieval units). |

---

## 4. Current JSON Schemas (Illustrative)

These are **reference shapes** for parsed HTML/PDF content. Actual files in-repo: **To be verified** (none found in scan).

### HTML-derived document

```json
{
  "source_file": "...",
  "document_type": "html",
  "title": "...",
  "sections": [
    {
      "heading": "...",
      "level": 1,
      "content": []
    }
  ],
  "links": []
}
```

### PDF-derived document

```json
{
  "source_file": "...",
  "document_type": "pdf",
  "title": "...",
  "page_count": 10,
  "extracted_pages": [
    {
      "page_number": 1,
      "text": "..."
    }
  ]
}
```

---

## 5. Future Normalized Legal Chunk Schema

```json
{
  "chunk_id": "property_sections_001",
  "source_type": "section",
  "document_title": "Transfer of Property Act",
  "heading": "Section heading",
  "text": "Actual legal text here",
  "jurisdiction": "India",
  "domain": "property_law",
  "issue_tags": [
    "eviction",
    "possession",
    "tenancy",
    "title"
  ],
  "citation": "Act / Section / Case name if available",
  "source_file": "original file path"
}
```

---

## 6. Future RAG Use

When normalized chunks and a vector index exist, the platform could:

- Retrieve **top-k** relevant snippets for a citizen scenario or student argument  
- Display **source-grounded** explanations (reducing unsupported claims)  
- Support **rule matching** and **citation display**  
- Combine with the **Scenario Analyzer** (today **API-only MVP by design**, not RAG-based unless implemented)

**Important:** Until RAG is implemented in code, the Scenario Analyzer and mock-trial models should **not** be documented as RAG-backed.

---

## 7. Relationship to This Repository

| Item | Status |
|------|--------|
| `dataset_generation/` scripts | **Completed** for synthetic **JSONL** training data (uses **Gemini** API). |
| `all_models/` legal training artifacts | **Completed** (datasets, adapters, benchmarks). |
| On-disk **scraped statute/case corpus** under `property_rights/` | **Not found** in scan — **Planned** / **To be verified**. |
