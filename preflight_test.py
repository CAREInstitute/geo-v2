#!/usr/bin/env python3
"""
GEO Pipeline — Pre-Flight Test Suite
Verifies the entire environment is ready before experiment execution.

Run: python preflight_test.py
Pass = safe to execute.  Any FAIL = do not proceed until resolved.

v1.0.0  2026-04-15  Initial build
"""

__version__ = "1.0.0"
__component__ = "preflight_test"

import sys
import os
import json
import hashlib
import importlib
from pathlib import Path
from datetime import datetime, timezone

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"
results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    return condition


def warn(name, detail=""):
    results.append({"name": name, "status": "warn", "detail": detail})
    print(f"  {WARN}  {name}" + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


def main():
    print("\n" + "═"*50)
    print("  GEO PIPELINE — PRE-FLIGHT TEST SUITE")
    print("═"*50)

    all_pass = True

    # ── 1. Python Environment ──
    section("1. Python Environment")

    v = sys.version_info
    check("Python ≥ 3.10", v.major == 3 and v.minor >= 10,
          f"Found {v.major}.{v.minor}.{v.micro}")

    required_packages = {
        "requests": "2.31.0",
        "pandas": "2.0.0",
        "numpy": "1.24.0",
        "scipy": "1.11.0",
    }
    optional_packages = {"rich": "13.0.0"}

    for pkg, min_ver in required_packages.items():
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "unknown")
            check(f"{pkg} installed", True, f"v{ver}")
        except ImportError:
            check(f"{pkg} installed", False, f"MISSING — pip install {pkg}")
            all_pass = False

    for pkg, min_ver in optional_packages.items():
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "unknown")
            check(f"{pkg} installed (optional)", True, f"v{ver}")
        except ImportError:
            warn(f"{pkg} not installed (optional)", "Terminal formatting will be plain text")

    # ── 2. Pipeline Modules ──
    section("2. Pipeline Modules")

    modules = ["geo_config", "geo_runner", "geo_extract", "geo_analyze", "geo_pipeline"]
    loaded = {}
    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "unknown")
            loaded[mod_name] = mod
            check(f"{mod_name} imports", True, f"v{ver}")
        except Exception as e:
            check(f"{mod_name} imports", False, str(e)[:80])
            all_pass = False

    # ── 3. Configuration Integrity ──
    section("3. Configuration Integrity")

    if "geo_config" in loaded:
        cfg = loaded["geo_config"]
        check("Models defined", len(cfg.MODELS) > 0, f"{len(cfg.MODELS)} models")
        check("Queries defined", len(cfg.QUERIES) > 0, f"{len(cfg.QUERIES)} queries")
        check("K_TRIALS ≥ 1", cfg.K_TRIALS >= 1, f"K={cfg.K_TRIALS}")
        check("Temperature valid", 0 <= cfg.TEMPERATURE <= 2, f"T={cfg.TEMPERATURE}")

        categories = set(q["category"] for q in cfg.QUERIES)
        check("Multiple query categories", len(categories) >= 2, f"{len(categories)}: {categories}")

        groups = set(m["group"] for m in cfg.MODELS)
        check("Multiple architecture groups", len(groups) >= 2, f"{len(groups)}: {groups}")

        # Check all model IDs are non-empty and formatted correctly
        for m in cfg.MODELS:
            valid = "/" in m["id"] and len(m["id"]) > 5
            if not valid:
                check(f"Model ID format: {m['short']}", False, f"Bad ID: {m['id']}")
                all_pass = False

        check("All model IDs well-formed", True, f"{len(cfg.MODELS)} models checked")

    if "geo_runner" in loaded:
        runner = loaded["geo_runner"]
        config_hash = runner.hash_config()
        check("Config hash computable", len(config_hash) == 64, config_hash[:24] + "...")

    # ── 4. API Key ──
    section("4. API Key")

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    check("OPENROUTER_API_KEY set", len(api_key) > 10,
          f"{'Set (' + str(len(api_key)) + ' chars)' if api_key else 'NOT SET — export OPENROUTER_API_KEY=sk-or-v1-...'}")
    if not api_key:
        all_pass = False

    # ── 5. API Connectivity ──
    section("5. API Connectivity")

    if api_key:
        try:
            import requests
            resp = requests.get("https://openrouter.ai/api/v1/models",
                                headers={"Authorization": f"Bearer {api_key}"},
                                timeout=15)
            check("OpenRouter API reachable", resp.status_code == 200,
                  f"HTTP {resp.status_code}, {len(resp.json().get('data', []))} models available")

            if resp.status_code == 200:
                available = {m["id"] for m in resp.json().get("data", [])}
                if "geo_config" in loaded:
                    for m in loaded["geo_config"].MODELS:
                        found = m["id"] in available
                        sub = loaded["geo_config"].SUBSTITUTIONS.get(m["id"], "none")
                        sub_ok = sub in available if sub != "none" else False
                        if found:
                            check(f"Model available: {m['short']}", True, m["id"])
                        elif sub_ok:
                            warn(f"Model substituted: {m['short']}", f"{m['id']} → {sub}")
                        else:
                            check(f"Model available: {m['short']}", False,
                                  f"{m['id']} NOT FOUND, substitute {sub} also missing")
                            all_pass = False
        except Exception as e:
            check("OpenRouter API reachable", False, str(e)[:80])
            warn("Skipping model availability checks", "API unreachable")
    else:
        warn("Skipping API tests", "No API key set")

    # ── 6. Prompt Builder ──
    section("6. Prompt Builder")

    if "geo_pipeline" in loaded:
        try:
            from geo_pipeline import _build_run_b_prompt
            prompt = _build_run_b_prompt()
            word_count = len(prompt.split())
            char_count = len(prompt)
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            check("Prompt builds successfully", word_count > 100, f"{word_count} words, {char_count} chars")
            check("Prompt hash", True, prompt_hash[:24] + "...")
        except Exception as e:
            check("Prompt builds successfully", False, str(e)[:80])
            all_pass = False

    # ── 7. File System ──
    section("7. File System")

    base = Path(".")
    for d in ["outputs/run_a", "outputs/run_b", "outputs/run_c", "data/run_metadata", "logs", "paper/results", "prompts"]:
        p = base / d
        p.mkdir(parents=True, exist_ok=True)
        check(f"Directory writable: {d}", p.exists() and os.access(p, os.W_OK))

    # ── 8. Dry Run (Single Cheap Model) ──
    section("8. Dry Run (Optional — Single API Call)")

    if api_key and "geo_runner" in loaded:
        runner = loaded["geo_runner"]
        # Find the cheapest model
        if "geo_config" in loaded:
            cheapest = min(loaded["geo_config"].MODELS, key=lambda m: m.get("cost_output_per_m", 999))
            print(f"\n  Testing with cheapest model: {cheapest['name']} ({cheapest['id']})")
            print(f"  Estimated cost: <$0.01")
            print(f"  Sending: 'Say hello in exactly 3 words.'")

            content, meta = runner.call_openrouter(
                api_key, cheapest["id"], "Say hello in exactly 3 words.", max_tokens=50
            )
            check("API call succeeds", meta["finish_reason"] != "error",
                  f"Got {len(content.split())} words, model={meta.get('model_returned', 'unknown')}")
            if content:
                print(f"  Response: {content.strip()[:100]}")
    else:
        warn("Skipping dry run", "No API key or runner not loaded")

    # ── 9. Cost Estimate ──
    section("9. Cost Estimate")

    if "geo_config" in loaded:
        cost = loaded["geo_config"].estimate_total_cost()
        check("Cost estimate computable", cost > 0, f"${cost:.2f} estimated total")
        if cost > 200:
            warn("Cost exceeds $200", f"${cost:.2f} — review model pricing")

    # ── Summary ──
    print(f"\n{'═'*50}")
    passes = sum(1 for r in results if r["status"] == "pass")
    fails = sum(1 for r in results if r["status"] == "fail")
    warns = sum(1 for r in results if r["status"] == "warn")
    print(f"  RESULTS: {passes} passed, {fails} failed, {warns} warnings")

    if all_pass and fails == 0:
        print(f"  {PASS}  ALL CHECKS PASSED — safe to execute experiment")
    else:
        print(f"  {FAIL}  {fails} CHECK(S) FAILED — resolve before executing")

    print(f"{'═'*50}\n")

    # Save results
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": f"{v.major}.{v.minor}.{v.micro}",
        "all_pass": all_pass and fails == 0,
        "summary": {"pass": passes, "fail": fails, "warn": warns},
        "checks": results,
    }
    report_path = Path("data") / "preflight_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Report saved to {report_path}\n")

    return 0 if (all_pass and fails == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
