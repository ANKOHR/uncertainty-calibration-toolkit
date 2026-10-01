# Lessons for KOML

Exact calibration depends on an explicit bin policy and on the supplied definition of correctness. A score is an observation summary, not proof of predictive validity. Reduced fractions avoid threshold and rounding ambiguity, particularly at an overconfidence gap of exactly 0.05.

Validated by the synthetic tests: literal hand-computed outcomes, bin counts, and full flag sets reconcile with computed reports, and changing one correctness label changes accuracy, Brier score, and flags. This validates deterministic arithmetic on planted data only. The assumption that Henry will use the tool or buyers will value it remains untested.

Operating rule: specify exact boundary semantics and independent ground truth before adding calibration metrics. Include a corrupted-label test so a matching demo cannot conceal hardcoded outputs.

An evidence-based build improvement came from the malformed CSV test: Python DictReader retained the preceding line number after a failed quoted row. Error reporting now uses the underlying CSV reader's physical line count, making the named error identify the actual offending line. The regression test verifies this. This build improvement does not replace the required two-week real-use improvement hook.
