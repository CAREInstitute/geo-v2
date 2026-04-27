# ERRATA

This file documents post-publication corrections and significant pre-execution findings
that deviate from the build file (3_Claude_GEO_v2_Build.md) as originally written.

---

## ERRATA-001: v2.0.1 recovery commit not anticipated by build file

**Date:** 2026-04-27
**Commit:** 806354e
**Severity:** High (affects interpretation of v3.0.0 lineage)

The build file assumed v3.0.0 would be built directly on top of the v1 published state
(tag v1.0-prerepatch, commit 2f7d455). In reality, a critical bug fix was applied on
2026-04-15 that was not committed at the time. This fix was captured in recovery commit
806354e before any v3.0.0 work began.

The _find_query_section fallback bug (fixed in v2.0.1) affected 14,222 phantom
extractions — 68.9% of v1 extraction volume. This is a larger correction than
EXTRACT-001 or EXTRACT-002.

**v3.0.0 lineage is therefore:**
v1.0 (2f7d455) -> v2.0.1 recovery (806354e) -> EXTRACT-001/002 patches (93e7888) -> v3.0.0

**Impact on pre-registration:** None. The paraphrase SHA-256 and all v3.0.0 artifacts
are computed from the corrected codebase. The v1 results referenced in the paper use
the v1 pipeline and are not affected.

---

## ERRATA-002: Build file archive/v1_pre_repatch/ copy step is redundant

**Date:** 2026-04-27
**Severity:** Low (documentation only)

The build file specified a manual copy step to create archive/v1_pre_repatch/.
This is fully covered by git tag v1.0-prerepatch at commit 2f7d455. No separate
archive directory is needed.

---
