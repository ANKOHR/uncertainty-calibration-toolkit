# Local build evidence

Measured on 2026-10-01, Windows, Python 3.12.10, CPU only.

- Pytest: 38 passed in 0.49 seconds.
- Actual installed CLI subprocess demo: fixtures, run, Markdown report completed in 1.072606 seconds combined, below the 5-second acceptance limit. No tracebacks.
- Synthetic observations: 200; correct: 90; incorrect: 110.
- Exact accuracy: 9/20; mean confidence: 1/2; Brier score: 67/400; ECE: 1/20.
- All 10 planted overconfidence bins and all 6 planted high-confidence errors matched independent expectations, with zero false positive flags.
- Input mutation changes computed scores and flags; determinism tests compare output bytes from repeated runs.
- Malformed, missing, empty, adversarial, Unicode, CSV, write-failure, and tampered-result cases covered.

All calibration figures above are computed from labelled SYNTHETIC illustrative fixtures. The elapsed time is a measured local build result, not a time-saved claim or a portability guarantee. No Henry-entered real observations were used. Real-use accuracy, usage, revenue, savings, and buyer demand remain unmeasured. The two-week verdict is pending in VERDICT.md.
