import json
import time
import pytest
from uncertainty_calibration_toolkit.cli import main, read_input, InputError, atomic_write
from uncertainty_calibration_toolkit.fixtures import generate


def test_run_completes_on_fixture(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    started = time.perf_counter()
    assert main(["fixtures","--out","demo"]) == 0
    assert main(["run","--input","demo"]) == 0
    assert main(["report","--format","md"]) == 0
    assert time.perf_counter() - started < 5
    assert "DATA PROVENANCE" in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    result = tmp_path / "result.json"
    assert main(["run","--input",str(tmp_path),"--out",str(result)]) == 0
    assert main(["report","--results",str(result)]) == 0
    assert "Observations: 0; correct: 0; incorrect: 0" in capsys.readouterr().out


@pytest.mark.parametrize("filename,text,line", [("bad.json", "[\n{bad}",2),("bad.jsonl","# label\n{bad}",2),("bad.csv",'id,confidence,correct,synthetic,source\na,"unfinished',2),("bad.yaml","broken: [",1)])
def test_malformed_input_named_error(tmp_path,capsys,filename,text,line):
    (tmp_path / filename).write_text(text,encoding="utf-8")
    assert main(["run","--input",str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and filename in error and f"line {line}" in error
    assert "Traceback" not in error


def test_determinism_byte_identical(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    generate("demo")
    first = (tmp_path/"demo/records.jsonl").read_bytes()
    generate("demo")
    assert first == (tmp_path/"demo/records.jsonl").read_bytes()
    outputs = []
    for _ in range(2):
        assert main(["run","--input","demo"]) == 0
        assert main(["report","--format","json","--out","report.json"]) == 0
        outputs.append((Path(".uct/results.json").read_bytes(),Path("report.json").read_bytes()))
    assert outputs[0] == outputs[1]


from pathlib import Path


def test_cli_smoke_all_subcommands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for command in ("fixtures","run","report","bins","audit"):
        with pytest.raises(SystemExit) as exc:
            main([command,"--help"])
        assert exc.value.code == 0
    assert main(["fixtures","--out","demo"]) == 0
    assert main(["run","--input","demo"]) == 0
    for args in (["report","--format","json"],["bins"],["audit","--input","demo"]):
        assert main(args) == 0


def test_handles_unicode_and_long_inputs(tmp_path,capsys):
    record = dict(id="漢字é",confidence="0.8",correct=False,synthetic=False,source="henry_entered",note="漢"*9990 + "C:\\data")
    (tmp_path/"records.json").write_text(json.dumps([record],ensure_ascii=False),encoding="utf-8")
    result = tmp_path/"saved/result.json"
    assert main(["run","--input",str(tmp_path),"--out",str(result)]) == 0
    assert main(["report","--format","json","--results",str(result)]) == 0
    assert json.loads(capsys.readouterr().out.split("\n",1)[1])["observations"][0]["note"] == record["note"]


def test_write_failure_no_partial_files(tmp_path):
    target = tmp_path/"directory"
    target.mkdir()
    with pytest.raises(InputError,match="WriteError"):
        atomic_write(target,"report")
    assert list(tmp_path.iterdir()) == [target]


def test_missing_input_named_error(tmp_path,capsys):
    assert main(["run","--input",str(tmp_path/"missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_schema_drift_and_duplicate_json_fields(tmp_path,capsys):
    path = tmp_path/"bad.jsonl"
    path.write_text('{"id":"a","id":"b"}',encoding="utf-8")
    assert main(["run","--input",str(tmp_path)]) == 2
    assert "duplicate JSON field" in capsys.readouterr().err
    path.write_text('{"amount":-10}',encoding="utf-8")
    assert main(["run","--input",str(tmp_path)]) == 2
    assert "amount" in capsys.readouterr().err


def test_csv_valid_input(tmp_path):
    (tmp_path/"data.csv").write_text("# SYNTHETIC\nid,confidence,correct,synthetic,source\na,0.25,false,true,synthetic_fixture\n",encoding="utf-8")
    rows,_ = read_input(tmp_path,"2026-09-30")
    assert rows[0]["confidence"] == "0.25"


def test_tampered_results_rejected(tmp_path,capsys):
    generate(tmp_path/"demo")
    path = tmp_path/"result.json"
    assert main(["run","--input",str(tmp_path/"demo"),"--out",str(path)]) == 0
    data = json.loads(path.read_text())
    data["correct"] += 1
    path.write_text(json.dumps(data),encoding="utf-8")
    assert main(["report","--results",str(path)]) == 2
    assert "SchemaError" in capsys.readouterr().err
