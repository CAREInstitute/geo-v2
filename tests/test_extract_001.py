"""
EXTRACT-001 unit test: slash-compound brand normalization.

Covers the 7 confirmed-affected patterns from the v1 bug report.
Each pattern, when bolded and placed in a list context, should be
extracted as its FIRST half only — not the full slash-compound.

Reference: CRITICAL geo_extraction_bug_report.md
Patch: geo_extract.py v3.0.0 (EXTRACT-001)
"""

import sys
from pathlib import Path

# Make geo_extract importable when running pytest from repo root or tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geo_extract import extract_brands_from_response


# Each test case: (input_text, expected_primary_brand)
SLASH_COMPOUND_CASES = [
    (
        "1. **Apple Watch Series 10/Ultra 2** \u2014 best fitness tracker overall",
        "Apple Watch Series 10",
    ),
    (
        "2. **Series 9/Ultra 2** \u2014 last-gen Apple Watch lineup",
        "Series 9",
    ),
    (
        "3. **Vivosmart 5/Forerunner 265** \u2014 Garmin tracker family",
        "Vivosmart 5",
    ),
    (
        "4. **Venu 3/Venu 3S** \u2014 Garmin smartwatch range",
        "Venu 3",
    ),
    (
        "5. **Series 11/Ultra 3** \u2014 newest Apple Watch tier",
        "Series 11",
    ),
    (
        "6. **Home Assistant Green/Home Assistant ecosystem** \u2014 smart home hub",
        "Home Assistant Green",
    ),
    (
        "7. **Amazon Echo (4th Gen)/Alexa ecosystem** \u2014 voice assistant platform",
        "Amazon Echo",
    ),
]


def test_extract_001_slash_compound_normalization():
    """Each slash-compound bolded brand resolves to its first half."""
    failures = []
    for input_text, expected in SLASH_COMPOUND_CASES:
        result = extract_brands_from_response(input_text)
        extracted_brands = [r["brand"] for r in result]
        if expected not in extracted_brands:
            failures.append(
                f"  Input: {input_text!r}\n"
                f"  Expected to find: {expected!r}\n"
                f"  Got: {extracted_brands}"
            )
    assert not failures, "EXTRACT-001 failures:\n" + "\n".join(failures)


def test_extract_001_no_slash_compounds_leak_through():
    """The full slash-compound form should NOT appear in extractions."""
    failures = []
    for input_text, expected in SLASH_COMPOUND_CASES:
        result = extract_brands_from_response(input_text)
        extracted_brands = [r["brand"] for r in result]
        for brand in extracted_brands:
            if "/" in brand:
                failures.append(
                    f"  Input: {input_text!r}\n"
                    f"  Slash-compound leaked through: {brand!r}"
                )
    assert not failures, "EXTRACT-001 leak failures:\n" + "\n".join(failures)


if __name__ == "__main__":
    test_extract_001_slash_compound_normalization()
    test_extract_001_no_slash_compounds_leak_through()
    print("All EXTRACT-001 tests passed.")
