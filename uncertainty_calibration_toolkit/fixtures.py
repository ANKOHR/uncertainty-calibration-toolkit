"""Labelled illustrative fixtures with literal, hand-computed expectations.

No randomness is used, so there is no seed. Each of ten groups has 20 records,
confidence (2k+1)/20 and exactly 2k correct outcomes for k = 0..9.
"""
import json
from pathlib import Path

HEADER = "# SYNTHETIC: illustrative planted data, not real-world performance.\n"


def fixture_records():
    return [{"id": f"g{k}-r{j:02}", "confidence": f"0.{5 + 10*k:02}",
             "correct": j < 2*k, "synthetic": True, "source": "synthetic_fixture"}
            for k in range(10) for j in range(20)]


def expectations():
    # Literal arithmetic, independent of the engine: 90/200 correct; total
    # confidence 100; squared error 33.5; weighted absolute gap 10.
    return {"synthetic": True, "label": "SYNTHETIC hand-computed ground truth",
            "count": 200, "correct": 90, "incorrect": 110,
            "accuracy": {"numerator": 9, "denominator": 20},
            "mean_confidence": {"numerator": 1, "denominator": 2},
            "brier_score": {"numerator": 67, "denominator": 400},
            "ece": {"numerator": 1, "denominator": 20},
            "overconfident_bins": list(range(10)),
            "high_confidence_error_ids": ["g8-r16", "g8-r17", "g8-r18", "g8-r19", "g9-r18", "g9-r19"],
            "bin_counts": [20]*10, "bin_correct": [0,2,4,6,8,10,12,14,16,18]}


def generate(out):
    directory = Path(out)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "records.jsonl").write_text(HEADER + "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in fixture_records()), encoding="utf-8")
    (directory / "expectations.json").write_text(HEADER + json.dumps(expectations(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return directory
