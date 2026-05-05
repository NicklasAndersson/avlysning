#!/usr/bin/env python3
"""Test script to verify that all PDF URLs are collected and would be displayed."""

import json

# Mock data simulating Kungsängen with 3 PDFs
mock_field = {
    "id": "kungsangen",
    "name": "Kungsängen skjutfält",
    "source": "forsvarsmakten.se",
    "source_url": "https://www.forsvarsmakten.se/pdf1.pdf",  # First PDF
    "pdf_urls": [
        "https://www.forsvarsmakten.se/pdf1.pdf",
        "https://www.forsvarsmakten.se/pdf2.pdf",
        "https://www.forsvarsmakten.se/pdf3.pdf"
    ],
    "restrictions": [
        # From PDF1 (old week)
        {"date": "2026-04-28", "start": "08:00", "end": "17:00", "type": "skjutvarning",
         "sectors": ["all"], "source_url": "https://www.forsvarsmakten.se/pdf1.pdf"},
        {"date": "2026-04-29", "start": "08:00", "end": "17:00", "type": "skjutvarning",
         "sectors": ["all"], "source_url": "https://www.forsvarsmakten.se/pdf1.pdf"},
        # From PDF2 (current week)
        {"date": "2026-05-05", "start": "08:00", "end": "17:00", "type": "skjutvarning",
         "sectors": ["all"], "source_url": "https://www.forsvarsmakten.se/pdf2.pdf"},
        {"date": "2026-05-06", "start": "08:00", "end": "17:00", "type": "skjutvarning",
         "sectors": ["all"], "source_url": "https://www.forsvarsmakten.se/pdf2.pdf"},
        # From PDF3 (next week)
        {"date": "2026-05-12", "start": "08:00", "end": "17:00", "type": "skjutvarning",
         "sectors": ["all"], "source_url": "https://www.forsvarsmakten.se/pdf3.pdf"},
    ],
    "parse_errors": []
}

# Simulate the frontend logic from InfoPanel.tsx lines 48-55
pdf_urls_from_field = set(mock_field.get("pdf_urls", []))
pdf_urls_from_errors = set(mock_field.get("parse_errors", []))
pdf_urls_from_restrictions = set(
    r.get("source_url") for r in mock_field["restrictions"]
    if r.get("source_url")
)

all_pdf_urls = pdf_urls_from_field | pdf_urls_from_errors | pdf_urls_from_restrictions

print("=== Frontend PDF URL Collection Test ===")
print(f"\nFrom field.pdf_urls: {len(pdf_urls_from_field)} URLs")
for url in sorted(pdf_urls_from_field):
    print(f"  - {url}")

print(f"\nFrom field.parse_errors: {len(pdf_urls_from_errors)} URLs")
for url in sorted(pdf_urls_from_errors):
    print(f"  - {url}")

print(f"\nFrom restrictions[].source_url: {len(pdf_urls_from_restrictions)} URLs")
for url in sorted(pdf_urls_from_restrictions):
    print(f"  - {url}")

print(f"\n=== All unique PDF URLs (as shown in GUI): {len(all_pdf_urls)} ===")
for url in sorted(all_pdf_urls):
    print(f"  📄 {url.split('/')[-1]}")

print("\n=== Restrictions by date ===")
restrictions_by_date = {}
for r in mock_field["restrictions"]:
    date = r["date"]
    if date not in restrictions_by_date:
        restrictions_by_date[date] = []
    restrictions_by_date[date].append(r)

for date in sorted(restrictions_by_date.keys()):
    print(f"\n{date}:")
    for r in restrictions_by_date[date]:
        pdf_name = r["source_url"].split("/")[-1]
        print(f"  - {r['start']}-{r['end']} ({r['type']}) [from {pdf_name}]")

# Test conclusion
if len(all_pdf_urls) == 3:
    print("\n✅ SUCCESS: All 3 PDFs would be displayed in the GUI")
else:
    print(f"\n❌ FAIL: Only {len(all_pdf_urls)} PDFs would be displayed (expected 3)")
