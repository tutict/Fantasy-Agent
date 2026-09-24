# Finding — EXP008-CLOSURE-EVID-001

- Source: `REVIEW-EXP-008-CLOSURE-R0`
- Category / Severity / Status: Evidence accounting / Minor / open
- Rework: TASK-010

The R0 staged boundary contained 42 governance artifacts and 3,146 total physical lines.
The report's 2,212 count used an incorrect PowerShell pipeline measure. Recompute final
physical lines from file bytes after all closure evidence exists.

## R2 Verification

Status remains open. R2 independently measured the pre-R2 totals correctly but returned
NOT VERIFIED-CORRECTED because RESULTS item 58 incorrectly says the measured boundary
still excludes the already-included R1 Review and STD-002 Finding.
