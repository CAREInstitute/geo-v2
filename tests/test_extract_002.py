"""
EXTRACT-002 unit test: citation-footer false positives.

The 4 phrases added to FALSE_POSITIVE_BRANDS in v3.0.0 should be
filtered out when they appear at the end of search-augmented model
responses. v1 incorrectly extracted these as brands; v3.0.0 filters them.

Reference: CRITICAL geo_extraction_bug_report.md (46 false-positive rows
in v1 production data; this test verifies the 4 specific phrase patterns
that produced the bulk of those 46 rows).

Patch: geo_extract.py v3.0.0 (EXTRACT-002)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geo_extract import extract_brands_from_response, FALSE_POSITIVE_BRANDS


CITATION_FOOTER_PHRASES = [
    "if web sources were consulted",
    "web sources consulted briefly",
    "sources consulted generally",
    "web sources consulted",
]


def test_extract_002_phrases_present_in_filter():
    """All 4 EXTRACT-002 phrases must be in the FALSE_POSITIVE_BRANDS set."""
    missing = [p for p in CITATION_FOOTER_PHRASES if p not in FALSE_POSITIVE_BRANDS]
    assert not missing, f"Missing from FALSE_POSITIVE_BRANDS: {missing}"


def test_extract_002_filter_in_list_context():
    """Each phrase, when extracted as a list-item brand, should be filtered."""
    failures = []
    for phrase in CITATION_FOOTER_PHRASES:
        # Title-case it the way it would appear after typical citation footers
        title_cased = " ".join(w.capitalize() for w in phrase.split())
        input_text = f"1. **{title_cased}** \u2014 see references section"
        result = extract_brands_from_response(input_text)
        extracted = [r["brand"].lower() for r in result]
        if phrase in extracted:
            failures.append(
                f"  Phrase '{phrase}' was NOT filtered.\n"
                f"  Input: {input_text!r}\n"
                f"  Got: {[r['brand'] for r in result]}"
            )
    assert not failures, "EXTRACT-002 failures:\n" + "\n".join(failures)


def test_extract_002_realistic_footer_pattern():
    """Realistic v1 false-positive pattern: citation footer at end of response."""
    realistic_input = (
        "1. **HubSpot** \u2014 best CRM for SMBs\n"
        "2. **Salesforce** \u2014 enterprise leader\n"
        "\n"
        "**Web Sources Consulted** \u2014 see appendix\n"
        "**If Web Sources Were Consulted** \u2014 disclosed below\n"
    )
    result = extract_brands_from_response(realistic_input)
    extracted = [r["brand"].lower() for r in result]
    legitimate = ["hubspot", "salesforce"]
    for brand in legitimate:
        assert brand in extracted, f"Legitimate brand '{brand}' should be extracted"
    for fp in ["web sources consulted", "if web sources were consulted"]:
        assert fp not in extracted, f"False positive '{fp}' should be filtered, but got: {extracted}"


if __name__ == "__main__":
    test_extract_002_phrases_present_in_filter()
    test_extract_002_filter_in_list_context()
    test_extract_002_realistic_footer_pattern()
    print("All EXTRACT-002 tests passed.")
