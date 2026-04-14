# Global Operator Runbook
# Provide this document to Claude Cowork along with geo_pipeline.tar.gz

---

## Mission Brief

You are operating the GEO Cross-Model Brand Visibility experiment pipeline. Your job is to get this experiment from a tar.gz archive to completed results with a full audit trail.

The experiment sends 20 commercial queries to 10 frontier AI models (5 trials each = 1,000 total API calls) via OpenRouter, extracts which brands each model recommends, and measures whether different AI platforms recommend different brands for identical queries.

**Your deliverables:**
1. All 1,000 API responses saved to `outputs/run_b/`
2. Brand extraction data in `data/brand_visibility_matrix.csv`
3. Statistical analysis results in `paper/results/`
4. A completed operator logbook at `logs/logbook_*.md`
5. A reproducibility manifest at `data/manifest.json`
6. All results committed to git (but NOT pushed — operator reviews first)

**Estimated time:** 6-8 hours (most is waiting for temporal spacing between search-augmented model trials)
**Estimated cost:** ~$53 in OpenRouter API credits
**Budget ceiling:** $150 (pipeline halts automatically if exceeded)

---

## Your Files

Extract the archive first:
```bash
tar -xzf geo_pipeline.tar.gz
cd geo_pipeline
```

Read these files in this order:
1. `COWORK_INSTRUCTIONS.md` — Your permission boundaries and decision trees (READ THIS FIRST)
2. `OPERATOR_GUIDE.md` — Step-by-step execution instructions
3. `README.md` — Quick reference for commands and file inventory

Key reference (consult when needed):
- `ARCHITECTURE.md` — Design rationale for every decision
- `CHANGELOG.md` — What changed and why

---

## Execution Sequence

Follow these steps in order. Do not skip steps. Log everything.

### Step 1: Setup Environment

```bash
pip install -r requirements.txt
```

Verify the API key is available:
```bash
echo "${OPENROUTER_API_KEY:0:10}"
```

If the API key is not set, check for a `.env` file or `~/.bashrc`. If truly absent, **stop and report** — you cannot proceed without an API key.

### Step 2: Run Pre-Flight Tests

```bash
python preflight_test.py
```

Every check must pass (except API-related checks if the key is being set up). Review `data/preflight_report.json` for any failures. Fix failures using the troubleshooting table in `COWORK_INSTRUCTIONS.md`. Re-run until all checks pass.

### Step 3: Initialize Git Repository

```bash
git init
git add .
git commit -m "Pre-registration: GEO pipeline v3.0"
git tag -a "pre-reg-v1.0" -m "Pre-registered experimental protocol"
```

### Step 4: Test Run (Fast Mode)

Run a quick test without temporal spacing:
```bash
python geo_pipeline.py full --fast
```

After completion, verify:
```bash
ls outputs/run_b/*.md | wc -l
# Expected: 50 files (10 models × 5 runs)

# Check word counts
for f in outputs/run_b/*_run1.md; do
  echo "$(wc -w < "$f") — $(basename "$f")"
done
# Expected: 200-8000 words per file
```

**Decision point:**
- If all 50 files exist with reasonable content → proceed to Step 5
- If some models failed → consult decision trees in `COWORK_INSTRUCTIONS.md`, fix, and re-run (resume will skip completed trials)
- If >3 models failed → likely an API issue; wait 10 minutes and retry

### Step 5: Clean Test Data and Run Academic Mode

```bash
rm -rf outputs/run_b/* data/run_metadata/*
python geo_pipeline.py full
```

This will take ~5-6 hours due to temporal spacing for search-augmented models. The pipeline will print progress to stdout and log to `logs/experiment_*.log`.

**During execution, monitor for:**
- Budget warnings (cumulative spend displayed after each trial)
- Quality flags (EMPTY_RESPONSE, POSSIBLE_REFUSAL, etc.)
- Repeated failures on the same model

**If the pipeline crashes or you need to interrupt:**
- Just re-run `python geo_pipeline.py full` — resume is built in
- Already-completed trials (files with >200 words) will be skipped automatically

### Step 6: Post-Execution Verification

```bash
# Verify all outputs exist
echo "Output files: $(ls outputs/run_b/*.md | wc -l)"
# Expected: 50

# Verify metadata
echo "Metadata files: $(ls data/run_metadata/*.json | wc -l)"
# Expected: 50

# Check for quality issues
python -c "
import json
from pathlib import Path
flags = {}
for f in Path('data/run_metadata').glob('*.json'):
    meta = json.loads(f.read_text())
    for flag in meta.get('quality_flags', []):
        flags[flag] = flags.get(flag, 0) + 1
print('Quality flags:', flags if flags else 'None — all clean')
"

# Run remaining analysis steps (if full pipeline didn't complete them)
python geo_pipeline.py extract
python geo_pipeline.py stochasticity
python geo_pipeline.py analyze
python geo_pipeline.py report
python geo_pipeline.py manifest
```

### Step 7: Review and Commit

```bash
# Review the logbook
python operator_logbook.py review

# Review key results
cat paper/results_summary.md

# Commit everything
git add -A
git commit -m "[data] Experiment complete — $(date +%Y-%m-%d)"
```

**Do NOT push to remote.** The operator will review the logbook and results before pushing.

### Step 8: Final Report

Print a summary for the operator:

```bash
echo "════════════════════════════════════════"
echo "  GEO EXPERIMENT — EXECUTION COMPLETE"
echo "════════════════════════════════════════"
echo ""
echo "Output files:   $(ls outputs/run_b/*.md 2>/dev/null | wc -l) / 50 expected"
echo "Metadata files: $(ls data/run_metadata/*.json 2>/dev/null | wc -l) / 50 expected"
echo ""
python -c "
import json
from pathlib import Path
# Cost
total = sum(json.loads(f.read_text()).get('call_cost_usd', 0) for f in Path('data/run_metadata').glob('*.json'))
print(f'Total spend:    \${total:.2f}')

# Manifest
m = Path('data/manifest.json')
if m.exists():
    mdata = json.loads(m.read_text())
    print(f'Config hash:    {mdata.get(\"config_sha256\", \"N/A\")[:24]}...')
    print(f'Prompt hash:    {mdata.get(\"prompt_sha256\", \"N/A\")[:24]}...')

# Quality
flags = {}
for f in Path('data/run_metadata').glob('*.json'):
    meta = json.loads(f.read_text())
    for flag in meta.get('quality_flags', []):
        flags[flag] = flags.get(flag, 0) + 1
print(f'Quality flags:  {flags if flags else \"None\"}')
"
echo ""
echo "Key results:    paper/results_summary.md"
echo "Logbook:        $(ls -t logs/logbook_*.md 2>/dev/null | head -1)"
echo "Manifest:       data/manifest.json"
echo ""
echo "STATUS: Ready for operator review"
echo "ACTION: Run 'python operator_logbook.py review' to see full logbook"
echo "════════════════════════════════════════"
```

---

## Rules of Engagement

1. **Read `COWORK_INSTRUCTIONS.md` for your permission boundaries** — GREEN/YELLOW/RED actions are defined there.
2. **If you modify any code, log it** — file, function, before/after, reason.
3. **If something fails and the decision tree doesn't cover it, use your best judgment and log your reasoning.** The operator will review.
4. **Never change the 20 query texts or the temperature/top_p settings.** These are pre-registered.
5. **Never push to git remote.** Commit locally only.
6. **If total spend approaches $150, the pipeline will halt automatically.** Do not override this.
7. **When in doubt, continue and log.** The operator prefers a completed experiment with notes over a halted experiment with clean logs.

---

## Success Criteria

The experiment is complete when:
- [ ] 50 output files exist in `outputs/run_b/` (10 models × 5 runs)
- [ ] 50 metadata files exist in `data/run_metadata/`
- [ ] `data/brand_visibility_matrix.csv` exists and has data
- [ ] `paper/results/analysis_results.json` exists
- [ ] `paper/results_summary.md` exists
- [ ] `data/manifest.json` exists with all hashes
- [ ] Operator logbook written to `logs/logbook_*.md`
- [ ] All changes committed to git (not pushed)
- [ ] Total spend ≤ $150
- [ ] No unresolved RED violations
