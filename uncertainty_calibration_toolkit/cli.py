"""Local-only CLI. Input errors have names, filenames, and line numbers."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from decimal import Decimal

from .core import SchemaError, analyze, validate_records
from .fixtures import generate
from .report import json_text, render


class InputError(ValueError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field " + key)
        result[key] = value
    return result


def _json(text, filename, line=0):
    try:
        return json.loads(text, object_pairs_hook=_unique_object, parse_float=Decimal, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite number " + value)))
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {filename}: line {line or exc.lineno}: {exc.msg}") from None
    except ValueError as exc:
        raise InputError(f"ParseError: {filename}: line {line or 1}: {exc}") from None


def read_input(directory, as_of):
    directory = Path(directory)
    if not directory.is_dir():
        raise InputError(f"MissingInput: {directory}: use --input with an existing directory; try uct fixtures --out demo")
    validate_records([], as_of)
    observations, inputs = [], []
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name not in {"expectations.json", "README.md"})
    for path in files:
        if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".yaml", ".yml"}:
            raise InputError(f"SchemaError: {path}: line 1: unsupported input file extension")
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InputError(f"ParseError: {path}: line 1: input must be UTF-8 (byte {exc.start})") from None
        inputs.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
        if path.suffix.lower() in {".yaml", ".yml"}:
            raise InputError(f"ParseError: {path}: line 1: YAML is unsupported; use JSON, JSONL, or CSV")
        # Whole-line comments label fixtures and preserve original error lines.
        cleaned = "\n".join("" if line.lstrip().startswith("#") else line for line in text.splitlines())
        located = []
        if path.suffix.lower() == ".jsonl":
            located = [(number, _json(line, path, number)) for number, line in enumerate(cleaned.splitlines(), 1) if line.strip()]
        elif path.suffix.lower() == ".json":
            value = _json(cleaned, path)
            if not isinstance(value, list):
                raise InputError(f"SchemaError: {path}: line 1: JSON input must be an array of records")
            located = [(1, item) for item in value]
        else:
            reader = csv.DictReader(io.StringIO(cleaned.lstrip("\n")), strict=True)
            offset = len(cleaned) - len(cleaned.lstrip("\n"))
            try:
                if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
                    raise InputError(f"SchemaError: {path}: line 1: missing or duplicate CSV header")
                for record in reader:
                    number = reader.line_num + offset
                    if None in record or any(value is None for value in record.values()):
                        raise InputError(f"ParseError: {path}: line {number}: CSV row width differs from header")
                    for field in ("correct", "synthetic"):
                        if record.get(field) not in {"true", "false"}:
                            raise InputError(f"SchemaError: {path}: line {number}: {field}: CSV requires true or false")
                        record[field] = record[field] == "true"
                    located.append((number, record))
            except csv.Error as exc:
                raise InputError(f"ParseError: {path}: line {reader.reader.line_num + offset}: {exc}") from None
        for number, record in located:
            try:
                validate_records([record], as_of)
                if any(old["id"] == record["id"] for old in observations):
                    raise SchemaError("id: duplicate " + repr(record["id"]))
            except SchemaError as exc:
                raise InputError(f"SchemaError: {path}: line {number}: {exc}") from None
            observations.append(record)
    return observations, inputs


def atomic_write(path, text):
    """Replace only after a full successful write; remove temporary files on failure."""
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=".uct-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError(f"WriteError: {path}: {exc.strerror or str(exc)}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_result(path):
    path = Path(path)
    if not path.is_file():
        raise InputError(f"MissingResults: {path}: run uct run --input <dir> first")
    value = _json(path.read_text(encoding="utf-8"), path)
    # Require the exact generated result structure to prevent misleading reports.
    try:
        expected = analyze(value["observations"], value["as_of"])
        for field, actual in expected.items():
            if value[field] != actual:
                raise ValueError(field)
        if not isinstance(value["inputs"], list):
            raise ValueError("inputs")
    except (KeyError, TypeError, ValueError) as exc:
        raise InputError(f"SchemaError: {path}: line 1: invalid or inconsistent results field {exc}") from None
    return value


def parser():
    root = argparse.ArgumentParser(prog="uct", description="Measure supplied confidence against supplied correctness. Local files only.")
    commands = root.add_subparsers(dest="command", required=True)
    fixture = commands.add_parser("fixtures", help="Generate 200 labelled synthetic observations", epilog="Example: uct fixtures --out demo")
    fixture.add_argument("--out", required=True)
    run = commands.add_parser("run", help="Validate input and calculate exact metrics", epilog="Example: uct run --input demo")
    run.add_argument("--input", required=True)
    run.add_argument("--out", default=".uct/results.json")
    run.add_argument("--as-of", default="2026-09-30", help="Explicit date cutoff, default 2026-09-30; no wall-clock dependence")
    report = commands.add_parser("report", help="Render provenance-labelled report", epilog="Example: uct report --format md")
    report.add_argument("--format", choices=("md", "json"), default="md")
    report.add_argument("--results", default=".uct/results.json")
    report.add_argument("--out", help="Atomic UTF-8 report file, otherwise stdout")
    bins = commands.add_parser("bins", help="Inspect fixed reliability bins and exact gaps", epilog="Example: uct bins --results .uct/results.json")
    bins.add_argument("--results", default=".uct/results.json")
    audit = commands.add_parser("audit", help="Validate observations and list high-confidence errors", epilog="Example: uct audit --input demo")
    audit.add_argument("--input", required=True)
    audit.add_argument("--as-of", default="2026-09-30")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print("SYNTHETIC illustrative fixture: 200 records written to " + args.out)
        elif args.command in {"run", "audit"}:
            observations, inputs = read_input(args.input, args.as_of)
            result = analyze(observations, args.as_of)
            # Store decimal confidence as a string to preserve exact input values.
            result["observations"] = [{**r, "confidence": str(r["confidence"])} for r in validate_records(observations, args.as_of)]
            result["inputs"] = inputs
            if args.command == "run":
                atomic_write(args.out, json_text(result))
                print(f"Computed {result['count']} observations; SYNTHETIC illustrative={result['provenance']['synthetic_records']}; Henry-entered={result['provenance']['real_henry_entered_records']}. Results: {args.out}")
            else:
                print(render(result, "json"), end="")
        else:
            result = load_result(args.results)
            output = render(result, "md" if args.command == "bins" else args.format)
            if args.command == "report" and args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        return 0
    except (InputError, SchemaError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"FileError: {exc.filename}: line 1: {exc.strerror}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
