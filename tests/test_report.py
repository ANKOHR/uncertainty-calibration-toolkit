import json
from uncertainty_calibration_toolkit.core import analyze
from uncertainty_calibration_toolkit.fixtures import fixture_records, expectations
from uncertainty_calibration_toolkit.report import render


def test_report_matches_ground_truth_exact():
    result = json.loads(render(analyze(fixture_records()),"json"))
    for field in ("count","correct","incorrect","accuracy","mean_confidence","brier_score","ece"):
        assert result[field] == expectations()[field]
    md = render(result)
    assert "| brier_score | 0.1675 |" in md
    assert "| ece | 0.05 |" in md


def test_report_zero_false_positives():
    result = json.loads(render(analyze(fixture_records()),"json"))
    assert set(result["high_confidence_error_ids"]) == set(expectations()["high_confidence_error_ids"])
    assert result["overconfident_bins"] == expectations()["overconfident_bins"]


def test_report_carries_provenance_banner():
    rows = fixture_records()[:1] + [dict(fixture_records()[1],synthetic=False,source="henry_entered")]
    for fmt in ("md","json"):
        output = render(analyze(rows),fmt)
        assert "DATA PROVENANCE: SYNTHETIC illustrative fixtures: 1; REAL Henry-entered observations: 1" in output


def test_hypothetical_figures_labelled():
    for fmt in ("md","json"):
        text = render(analyze(fixture_records()),fmt)
        assert "illustrative" in text
        assert "unmeasured" in text
        assert "not reported" in text


def test_no_em_dashes_in_outputs():
    rows = fixture_records()[:1]
    rows[0]["id"] = "unicode" + chr(0x2014)
    rows[0]["correct"] = False
    rows[0]["confidence"] = "0.9"
    for fmt in ("md","json"):
        assert chr(0x2014) not in render(analyze(rows),fmt)
