import pytest
from uncertainty_calibration_toolkit.core import analyze, SchemaError


def record(**changes):
    return dict(id="one", confidence="0.8", correct=False, synthetic=True, source="synthetic_fixture", **changes)


def test_hand_written_five_records():
    rows = [dict(record(), id=str(i), confidence=p, correct=c) for i, (p,c) in enumerate(zip(["0","0.25","0.5","0.75","1"], [False,False,True,True,True]))]
    result = analyze(rows)
    assert result["accuracy"] == {"numerator":3,"denominator":5}
    assert result["brier_score"] == {"numerator":3,"denominator":40}
    assert result["ece"] == {"numerator":1,"denominator":5}


@pytest.mark.parametrize("change", [dict(confidence=-1),dict(confidence="NaN"),dict(confidence="Infinity"),dict(confidence=True),dict(confidence=1.1),dict(confidence="1e-1000"),dict(correct=1),dict(synthetic="true"),dict(amount=-5),dict(observed_on="2026-10-01"),dict(id="x"*1025),dict(note="x"*10001),dict(source="unknown")])
def test_rejects_adversarial_values(change):
    with pytest.raises(SchemaError):
        analyze([dict(record(), **change)])


def test_duplicate_ids_rejected():
    with pytest.raises(SchemaError, match="duplicate"):
        analyze([record(),record()])


def test_bin_edges_and_thresholds():
    rows = [dict(record(),id=str(i),confidence=p,correct=c) for i,(p,c) in enumerate([("0.1",True),("1",False),("0.8",False),("0.05",False),("0.049",False)])]
    result = analyze(rows)
    assert result["bins"][1]["count"] == 1
    assert result["bins"][9]["count"] == 1
    assert result["high_confidence_error_ids"] == ["1","2"]
    assert result["overconfident_bins"] == [8,9]


def test_corrupted_ground_truth_changes_metrics():
    from uncertainty_calibration_toolkit.fixtures import fixture_records
    rows = fixture_records()
    before = analyze(rows)
    rows[0]["correct"] = True
    after = analyze(rows)
    assert after["correct"] == before["correct"] + 1
    assert after["accuracy"] != before["accuracy"]
    assert after["brier_score"] != before["brier_score"]
    assert after["overconfident_bins"] == list(range(1,10))
