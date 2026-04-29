# Deviations Log

This file records all post-pre-registration deviations from the registered protocol.
Any change to hypotheses, model roster, query set, prompt, or analysis plan must be
logged here immediately with date, description, and justification.

Format:
## DEV-NNN: Short title
**Date:** YYYY-MM-DD
**Category:** [hypothesis | model_roster | query_set | prompt | analysis_plan | other]
**Description:** What changed.
**Justification:** Why the change was necessary.
**Impact on confirmatory analyses:** None | [describe impact]

---

## DEV-001: Main run process interruption
**Date:** 2026-04-28
**Category:** other
**Description:** Stage 3.4 main run process terminated during 3600s inter-trial wait. Last file written 00:10 PDT, process death discovered 02:08 PDT. Run restarted 02:11 PDT with full archive of partial outputs.
**Justification:** Process launched via bg+disown outside tmux; did not survive SSH session change. Restarted inside tmux for persistence.
**Impact on confirmatory analyses:** None. Minimum 60-minute spacing still satisfied — gap of ~2 hours exceeds pre-registered 60-minute threshold. Final clean run produced 55/55 files with correct v3 model IDs.
