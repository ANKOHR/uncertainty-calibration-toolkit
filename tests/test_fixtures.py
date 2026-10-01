import json
from uncertainty_calibration_toolkit.fixtures import generate, expectations
from uncertainty_calibration_toolkit.cli import read_input
from uncertainty_calibration_toolkit.core import analyze


def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path)
    for path in tmp_path.iterdir():
        text = path.read_text(encoding="utf-8")
        assert text.startswith("# SYNTHETIC")
        assert '"synthetic": true' in text
    rows, _ = read_input(tmp_path,"2026-09-30")
    assert len(rows) == 200
    assert all(r["synthetic"] for r in rows)


def test_fixture_ground_truth_matches_hand_computed(tmp_path):
    generate(tmp_path)
    actual = analyze(read_input(tmp_path,"2026-09-30")[0])
    expected = expectations()
    for key in ("count","correct","incorrect","accuracy","mean_confidence","brier_score","ece","overconfident_bins","high_confidence_error_ids"):
        assert actual[key] == expected[key]
    assert [b["count"] for b in actual["bins"]] == expected["bin_counts"]
    assert [b["correct"] for b in actual["bins"]] == expected["bin_correct"]
    assert sum(b["count"] for b in actual["bins"]) == actual["count"]
