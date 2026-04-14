#!/usr/bin/env python3
"""
GEO Pipeline — Operator Logbook
Structured run log for human review after autonomous (Cowork) or manual execution.

The logbook answers five questions:
  1. What was attempted?
  2. What succeeded / failed?
  3. Were any code modifications made? (with diffs)
  4. Where are results stored?
  5. What should the operator do next?

Usage:
  # Automatically created during pipeline execution
  python geo_pipeline.py full  # → creates logbook entry

  # Review the latest logbook
  python operator_logbook.py review

  # Review a specific logbook
  python operator_logbook.py review --file logs/logbook_20260415_120000.md

v1.0.0  2026-04-15  Initial build
"""

__version__ = "1.0.0"
__component__ = "operator_logbook"

import os
import sys
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path


class OperatorLogbook:
    """Structured logbook for experiment runs.

    Creates a markdown file that a human can read to understand
    exactly what happened during an autonomous run.
    """

    def __init__(self, base_dir, run_name="experiment"):
        self.base_dir = Path(base_dir)
        self.log_dir = self.base_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.ts = datetime.now(timezone.utc)
        ts_str = self.ts.strftime("%Y%m%d_%H%M%S")
        self.log_path = self.log_dir / f"logbook_{ts_str}.md"

        self.entries = []
        self.code_changes = []
        self.output_files = []
        self.errors = []
        self.warnings = []

        # Snapshot file hashes at start (to detect modifications)
        self.initial_hashes = self._snapshot_code_hashes()

        self._write_header(run_name)

    def _write_header(self, run_name):
        """Write the logbook header."""
        self._raw(f"# Operator Logbook — {run_name}")
        self._raw(f"")
        self._raw(f"**Started:** {self.ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self._raw(f"**Pipeline version:** (captured at close)")
        self._raw(f"**Status:** IN PROGRESS")
        self._raw(f"")
        self._raw(f"---")
        self._raw(f"")

    def step_start(self, step_name, description=""):
        """Log the start of a pipeline step."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.entries.append({
            "step": step_name,
            "status": "started",
            "start_time": ts,
            "description": description,
        })
        self._raw(f"## [{ts}] {step_name}")
        if description:
            self._raw(f"")
            self._raw(f"{description}")
        self._raw(f"")

    def step_pass(self, step_name, detail=""):
        """Log a successful step completion."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        for e in reversed(self.entries):
            if e["step"] == step_name and e["status"] == "started":
                e["status"] = "pass"
                e["end_time"] = ts
                e["detail"] = detail
                break
        self._raw(f"**Result:** ✅ PASS" + (f" — {detail}" if detail else ""))
        self._raw(f"")

    def step_fail(self, step_name, error_msg):
        """Log a failed step."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        for e in reversed(self.entries):
            if e["step"] == step_name and e["status"] == "started":
                e["status"] = "fail"
                e["end_time"] = ts
                e["error"] = error_msg
                break
        self.errors.append({"step": step_name, "error": error_msg, "time": ts})
        self._raw(f"**Result:** ❌ FAIL — {error_msg}")
        self._raw(f"")

    def step_warn(self, step_name, warning_msg):
        """Log a warning during a step."""
        self.warnings.append({"step": step_name, "warning": warning_msg})
        self._raw(f"**Warning:** ⚠️ {warning_msg}")
        self._raw(f"")

    def log_code_change(self, file_path, reason, before_hash=None, after_hash=None):
        """Log a code modification with reason."""
        change = {
            "file": str(file_path),
            "reason": reason,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        }
        self.code_changes.append(change)
        self._raw(f"### Code Modification: `{file_path}`")
        self._raw(f"")
        self._raw(f"- **Reason:** {reason}")
        if before_hash and after_hash:
            self._raw(f"- **Before:** `{before_hash[:16]}...`")
            self._raw(f"- **After:** `{after_hash[:16]}...`")
        self._raw(f"")

    def log_output(self, file_path, description=""):
        """Register an output file location."""
        self.output_files.append({"path": str(file_path), "description": description})

    def log_info(self, message):
        """Log a general informational message."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._raw(f"[{ts}] {message}")
        self._raw(f"")

    def close(self, final_status="completed"):
        """Close the logbook with summary and next steps."""
        end_ts = datetime.now(timezone.utc)
        elapsed = (end_ts - self.ts).total_seconds()

        # Detect code changes since start
        final_hashes = self._snapshot_code_hashes()
        detected_changes = []
        for fname, initial_hash in self.initial_hashes.items():
            final_hash = final_hashes.get(fname)
            if final_hash and final_hash != initial_hash:
                detected_changes.append(fname)

        # Write summary sections
        self._raw(f"---")
        self._raw(f"")
        self._raw(f"## Summary")
        self._raw(f"")
        self._raw(f"**Finished:** {end_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self._raw(f"**Elapsed:** {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
        self._raw(f"**Final status:** {final_status.upper()}")
        self._raw(f"")

        # Steps summary
        passes = sum(1 for e in self.entries if e.get("status") == "pass")
        fails = sum(1 for e in self.entries if e.get("status") == "fail")
        self._raw(f"### Steps: {passes} passed, {fails} failed")
        self._raw(f"")
        for e in self.entries:
            icon = "✅" if e.get("status") == "pass" else "❌" if e.get("status") == "fail" else "⏳"
            self._raw(f"- {icon} {e['step']}" + (f" — {e.get('detail', e.get('error', ''))}" if e.get("detail") or e.get("error") else ""))
        self._raw(f"")

        # Code changes
        self._raw(f"### Code Modifications: {len(self.code_changes) + len(detected_changes)}")
        self._raw(f"")
        if not self.code_changes and not detected_changes:
            self._raw(f"No code modifications were made during this run.")
        else:
            for c in self.code_changes:
                self._raw(f"- `{c['file']}` — {c['reason']}")
            for fname in detected_changes:
                if not any(c["file"].endswith(fname) for c in self.code_changes):
                    self._raw(f"- `{fname}` — MODIFIED (detected by hash comparison, reason not logged)")
        self._raw(f"")

        # Output files
        self._raw(f"### Output Files: {len(self.output_files)}")
        self._raw(f"")
        if self.output_files:
            for f in self.output_files:
                self._raw(f"- `{f['path']}`" + (f" — {f['description']}" if f['description'] else ""))
        else:
            self._raw(f"No output files were registered.")
        self._raw(f"")

        # Errors
        if self.errors:
            self._raw(f"### Errors: {len(self.errors)}")
            self._raw(f"")
            for e in self.errors:
                self._raw(f"- [{e['time']}] **{e['step']}**: {e['error']}")
            self._raw(f"")

        # Warnings
        if self.warnings:
            self._raw(f"### Warnings: {len(self.warnings)}")
            self._raw(f"")
            for w in self.warnings:
                self._raw(f"- **{w['step']}**: {w['warning']}")
            self._raw(f"")

        # Next steps
        self._raw(f"### Operator Action Required")
        self._raw(f"")
        if fails > 0:
            self._raw(f"1. Review the {fails} failed step(s) above")
            self._raw(f"2. Check `data/preflight_report.json` for diagnostic details")
            self._raw(f"3. Fix the issue and re-run the failed step(s)")
        elif len(self.code_changes) + len(detected_changes) > 0:
            self._raw(f"1. Review the code modifications listed above")
            self._raw(f"2. Verify changes are intentional and correct")
            self._raw(f"3. Update CHANGELOG.md if not already done")
            self._raw(f"4. Commit changes: `git add -A && git commit -m '[pipeline] Cowork modifications'`")
        else:
            self._raw(f"1. Review output files listed above")
            self._raw(f"2. Run `python geo_pipeline.py manifest` to generate reproducibility manifest")
            self._raw(f"3. Commit results: `git add data/ paper/ && git commit -m '[data] Experiment results'`")
        self._raw(f"")

        # ── Post-Mortem: Framework Feedback ──
        self._raw(f"### Post-Mortem: Framework Feedback")
        self._raw(f"")
        self._raw(f"Review these items and update `FRAMEWORK.md` Section 6 (Lessons Learned):")
        self._raw(f"")

        framework_items = []

        # Auto-generate feedback items from run events
        if fails > 0:
            fail_steps = [e["step"] for e in self.entries if e.get("status") == "fail"]
            item = f"**Failure pattern:** {fails} step(s) failed ({', '.join(fail_steps)}). Is this a known failure mode? If not, add a decision tree entry to `COWORK_INSTRUCTIONS.md`."
            framework_items.append(item)
            self._raw(f"- {item}")

        if self.code_changes:
            change_files = list(set(c["file"] for c in self.code_changes))
            item = f"**Code modifications:** {len(self.code_changes)} change(s) to {', '.join(change_files)}. Were these workarounds for framework gaps? If so, integrate the fix into the base pipeline and document in `CHANGELOG.md`."
            framework_items.append(item)
            self._raw(f"- {item}")

        if detected_changes:
            item = f"**Unlogged code changes:** {len(detected_changes)} file(s) modified without explicit logging. Review whether `COWORK_INSTRUCTIONS.md` permission boundaries need tightening."
            framework_items.append(item)
            self._raw(f"- {item}")

        if self.warnings:
            warn_steps = list(set(w["step"] for w in self.warnings))
            item = f"**Warnings:** {len(self.warnings)} warning(s) across {', '.join(warn_steps)}. Are any of these recurring patterns that should become preflight checks?"
            framework_items.append(item)
            self._raw(f"- {item}")

        # Check for quality flag patterns
        quality_flags_found = {}
        meta_dir = self.base_dir / "data" / "run_metadata"
        if meta_dir.exists():
            for mf in meta_dir.glob("*.json"):
                try:
                    meta = json.loads(mf.read_text())
                    for flag in meta.get("quality_flags", []):
                        quality_flags_found[flag] = quality_flags_found.get(flag, 0) + 1
                except Exception:
                    pass

        if quality_flags_found:
            flag_summary = ", ".join(f"{k}({v})" for k, v in sorted(quality_flags_found.items()))
            item = f"**Quality flags:** {sum(quality_flags_found.values())} total across outputs: {flag_summary}. Do any of these indicate extraction patterns that need updating or model behaviors that need documenting?"
            framework_items.append(item)
            self._raw(f"- {item}")

        # Check for resume events (indicates interrupted runs)
        skip_count = sum(1 for e in self.entries
                        if e.get("detail") and "skipped_existing" in str(e.get("detail", "")))
        if skip_count > 0:
            item = f"**Resume events:** {skip_count} trials were skipped (already completed). Was the pipeline interrupted? If crashes are recurring, investigate the root cause."
            framework_items.append(item)
            self._raw(f"- {item}")

        # Cost analysis
        total_cost = 0
        if meta_dir.exists():
            for mf in meta_dir.glob("*.json"):
                try:
                    meta = json.loads(mf.read_text())
                    total_cost += meta.get("call_cost_usd", 0)
                except Exception:
                    pass

        if total_cost > 0:
            from geo_config import estimate_total_cost
            estimated = estimate_total_cost()
            ratio = total_cost / estimated if estimated > 0 else 0
            if ratio > 1.5:
                item = f"**Cost overrun:** Actual ${total_cost:.2f} vs estimated ${estimated:.2f} ({ratio:.1f}×). Update `estimate_total_cost()` assumptions (likely output tokens are higher than 8K estimate)."
                framework_items.append(item)
                self._raw(f"- {item}")
            elif ratio < 0.5:
                item = f"**Cost underrun:** Actual ${total_cost:.2f} vs estimated ${estimated:.2f} ({ratio:.1f}×). Models may be producing shorter responses than expected — check if outputs are complete."
                framework_items.append(item)
                self._raw(f"- {item}")
            else:
                self._raw(f"- **Cost tracking:** Actual ${total_cost:.2f} vs estimated ${estimated:.2f} ({ratio:.1f}×) — within expected range.")

        if not framework_items:
            self._raw(f"- No framework issues detected. Clean run.")

        self._raw(f"")
        self._raw(f"*After reviewing, update `FRAMEWORK.md` Section 6 and commit:*")
        self._raw(f"*`git add FRAMEWORK.md && git commit -m '[docs] Post-mortem framework update'`*")
        self._raw(f"")

        # Version info
        self._raw(f"### Pipeline Versions (at close)")
        self._raw(f"")
        try:
            from geo_pipeline import _get_version_info
            for comp, ver in _get_version_info().items():
                self._raw(f"- `{comp}` v{ver}")
        except ImportError:
            self._raw(f"(could not load version info)")
        self._raw(f"")

        # Save structured data alongside markdown
        structured = {
            "started": self.ts.isoformat(),
            "finished": end_ts.isoformat(),
            "elapsed_seconds": elapsed,
            "status": final_status,
            "steps": self.entries,
            "code_changes": self.code_changes,
            "detected_changes": detected_changes,
            "output_files": self.output_files,
            "errors": self.errors,
            "warnings": self.warnings,
            "framework_feedback": framework_items,
            "quality_flags_summary": quality_flags_found,
            "total_cost_usd": total_cost,
        }
        json_path = self.log_path.with_suffix(".json")
        json_path.write_text(json.dumps(structured, indent=2), encoding="utf-8")

        return str(self.log_path)

    def _raw(self, line):
        """Append a raw line to the logbook."""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _snapshot_code_hashes(self):
        """Hash all .py files to detect modifications."""
        hashes = {}
        for f in self.base_dir.glob("*.py"):
            try:
                content = f.read_bytes()
                hashes[f.name] = hashlib.sha256(content).hexdigest()
            except Exception:
                pass
        return hashes


# ─── Review Command ──────────────────────────────────────────────────────────

def review_logbook(filepath=None):
    """Print the latest (or specified) logbook for operator review."""
    log_dir = Path("logs")

    if filepath:
        p = Path(filepath)
    else:
        # Find the most recent logbook
        logbooks = sorted(log_dir.glob("logbook_*.md"), reverse=True)
        if not logbooks:
            print("No logbooks found in logs/")
            return 1
        p = logbooks[0]

    if not p.exists():
        print(f"Logbook not found: {p}")
        return 1

    print(p.read_text(encoding="utf-8"))

    # Also print structured summary if available
    json_path = p.with_suffix(".json")
    if json_path.exists():
        data = json.loads(json_path.read_text())
        passes = sum(1 for e in data.get("steps", []) if e.get("status") == "pass")
        fails = sum(1 for e in data.get("steps", []) if e.get("status") == "fail")
        print(f"\n{'═'*50}")
        print(f"  QUICK STATUS: {passes} passed, {fails} failed, "
              f"{len(data.get('code_changes', []))} code changes, "
              f"{len(data.get('output_files', []))} outputs")
        print(f"{'═'*50}\n")

    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GEO Pipeline Operator Logbook")
    sub = parser.add_subparsers(dest="command")
    p_review = sub.add_parser("review", help="Review the latest logbook")
    p_review.add_argument("--file", help="Specific logbook file to review")
    args = parser.parse_args()

    if args.command == "review":
        sys.exit(review_logbook(args.file))
    else:
        parser.print_help()
