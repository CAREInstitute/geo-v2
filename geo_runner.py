"""
GEO Pipeline — OpenRouter API Runner
Handles API calls, retries, metadata capture, temporal spacing.

v2.1.0  2026-04-15  Added manifest generation, config hashing, env fingerprint, file logger
v2.0.0  2026-04-14  Revised model roster (8/10 replaced), K=5 trials, temporal spacing
v1.0.0  2026-04-14  Initial build
"""

__version__ = "2.1.0"
__component__ = "geo_runner"

import os
import json
import time
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import geo_config as cfg

# ─── Constants ────────────────────────────────────────────────────────────────

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds

# ─── Core API Call ────────────────────────────────────────────────────────────

def call_openrouter(api_key, model_id, prompt, max_tokens, extra_body=None):
    """Send a single request to OpenRouter and return parsed response + metadata."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/geo-cross-model-study",
        "X-Title": "GEO Cross-Model Brand Visibility Study",
    }

    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": cfg.TEMPERATURE,
        "max_tokens": max_tokens,
        "top_p": cfg.TOP_P,
    }

    if extra_body:
        body.update(extra_body)

    start = datetime.now(timezone.utc)
    errors = []

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, headers=headers, json=body, timeout=300)
            resp.raise_for_status()
            data = resp.json()

            content = ""
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                content = msg.get("content", "")

            end = datetime.now(timezone.utc)

            usage = data.get("usage", {})
            meta = {
                "model_requested": model_id,
                "model_returned": data.get("model", "unknown"),
                "start_timestamp": start.isoformat(),
                "end_timestamp": end.isoformat(),
                "duration_seconds": (end - start).total_seconds(),
                "prompt_tokens": usage.get("prompt_tokens", -1),
                "completion_tokens": usage.get("completion_tokens", -1),
                "total_tokens": usage.get("total_tokens", -1),
                "finish_reason": data["choices"][0].get("finish_reason", "unknown") if data.get("choices") else "no_choices",
                "attempt": attempt,
                "errors": errors,
                "response_id": data.get("id", "unknown"),
            }

            return content, meta

        except requests.exceptions.Timeout:
            errors.append({"attempt": attempt, "error": "timeout", "ts": datetime.now(timezone.utc).isoformat()})
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            errors.append({"attempt": attempt, "error": f"http_{status}", "body": e.response.text[:500] if e.response else "", "ts": datetime.now(timezone.utc).isoformat()})
            if status == 429:  # Rate limited
                time.sleep(RETRY_DELAY * attempt)
        except Exception as e:
            errors.append({"attempt": attempt, "error": str(e)[:200], "ts": datetime.now(timezone.utc).isoformat()})

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    # All retries exhausted
    end = datetime.now(timezone.utc)
    return "", {
        "model_requested": model_id,
        "model_returned": "FAILED",
        "start_timestamp": start.isoformat(),
        "end_timestamp": end.isoformat(),
        "duration_seconds": (end - start).total_seconds(),
        "prompt_tokens": -1,
        "completion_tokens": -1,
        "total_tokens": -1,
        "finish_reason": "error",
        "attempt": MAX_RETRIES,
        "errors": errors,
        "response_id": "FAILED",
    }


# ─── Run B Executor ───────────────────────────────────────────────────────────

def run_single_trial(api_key, model, prompt, run_k, out_dir, meta_dir, prompt_hash):
    """Execute a single trial for one model and save output + metadata.

    Returns: (short, run_k, word_count, finish_reason, errors, cost)
    """
    short = model["short"]
    model_id = model["id"]
    max_tokens = model.get("max_tokens", cfg.MAX_TOKENS)
    extra = model.get("extra_body")

    out_file = Path(out_dir) / f"{short}_run{run_k}.md"
    meta_file = Path(meta_dir) / f"{short}_run{run_k}.json"

    # ── Resume: skip if output already exists with content ──
    if out_file.exists() and out_file.stat().st_size > 500:
        existing = out_file.read_text(encoding="utf-8")
        wc = len(existing.split())
        if wc >= 200:  # Minimum viable response
            return short, run_k, wc, "skipped_existing", [], 0.0

    content, meta = call_openrouter(api_key, model_id, prompt, max_tokens, extra)

    # ── Output validation ──
    quality_flags = []
    wc = len(content.split()) if content else 0

    if wc == 0:
        quality_flags.append("EMPTY_RESPONSE")
    elif wc < 100:
        quality_flags.append("VERY_SHORT")

    # Check for common refusal patterns
    refusal_signals = ["i can't", "i cannot", "i'm not able", "i am not able",
                       "as an ai", "i don't have the ability", "against my guidelines"]
    if content and any(sig in content.lower()[:500] for sig in refusal_signals):
        quality_flags.append("POSSIBLE_REFUSAL")

    # Check for error responses masquerading as content
    if content and content.strip().startswith("{") and '"error"' in content[:200]:
        quality_flags.append("ERROR_AS_CONTENT")

    # ── Cost tracking ──
    input_toks = meta.get("prompt_tokens", 0)
    output_toks = meta.get("completion_tokens", 0)
    cost_in = model.get("cost_input_per_m", 0)
    cost_out = model.get("cost_output_per_m", 0)
    if isinstance(input_toks, int) and input_toks > 0:
        call_cost = (input_toks / 1e6) * cost_in + (output_toks / 1e6) * cost_out
    else:
        call_cost = 0.0

    # Enrich metadata
    meta["model_short"] = short
    meta["model_name"] = model["name"]
    meta["model_group"] = model["group"]
    meta["model_arch"] = model["arch"]
    meta["model_corpus"] = model["corpus"]
    meta["run_number"] = run_k
    meta["prompt_sha256"] = prompt_hash
    meta["word_count"] = wc
    meta["content_sha256"] = hashlib.sha256(content.encode()).hexdigest() if content else ""
    meta["quality_flags"] = quality_flags
    meta["call_cost_usd"] = round(call_cost, 6)

    # Save
    out_file.write_text(content, encoding="utf-8")
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return short, run_k, wc, meta["finish_reason"], quality_flags, call_cost


# ─── Budget Guard ─────────────────────────────────────────────────────────────

BUDGET_CEILING_USD = 150.0  # Hard ceiling — pipeline halts if exceeded


def run_b_experiment(api_key, prompt_text, base_dir, progress_callback=None):
    """
    Execute the full Run B experiment: K trials across all models.
    Parametric-only models run in parallel batches.
    Search-augmented models run with temporal spacing.
    """
    out_dir = Path(base_dir) / "outputs" / "run_b"
    meta_dir = Path(base_dir) / "data" / "run_metadata"
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

    # Save prompt hash
    (Path(base_dir) / "prompt_hash.txt").write_text(f"{prompt_hash}  run_b_experiment.md\n")

    parametric = [m for m in cfg.MODELS if m["group"] != "search_augmented"]
    search_aug = [m for m in cfg.MODELS if m["group"] == "search_augmented"]

    results = []
    total_tasks = len(cfg.MODELS) * cfg.K_TRIALS
    completed = 0
    cumulative_cost = 0.0

    # ── Phase 2A: Parametric-only models (all K runs, parallel) ──
    if progress_callback:
        progress_callback("phase2a_start", f"Parametric-only models: {len(parametric)} models × {cfg.K_TRIALS} runs")

    with ThreadPoolExecutor(max_workers=min(8, len(parametric) * cfg.K_TRIALS)) as executor:
        futures = {}
        for model in parametric:
            for k in range(1, cfg.K_TRIALS + 1):
                f = executor.submit(run_single_trial, api_key, model, prompt_text, k, out_dir, meta_dir, prompt_hash)
                futures[f] = (model["short"], k)

        for f in as_completed(futures):
            short, k = futures[f]
            try:
                name, run_k, wc, finish, flags, cost = f.result()
                status = "SKIP" if finish == "skipped_existing" else ("OK" if finish != "error" else "FAILED")
                cumulative_cost += cost
                results.append({"model": name, "run": run_k, "words": wc, "status": status, "cost": cost, "flags": flags})
                completed += 1
                flag_str = f" [{','.join(flags)}]" if flags else ""
                if progress_callback:
                    progress_callback("trial_done", f"  {name} run {run_k}: {wc}w [{status}]{flag_str} ${cumulative_cost:.2f} ({completed}/{total_tasks})")
            except Exception as e:
                results.append({"model": short, "run": k, "words": 0, "status": f"EXCEPTION: {e}", "cost": 0, "flags": []})
                completed += 1

    if progress_callback:
        progress_callback("phase2a_done", f"Parametric-only complete: {completed}/{total_tasks}")

    # ── Phase 2B: Search-augmented models (K runs with temporal spacing) ──
    if progress_callback:
        progress_callback("phase2b_start", f"Search-augmented models: {len(search_aug)} models × {cfg.K_TRIALS} runs (≥{cfg.SEARCH_SPACING_SECONDS}s spacing)")

    for k in range(1, cfg.K_TRIALS + 1):
        # ── Budget guard ──
        if cumulative_cost >= BUDGET_CEILING_USD:
            if progress_callback:
                progress_callback("budget_halt", f"  BUDGET CEILING HIT: ${cumulative_cost:.2f} ≥ ${BUDGET_CEILING_USD:.2f} — halting")
            break

        if progress_callback:
            progress_callback("trial_batch", f"  Search-augmented trial {k}/{cfg.K_TRIALS} (spent: ${cumulative_cost:.2f})")

        with ThreadPoolExecutor(max_workers=len(search_aug)) as executor:
            futures = {}
            for model in search_aug:
                f = executor.submit(run_single_trial, api_key, model, prompt_text, k, out_dir, meta_dir, prompt_hash)
                futures[f] = (model["short"], k)

            for f in as_completed(futures):
                short, rk = futures[f]
                try:
                    name, run_k, wc, finish, flags, cost = f.result()
                    status = "SKIP" if finish == "skipped_existing" else ("OK" if finish != "error" else "FAILED")
                    cumulative_cost += cost
                    results.append({"model": name, "run": run_k, "words": wc, "status": status, "cost": cost, "flags": flags})
                    completed += 1
                    flag_str = f" [{','.join(flags)}]" if flags else ""
                    if progress_callback:
                        progress_callback("trial_done", f"    {name} run {run_k}: {wc}w [{status}]{flag_str} ${cumulative_cost:.2f} ({completed}/{total_tasks})")
                except Exception as e:
                    results.append({"model": short, "run": rk, "words": 0, "status": f"EXCEPTION: {e}", "cost": 0, "flags": []})
                    completed += 1

        # Wait between search-augmented batches (except after last)
        if k < cfg.K_TRIALS:
            wait_sec = cfg.SEARCH_SPACING_SECONDS
            if progress_callback:
                progress_callback("spacing_wait", f"  Waiting {wait_sec}s before next search-augmented trial...")
            time.sleep(wait_sec)

    if progress_callback:
        progress_callback("phase2b_done", f"All trials complete: {completed}/{total_tasks} | Total spend: ${cumulative_cost:.2f}")

    return results


# ─── Run A Executor ───────────────────────────────────────────────────────────

def run_a_single(api_key, run_key, prompt_text, base_dir, progress_callback=None):
    """Execute a single Run A task via OpenRouter."""
    model_cfg = cfg.RUN_A_MODELS[run_key]
    model_id = model_cfg["id"]
    max_tokens = model_cfg.get("max_tokens", 32768)

    out_dir = Path(base_dir) / "outputs" / "run_a"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_key}_output.md"
    meta_file = out_dir / f"{run_key}_meta.json"

    if progress_callback:
        progress_callback("run_a_start", f"Starting {run_key} ({model_cfg['name']})...")

    content, meta = call_openrouter(api_key, model_id, prompt_text, max_tokens)

    meta["run_key"] = run_key
    meta["word_count"] = len(content.split()) if content else 0

    out_file.write_text(content, encoding="utf-8")
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if progress_callback:
        progress_callback("run_a_done", f"  {run_key}: {meta['word_count']} words [{meta['finish_reason']}]")

    return run_key, meta["word_count"], meta["finish_reason"]


# ─── Pre-flight Check ─────────────────────────────────────────────────────────

def preflight_check(api_key):
    """Verify all models are available on OpenRouter."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=30)
        resp.raise_for_status()
        available = {m["id"] for m in resp.json().get("data", [])}
    except Exception as e:
        return False, f"Failed to fetch model list: {e}", {}

    status = {}
    all_ok = True
    for model in cfg.MODELS:
        mid = model["id"]
        if mid in available:
            status[mid] = "available"
        elif mid in cfg.SUBSTITUTIONS and cfg.SUBSTITUTIONS[mid] in available:
            sub = cfg.SUBSTITUTIONS[mid]
            status[mid] = f"substituted → {sub}"
            model["id"] = sub  # Apply substitution in-place
            model["_original_id"] = mid
        else:
            status[mid] = "UNAVAILABLE"
            all_ok = False

    return all_ok, "All models available" if all_ok else "Some models unavailable", status


# ─── Stochasticity Check ─────────────────────────────────────────────────────

def check_stochasticity(base_dir):
    """Compute identical-response proportion across K runs per model."""
    out_dir = Path(base_dir) / "outputs" / "run_b"
    results = {}

    for model in cfg.MODELS:
        short = model["short"]
        hashes = []
        for k in range(1, cfg.K_TRIALS + 1):
            f = out_dir / f"{short}_run{k}.md"
            if f.exists():
                content = f.read_text(encoding="utf-8")
                hashes.append(hashlib.md5(content.encode()).hexdigest())

        if hashes:
            unique = len(set(hashes))
            total = len(hashes)
            results[short] = {
                "model": model["name"],
                "group": model["group"],
                "total_runs": total,
                "unique_outputs": unique,
                "identical_proportion": round(1 - (unique / total), 3) if total > 0 else 0,
                "effectively_deterministic": unique == 1,
            }

    return results


# ─── Environment Fingerprint ──────────────────────────────────────────────────

def get_environment_fingerprint():
    """Capture the execution environment for reproducibility."""
    import platform
    import sys

    fp = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for pkg in ["requests", "pandas", "numpy", "scipy"]:
        try:
            mod = __import__(pkg)
            fp[f"pkg_{pkg}"] = getattr(mod, "__version__", "unknown")
        except ImportError:
            fp[f"pkg_{pkg}"] = "not_installed"
    return fp


# ─── Config Hash ──────────────────────────────────────────────────────────────

def hash_config():
    """SHA-256 of experiment config (models + queries + params).
    Same config hash = same experimental design."""
    blob = json.dumps({
        "version": cfg.VERSION,
        "temperature": cfg.TEMPERATURE,
        "top_p": cfg.TOP_P,
        "max_tokens": cfg.MAX_TOKENS,
        "k_trials": cfg.K_TRIALS,
        "models": [{"id": m["id"], "group": m["group"],
                     "max_tokens": m.get("max_tokens", cfg.MAX_TOKENS)}
                    for m in cfg.MODELS],
        "queries": [{"id": q["id"], "text": q["text"]} for q in cfg.QUERIES],
    }, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


# ─── Experiment Manifest ──────────────────────────────────────────────────────

def generate_manifest(base_dir, prompt_hash=None):
    """One-file reproducibility manifest another researcher can verify against.

    config_hash + prompt_hash match → same experiment.
    content hashes also match → identical outputs (full replication).
    """
    out_dir = Path(base_dir) / "outputs" / "run_b"
    meta_dir = Path(base_dir) / "data" / "run_metadata"

    manifest = {
        "manifest_version": "1.0",
        "generated": datetime.now(timezone.utc).isoformat(),
        "experiment": cfg.EXPERIMENT_NAME,
        "config_version": cfg.VERSION,
        "config_sha256": hash_config(),
        "prompt_sha256": prompt_hash or "(run experiment first)",
        "environment": get_environment_fingerprint(),
        "design": {
            "models": len(cfg.MODELS),
            "queries": len(cfg.QUERIES),
            "trials": cfg.K_TRIALS,
            "total_observations": len(cfg.MODELS) * len(cfg.QUERIES) * cfg.K_TRIALS,
            "temperature": cfg.TEMPERATURE,
        },
        "outputs": {},
    }

    for model in cfg.MODELS:
        short = model["short"]
        model_outputs = {}
        for k in range(1, cfg.K_TRIALS + 1):
            fpath = out_dir / f"{short}_run{k}.md"
            mpath = meta_dir / f"{short}_run{k}.json"
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8")
                entry = {
                    "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "word_count": len(content.split()),
                }
                if mpath.exists():
                    try:
                        meta = json.loads(mpath.read_text())
                        entry["model_returned"] = meta.get("model_returned", "unknown")
                        entry["timestamp"] = meta.get("start_timestamp", "unknown")
                    except Exception:
                        pass
                model_outputs[f"run{k}"] = entry
        if model_outputs:
            manifest["outputs"][short] = model_outputs

    manifest_path = Path(base_dir) / "data" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


# ─── File Logger ──────────────────────────────────────────────────────────────

class ExperimentLogger:
    """Persistent append-only log file for the experiment run."""

    def __init__(self, base_dir):
        log_dir = Path(base_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.log_path = log_dir / f"experiment_{ts}.log"
        self._write(f"=== GEO Experiment Log ===")
        self._write(f"Config SHA-256: {hash_config()}")
        env = get_environment_fingerprint()
        self._write(f"Python {env['python_version']} | {env['platform']}")

    def _write(self, msg):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")

    def info(self, msg):  self._write(msg)
    def error(self, msg): self._write(f"ERROR: {msg}")
    def trial(self, model_short, run_k, words, status):
        self._write(f"{model_short} run{run_k}: {words}w [{status}]")
