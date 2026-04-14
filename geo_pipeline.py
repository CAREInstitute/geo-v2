#!/usr/bin/env python3
"""
GEO Cross-Model Brand Visibility Study — Pipeline Orchestrator

Usage:
  python geo_pipeline.py preflight                    # Check model availability
  python geo_pipeline.py run-b                        # Execute Run B experiment
  python geo_pipeline.py run-b --fast                 # Skip temporal spacing (non-academic)
  python geo_pipeline.py run-a --prompt prompts/a1.md # Execute a single Run A
  python geo_pipeline.py extract                      # Extract brands from outputs
  python geo_pipeline.py analyze                      # Run statistical analysis
  python geo_pipeline.py stochasticity                # Check output determinism
  python geo_pipeline.py manifest                     # Generate reproducibility manifest
  python geo_pipeline.py report                       # Generate summary report
  python geo_pipeline.py full                         # Run entire pipeline end-to-end
  python geo_pipeline.py full --fast                   # Full pipeline, no spacing

Set OPENROUTER_API_KEY environment variable before running.

v2.1.0  2026-04-15  Added manifest command, version tracking, revised prompt
v2.0.0  2026-04-14  K=5 trials, 20 queries, temporal spacing, full analysis plan
v1.0.0  2026-04-14  Initial build
"""

__version__ = "2.1.0"
__component__ = "geo_pipeline"

import os
import sys
import json
import time
import hashlib
import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich import print as rprint
    RICH = True
except ImportError:
    RICH = False
    def rprint(*a, **kw): print(*a)

import geo_config as cfg
import geo_runner as runner
import geo_extract as extract
import geo_analyze as analyze

console = Console() if RICH else None
BASE_DIR = Path(__file__).parent


# ─── Progress Callback ────────────────────────────────────────────────────────

def progress_cb(event, msg):
    """Print progress events."""
    if RICH:
        styles = {
            "phase2a_start": "[bold cyan]",
            "phase2a_done": "[bold green]",
            "phase2b_start": "[bold cyan]",
            "phase2b_done": "[bold green]",
            "trial_batch": "[yellow]",
            "trial_done": "[dim]",
            "spacing_wait": "[bold magenta]",
            "run_a_start": "[bold cyan]",
            "run_a_done": "[green]",
        }
        style = styles.get(event, "")
        console.print(f"{style}{msg}")
    else:
        print(f"[{event}] {msg}")


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_preflight(args):
    """Check model availability on OpenRouter."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        rprint("[red]Error: Set OPENROUTER_API_KEY environment variable[/red]" if RICH else "Error: Set OPENROUTER_API_KEY")
        return 1

    rprint("\n[bold]Pre-flight check: verifying model availability on OpenRouter...[/bold]\n" if RICH else "\nPre-flight check...\n")

    ok, msg, status = runner.preflight_check(api_key)

    if RICH:
        table = Table(title="Model Availability")
        table.add_column("Model ID", style="cyan")
        table.add_column("Status")
        for mid, s in status.items():
            style = "green" if s == "available" else ("yellow" if "substituted" in s else "red")
            table.add_row(mid, f"[{style}]{s}[/{style}]")
        console.print(table)
    else:
        for mid, s in status.items():
            print(f"  {mid}: {s}")

    rprint(f"\n{'[green]✓' if ok else '[red]✗'} {msg}\n" if RICH else f"\n{'OK' if ok else 'FAIL'}: {msg}\n")
    return 0 if ok else 1


def cmd_run_b(args):
    """Execute Run B experiment."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        rprint("[red]Error: Set OPENROUTER_API_KEY[/red]" if RICH else "Error: Set OPENROUTER_API_KEY")
        return 1

    # Build prompt from queries
    prompt_text = _build_run_b_prompt()
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

    if RICH:
        console.print(Panel(
            f"[bold]GEO Cross-Model Brand Visibility Experiment[/bold]\n\n"
            f"Models: {len(cfg.MODELS)}\n"
            f"Queries: {len(cfg.QUERIES)}\n"
            f"Trials per model: {cfg.K_TRIALS}\n"
            f"Total observations: {len(cfg.MODELS) * cfg.K_TRIALS}\n"
            f"Prompt SHA-256: {prompt_hash[:16]}...\n"
            f"Temporal spacing: {'DISABLED (--fast)' if args.fast else f'{cfg.SEARCH_SPACING_SECONDS}s for search-augmented'}",
            title="Run B Configuration", border_style="blue"
        ))
    else:
        print(f"\nRun B: {len(cfg.MODELS)} models × {cfg.K_TRIALS} trials")
        print(f"Prompt hash: {prompt_hash[:16]}...")

    # Apply --fast mode
    if args.fast:
        original_spacing = cfg.SEARCH_SPACING_SECONDS
        cfg.SEARCH_SPACING_SECONDS = 5  # Minimal spacing

    # Save prompt
    prompt_path = BASE_DIR / "prompts" / "run_b_experiment.md"
    prompt_path.parent.mkdir(exist_ok=True)
    prompt_path.write_text(prompt_text, encoding="utf-8")

    # Save experiment metadata
    _save_experiment_metadata(prompt_hash)

    # Execute
    start = time.time()
    results = runner.run_b_experiment(api_key, prompt_text, str(BASE_DIR), progress_cb)
    elapsed = time.time() - start

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "OK")
    fail_count = sum(1 for r in results if r["status"] != "OK")
    total_words = sum(r["words"] for r in results)

    if RICH:
        console.print(Panel(
            f"[green]Completed: {ok_count}[/green] | [red]Failed: {fail_count}[/red]\n"
            f"Total words: {total_words:,}\n"
            f"Elapsed: {elapsed/60:.1f} minutes",
            title="Run B Complete", border_style="green"
        ))
    else:
        print(f"\nDone: {ok_count} OK, {fail_count} failed, {total_words} words, {elapsed/60:.1f} min")

    if args.fast:
        cfg.SEARCH_SPACING_SECONDS = original_spacing

    return 0 if fail_count == 0 else 1


def cmd_run_a(args):
    """Execute a Run A task."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        rprint("[red]Error: Set OPENROUTER_API_KEY[/red]" if RICH else "Error: Set OPENROUTER_API_KEY")
        return 1

    prompt_file = Path(args.prompt)
    if not prompt_file.exists():
        rprint(f"[red]Prompt file not found: {prompt_file}[/red]" if RICH else f"Error: {prompt_file} not found")
        return 1

    # Determine which A-run based on filename
    run_key = None
    for key in cfg.RUN_A_MODELS:
        if key in prompt_file.stem:
            run_key = key
            break

    if not run_key:
        rprint(f"[red]Cannot determine run type from filename: {prompt_file.name}[/red]" if RICH else f"Error: unknown run type")
        return 1

    prompt_text = prompt_file.read_text(encoding="utf-8")
    rprint(f"\n[bold]Running {run_key} via OpenRouter ({cfg.RUN_A_MODELS[run_key]['name']})[/bold]\n" if RICH else f"\nRunning {run_key}...")

    name, wc, finish = runner.run_a_single(api_key, run_key, prompt_text, str(BASE_DIR), progress_cb)
    rprint(f"\n[green]✓ {name}: {wc} words [{finish}][/green]\n" if RICH else f"\nDone: {name}: {wc} words [{finish}]")
    return 0


def cmd_extract(args):
    """Extract brands from Run B outputs."""
    rprint("\n[bold]Extracting brands from Run B outputs...[/bold]\n" if RICH else "\nExtracting brands...")

    raw_df = extract.extract_all_brands(str(BASE_DIR))

    if raw_df.empty:
        rprint("[red]No brands extracted. Check that Run B outputs exist.[/red]" if RICH else "No brands found.")
        return 1

    matrix_df = extract.build_brand_matrix(raw_df, str(BASE_DIR))

    rprint(f"[green]Extracted {len(raw_df)} brand mentions across {raw_df['model_short'].nunique()} models[/green]" if RICH else f"Extracted {len(raw_df)} mentions")
    rprint(f"[green]Brand matrix: {len(matrix_df)} entries saved to data/brand_visibility_matrix.csv[/green]" if RICH else f"Matrix: {len(matrix_df)} entries")

    # Generate inter-coder sample
    sample = extract.generate_intercoder_sample(raw_df)
    sample_path = BASE_DIR / "data" / "intercoder_sample.csv"
    sample.to_csv(sample_path, index=False)
    rprint(f"[yellow]Inter-coder sample: {len(sample)} responses → {sample_path}[/yellow]" if RICH else f"Sample: {len(sample)} responses")

    return 0


def cmd_analyze(args):
    """Run full statistical analysis."""
    rprint("\n[bold]Running pre-registered analysis plan...[/bold]\n" if RICH else "\nAnalyzing...")

    results = analyze.run_full_analysis(str(BASE_DIR))

    if "error" in results:
        rprint(f"[red]{results['error']}[/red]" if RICH else results['error'])
        return 1

    # Display results
    if RICH:
        # H1: Fleiss' kappa
        console.print(Panel(
            f"Mean Fleiss' κ: [bold]{results['H1']['mean_kappa']}[/bold] "
            f"(±{results['H1']['std_kappa']})\n"
            f"Interpretation: {results['H1']['interpretation']}\n"
            f"H1 supported (κ < 0.6): [{'green' if results['H1']['hypothesis_supported'] else 'red'}]"
            f"{'YES' if results['H1']['hypothesis_supported'] else 'NO'}",
            title="H1: Cross-Model Agreement", border_style="cyan"
        ))

        # H2: Architecture effect
        h2 = results["H2"]
        console.print(Panel(
            f"Within search-augmented: {h2['within_search_mean']:.4f} (n={h2['within_search_n']})\n"
            f"Between groups: {h2['between_groups_mean']:.4f} (n={h2['between_groups_n']})\n"
            f"Cohen's d: {h2['cohens_d']:.4f}\n"
            f"p-value: {h2['p_value']:.4f}" if h2['p_value'] else "p-value: N/A",
            title="H2: Retrieval Architecture Effect", border_style="cyan"
        ))

        # H4: Intra vs. inter
        h4 = results["H4"]
        console.print(Panel(
            f"Intra-model Jaccard: {h4['mean_intra_jaccard']:.4f}\n"
            f"Inter-model Jaccard: {h4['mean_inter_jaccard']:.4f}\n"
            f"Difference: {h4['difference']:.4f}\n"
            f"H4 supported (intra > inter): [{'green' if h4['hypothesis_supported'] else 'red'}]"
            f"{'YES' if h4['hypothesis_supported'] else 'NO'}",
            title="H4: Intra vs. Inter Consistency", border_style="cyan"
        ))

        # Brand frequency
        bf = results.get("Brand_Frequency", {})
        if bf:
            console.print(Panel(
                f"Total unique brands: {bf['total_unique_brands']}\n"
                f"Universal (≥8 models): {', '.join(bf['universal_brands'][:10])}\n"
                f"Model-specific (≤2 models): {len(bf['model_specific_brands'])} brands",
                title="Brand Frequency (Exploratory)", border_style="yellow"
            ))
    else:
        print(json.dumps(results, indent=2, default=str))

    rprint(f"\n[green]Results saved to paper/results/[/green]\n" if RICH else "\nResults saved.")
    return 0


def cmd_stochasticity(args):
    """Check output determinism across K runs."""
    rprint("\n[bold]Stochasticity analysis...[/bold]\n" if RICH else "\nStochasticity check...")

    results = runner.check_stochasticity(str(BASE_DIR))

    if not results:
        rprint("[red]No Run B outputs found.[/red]" if RICH else "No outputs found.")
        return 1

    if RICH:
        table = Table(title="Stochasticity Report (T=0.3)")
        table.add_column("Model", style="cyan")
        table.add_column("Group")
        table.add_column("Unique / Total")
        table.add_column("Identical %")
        table.add_column("Deterministic?")

        for short, r in sorted(results.items()):
            det_style = "red" if r["effectively_deterministic"] else "green"
            table.add_row(
                r["model"], r["group"],
                f"{r['unique_outputs']}/{r['total_runs']}",
                f"{r['identical_proportion']*100:.0f}%",
                f"[{det_style}]{'YES' if r['effectively_deterministic'] else 'NO'}[/{det_style}]"
            )
        console.print(table)
    else:
        for short, r in sorted(results.items()):
            print(f"  {r['model']}: {r['unique_outputs']}/{r['total_runs']} unique ({r['identical_proportion']*100:.0f}% identical)")

    # Save
    report_path = BASE_DIR / "data" / "stochasticity_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    rprint(f"\n[green]Saved to {report_path}[/green]\n" if RICH else f"\nSaved to {report_path}")
    return 0


def cmd_manifest(args):
    """Generate reproducibility manifest with all hashes and environment info."""
    rprint("\n[bold]Generating experiment manifest...[/bold]\n" if RICH else "\nGenerating manifest...")

    # Read prompt hash if it exists
    hash_path = BASE_DIR / "prompt_hash.txt"
    prompt_hash = None
    if hash_path.exists():
        prompt_hash = hash_path.read_text().strip().split()[0]

    manifest = runner.generate_manifest(str(BASE_DIR), prompt_hash)

    config_hash = runner.hash_config()
    n_outputs = sum(len(v) for v in manifest.get("outputs", {}).values())

    if RICH:
        console.print(Panel(
            f"[bold]Config SHA-256:[/bold] {config_hash[:32]}...\n"
            f"[bold]Prompt SHA-256:[/bold] {manifest['prompt_sha256'][:32] if manifest['prompt_sha256'] != '(run experiment first)' else '(not yet computed)'}...\n"
            f"[bold]Environment:[/bold] Python {manifest['environment']['python_version']} | {manifest['environment']['platform'][:40]}\n"
            f"[bold]Output hashes:[/bold] {n_outputs} response files fingerprinted\n"
            f"\n[dim]A replicator with matching config_hash + prompt_hash ran the identical experiment.\n"
            f"Matching content hashes = identical outputs (full replication).[/dim]",
            title="Experiment Manifest", border_style="green"
        ))
    else:
        print(f"Config hash:  {config_hash[:32]}...")
        print(f"Prompt hash:  {manifest['prompt_sha256'][:32] if manifest['prompt_sha256'] != '(run experiment first)' else 'N/A'}...")
        print(f"Outputs:      {n_outputs} files hashed")

    rprint(f"[green]Manifest saved to data/manifest.json[/green]\n" if RICH else "Saved to data/manifest.json\n")
    return 0


def cmd_report(args):
    """Generate a summary report of all analyses."""
    results_path = BASE_DIR / "paper" / "results" / "analysis_results.json"
    stoch_path = BASE_DIR / "data" / "stochasticity_report.json"

    if not results_path.exists():
        rprint("[red]Run analysis first: python geo_pipeline.py analyze[/red]" if RICH else "Run analyze first")
        return 1

    with open(results_path) as f:
        results = json.load(f)

    stoch = {}
    if stoch_path.exists():
        with open(stoch_path) as f:
            stoch = json.load(f)

    # Generate markdown report
    report = _generate_report(results, stoch)
    report_path = BASE_DIR / "paper" / "results_summary.md"
    report_path.write_text(report, encoding="utf-8")
    rprint(f"[green]Report saved to {report_path}[/green]" if RICH else f"Report: {report_path}")
    return 0


def cmd_full(args):
    """Run the entire pipeline end-to-end."""
    rprint("\n[bold magenta]═══ GEO Full Pipeline ═══[/bold magenta]\n" if RICH else "\n=== GEO Full Pipeline ===\n")

    steps = [
        ("Pre-flight", lambda: cmd_preflight(args)),
        ("Run B Experiment", lambda: cmd_run_b(args)),
        ("Brand Extraction", lambda: cmd_extract(args)),
        ("Stochasticity Check", lambda: cmd_stochasticity(args)),
        ("Statistical Analysis", lambda: cmd_analyze(args)),
        ("Report Generation", lambda: cmd_report(args)),
        ("Reproducibility Manifest", lambda: cmd_manifest(args)),
    ]

    for name, fn in steps:
        rprint(f"\n[bold]{'─'*40}[/bold]" if RICH else f"\n{'─'*40}")
        rprint(f"[bold blue]Step: {name}[/bold blue]" if RICH else f"Step: {name}")
        rprint(f"[bold]{'─'*40}[/bold]\n" if RICH else f"{'─'*40}\n")

        rc = fn()
        if rc != 0:
            rprint(f"[red]Step '{name}' failed (exit {rc}). Pipeline halted.[/red]" if RICH else f"FAILED: {name}")
            return rc

    rprint(f"\n[bold green]═══ Pipeline Complete ═══[/bold green]\n" if RICH else "\n=== Pipeline Complete ===\n")
    return 0


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_run_b_prompt():
    """Build the Run B prompt from the query set.

    v2.0 changes (2026-04-15):
      - Removed research-study framing (ecologically invalid — triggers hedging)
      - Unconstrained brand count ("recommend the brands you think best fit")
      - Added "Respond entirely in English" for non-English-corpus models
      - Added lightweight format instruction for extraction consistency
      - Moved Sections B/C to optional follow-up (saves ~50% tokens)
      - Added response-length anchor (200-400 words per query)
    """
    lines = [
        "I need your help evaluating options across several product and service categories.",
        "For each question below, please recommend the specific brands or products you think",
        "best fit the described need. Rank your recommendations from strongest to weakest,",
        "and include a brief justification (1-2 sentences) for each.",
        "",
        "Please respond entirely in English. For each query, use the format:",
        "",
        "**Q[number]: [query topic]**",
        "1. **Brand Name** — Justification",
        "2. **Brand Name** — Justification",
        "(continue as needed)",
        "",
        "Aim for 200-400 words per query. Be specific and commit to your recommendations.",
        "If you consulted web sources, briefly note them after your recommendations.",
        "",
        "---",
        "",
    ]

    for q in cfg.QUERIES:
        lines.append(f"**{q['id']}:** {q['text']}")
        lines.append("")

    return "\n".join(lines)


def _build_run_b_meta_prompt():
    """Optional follow-up prompt for source attribution + self-analysis.

    Run AFTER primary data collection, only if budget allows.
    Not part of the pre-registered primary analysis.
    """
    return (
        "For the recommendations you just provided, please answer these follow-up questions:\n\n"
        "1. For each query, what sources informed your recommendations — your training data, "
        "web search results, or both? Be specific.\n"
        "2. For each query, rate your confidence in your top recommendation: HIGH, MEDIUM, or LOW.\n"
        "3. Were there brands you considered but excluded? If so, which ones and why?\n"
        "4. Do you notice any systematic patterns in which brands you tend to recommend?\n"
        "5. What factors most influenced your rankings?\n"
    )


def _get_version_info():
    """Collect version strings from all pipeline components."""
    components = {}
    for mod_name in ["geo_config", "geo_runner", "geo_extract", "geo_analyze", "geo_pipeline"]:
        try:
            mod = __import__(mod_name)
            components[mod_name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            components[mod_name] = "not_found"
    return components


def _save_experiment_metadata(prompt_hash):
    """Save experiment metadata JSON."""
    meta = {
        "experiment_name": cfg.EXPERIMENT_NAME,
        "version": cfg.VERSION,
        "date_conducted": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "prompt_sha256": prompt_hash,
        "pipeline_versions": _get_version_info(),
        "config_sha256": runner.hash_config(),
        "design": {
            "queries": len(cfg.QUERIES),
            "query_categories": list(set(q["category"] for q in cfg.QUERIES)),
            "models_tested": len(cfg.MODELS),
            "trials_per_model": cfg.K_TRIALS,
            "total_observations": len(cfg.QUERIES) * len(cfg.MODELS) * cfg.K_TRIALS,
            "temperature": cfg.TEMPERATURE,
            "top_p": cfg.TOP_P,
            "search_spacing_seconds": cfg.SEARCH_SPACING_SECONDS,
        },
        "models": [
            {k: v for k, v in m.items() if k != "extra_body"}
            for m in cfg.MODELS
        ],
        "queries": cfg.QUERIES,
    }

    meta_path = BASE_DIR / "data" / "experiment_metadata.json"
    meta_path.parent.mkdir(exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _generate_report(results, stoch):
    """Generate a markdown summary report."""
    lines = [
        "# GEO Cross-Model Brand Visibility Study — Results Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "---",
        "",
        "## H1: Cross-Model Agreement (Fleiss' κ)",
        "",
        f"- **Mean κ = {results['H1']['mean_kappa']}** (±{results['H1']['std_kappa']})",
        f"- Interpretation: {results['H1']['interpretation']}",
        f"- H1 supported (κ < 0.6): **{'YES' if results['H1']['hypothesis_supported'] else 'NO'}**",
        "",
    ]

    if results["H1"].get("per_query"):
        lines.extend(["| Query | Category | κ | Brands |", "|-------|----------|---|--------|"])
        for r in results["H1"]["per_query"]:
            lines.append(f"| {r['query_id']} | {r['category']} | {r['fleiss_kappa']} | {r['n_brands']} |")
        lines.append("")

    h2 = results.get("H2", {})
    lines.extend([
        "## H2: Retrieval Architecture Effect",
        "",
        f"- Within search-augmented Jaccard: **{h2.get('within_search_mean', 'N/A'):.4f}**",
        f"- Between groups Jaccard: **{h2.get('between_groups_mean', 'N/A'):.4f}**",
        f"- Cohen's d: **{h2.get('cohens_d', 'N/A'):.4f}**",
        f"- p-value: **{h2.get('p_value', 'N/A')}**",
        "",
    ])

    h4 = results.get("H4", {})
    lines.extend([
        "## H4: Intra vs. Inter Consistency",
        "",
        f"- Intra-model Jaccard: **{h4.get('mean_intra_jaccard', 'N/A')}**",
        f"- Inter-model Jaccard: **{h4.get('mean_inter_jaccard', 'N/A')}**",
        f"- H4 supported: **{'YES' if h4.get('hypothesis_supported') else 'NO'}**",
        "",
    ])

    bf = results.get("Brand_Frequency", {})
    if bf:
        lines.extend([
            "## Brand Frequency (Exploratory)",
            "",
            f"- Total unique brands: {bf.get('total_unique_brands', 'N/A')}",
            f"- Universal brands (≥8 models): {', '.join(bf.get('universal_brands', [])[:15])}",
            f"- Model-specific brands (≤2 models): {len(bf.get('model_specific_brands', []))}",
            "",
        ])

    if stoch:
        lines.extend(["## Stochasticity Report", "", "| Model | Group | Unique/Total | Deterministic |", "|-------|-------|-------------|---------------|"])
        for short, r in sorted(stoch.items()):
            lines.append(f"| {r['model']} | {r['group']} | {r['unique_outputs']}/{r['total_runs']} | {'Yes' if r['effectively_deterministic'] else 'No'} |")
        lines.append("")

    return "\n".join(lines)


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GEO Cross-Model Brand Visibility Study Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Set OPENROUTER_API_KEY environment variable before running."
    )
    sub = parser.add_subparsers(dest="command", help="Pipeline command")

    sub.add_parser("preflight", help="Check model availability")

    p_rb = sub.add_parser("run-b", help="Execute Run B experiment")
    p_rb.add_argument("--fast", action="store_true", help="Skip temporal spacing (non-academic mode)")

    p_ra = sub.add_parser("run-a", help="Execute a Run A task")
    p_ra.add_argument("--prompt", required=True, help="Path to Run A prompt file")

    sub.add_parser("extract", help="Extract brands from outputs")
    sub.add_parser("analyze", help="Run statistical analysis")
    sub.add_parser("stochasticity", help="Check output determinism")
    sub.add_parser("report", help="Generate summary report")
    sub.add_parser("manifest", help="Generate reproducibility manifest (hashes + fingerprint)")

    p_full = sub.add_parser("full", help="Run entire pipeline")
    p_full.add_argument("--fast", action="store_true", help="Skip temporal spacing")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "preflight": cmd_preflight,
        "run-b": cmd_run_b,
        "run-a": cmd_run_a,
        "extract": cmd_extract,
        "analyze": cmd_analyze,
        "stochasticity": cmd_stochasticity,
        "report": cmd_report,
        "manifest": cmd_manifest,
        "full": cmd_full,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
