#!/usr/bin/env python3
"""Test script to verify PDF filtering logic processes all relevant PDFs."""

# Mock data simulating Kungsängen with 3 PDFs where only 1 has keyword in title
mock_documents = [
    {
        "title": "Skjutvarning vecka 18",  # Has keyword "skjutvarning"
        "url": "/pdf/kungsangen-v18.pdf"
    },
    {
        "title": "Vecka 19",  # NO keyword
        "url": "/pdf/kungsangen-v19.pdf"
    },
    {
        "title": "Beslut om tillträde",  # Has keyword "tillträde" (but not in list)
        "url": "/pdf/kungsangen-beslut.pdf"
    },
    {
        "title": "Karta över området",  # Should be filtered out (map)
        "url": "/pdf/kungsangen-karta.pdf"
    }
]

# OLD LOGIC (buggy - only processes docs with specific keywords)
print("=== OLD LOGIC (BUGGY) ===")
restriction_docs_old = [
    d for d in mock_documents
    if any(kw in d.get("title", "").lower()
           for kw in ["tilltradesforbud", "skjutvarning", "avlysning", "varningsmeddelande"])
]

# Om inga specifika, ta alla icke-karta PDF:er
if not restriction_docs_old:
    restriction_docs_old = [
        d for d in mock_documents
        if "karta" not in d.get("title", "").lower()
        and d.get("url", "").lower().endswith(".pdf")
    ]

print(f"Processed {len(restriction_docs_old)} PDFs:")
for doc in restriction_docs_old:
    print(f"  - {doc['title']} → {doc['url']}")

# NEW LOGIC (fixed - processes all non-map PDFs)
print("\n=== NEW LOGIC (FIXED) ===")
restriction_docs_new = [
    d for d in mock_documents
    if d.get("url", "").lower().endswith(".pdf")
    and "karta" not in d.get("title", "").lower()
]

print(f"Processed {len(restriction_docs_new)} PDFs:")
for doc in restriction_docs_new:
    print(f"  - {doc['title']} → {doc['url']}")

# Verification
print("\n=== VERIFICATION ===")
if len(restriction_docs_old) == 1:
    print("❌ OLD LOGIC: Only processes 1 PDF (buggy)")
else:
    print(f"⚠️  OLD LOGIC: Processes {len(restriction_docs_old)} PDFs")

if len(restriction_docs_new) == 3:
    print("✅ NEW LOGIC: Processes all 3 relevant PDFs (correct)")
else:
    print(f"❌ NEW LOGIC: Processes {len(restriction_docs_new)} PDFs (expected 3)")

print("\nSummary:")
print(f"  Old: {len(restriction_docs_old)} PDFs → User only sees data from 1 PDF")
print(f"  New: {len(restriction_docs_new)} PDFs → User sees data from all 3 PDFs")
print(f"  Improvement: +{len(restriction_docs_new) - len(restriction_docs_old)} PDFs processed")
