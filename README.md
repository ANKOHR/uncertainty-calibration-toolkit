# Uncertainty Calibration Toolkit

`uct` measures recorded confidence against recorded correctness using exact arithmetic. CPU only, Python standard library only, local files only. No models, network calls, predictions, or databases.

Hypothesis: a deterministic CLI with explicit inputs and tested ground truth provides trustworthy descriptive calibration measurements. Intended users are Henry and technical buyers evaluating his work.

## Quickstart

Python 3.10 or newer. Install from this checkout without contacting a package index:

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
uct fixtures --out demo
uct run --input demo
uct report --format md
python -m pytest -q
```

On Windows, if pip warns that its user Scripts directory is outside PATH, add the directory named in that warning to the current shell PATH, or use the module invocation below.

Pytest is a development prerequisite, not a runtime dependency. The same CLI can run without installation using `python -m uncertainty_calibration_toolkit.cli` in place of `uct`.

The smallest hand-written version is in `examples/tiny/records.jsonl`: five synthetic observations, accuracy 3/5, mean confidence 1/2, Brier score 3/40, ECE 1/5. Run `uct run --input examples/tiny`, then `uct report --format md`.

## Input reference

A directory contains UTF-8 JSON arrays, JSONL objects, or CSV files. Whole lines starting with `#` are a supported comment extension, including in fixture JSON. YAML is deliberately unsupported and returns a named error with an alternative format. Only `expectations.json` and `README.md` are ignored. Other unsupported file extensions fail, rather than silently disappearing.

```json
{"id":"prediction-1","confidence":"0.8","correct":false,"synthetic":false,"source":"henry_entered","observed_on":"2026-09-30","note":"Hand-checked outcome"}
```

Required fields:

| Field | Rule |
| --- | --- |
| id | Unique nonblank string, maximum 1024 characters, across all files |
| confidence | Finite decimal between 0 and 1 inclusive; string or JSON number; maximum 100 characters and decimal exponent magnitude 100 |
| correct | Boolean, supplied correctness for an observed outcome |
| synthetic | Boolean, explicit author declaration |
| source | `synthetic_fixture` when synthetic, otherwise `henry_entered` |

Optional `observed_on` is an ISO date no later than the explicit `--as-of` cutoff. Optional `note` is a string of at most 10000 characters. Unknown fields, including amounts or savings, fail with a schema error. Negative confidence, future dates, oversized strings, duplicate IDs and duplicate JSON keys fail. No records are silently dropped. CSV booleans must be lowercase `true` or `false`; confidence is decimal text. Unicode and Windows path strings are supported. JSON serialization escapes Unicode losslessly; report text escapes the prohibited dash character.

Henry can enter his own hand-checked observations with `synthetic: false` and `source: henry_entered`. Keep real trial data outside the shipped repo. Author declarations of correctness and provenance are not independently verified.

## Commands

| Command | Example | Purpose |
| --- | --- | --- |
| fixtures | `uct fixtures --out demo` | Write 200 synthetic records and independent expectations |
| run | `uct run --input demo --out .uct/results.json --as-of 2026-09-30` | Validate and calculate exact metrics |
| report | `uct report --format json --out report.json` | Render JSON or Markdown with provenance |
| bins | `uct bins --results .uct/results.json` | Inspect reliability bins in the full Markdown report |
| audit | `uct audit --input demo` | Validate and print metrics and high-confidence error IDs without storing results |

Every subcommand includes `--help` and an example. Reports and bins default to `.uct/results.json`; `report --results PATH` reads a different run. Failed commands return 2 with a named error. Success returns 0.

## Measurements and planted ground truth

Accuracy is correct count divided by count. Mean confidence is the arithmetic mean. Brier score is the mean squared difference between confidence and boolean correctness. ECE is the count-weighted mean absolute calibration gap over ten fixed bins. Bins are lower inclusive, upper exclusive, with 1 included in the final bin. Overconfidence flags require a populated bin and mean confidence minus accuracy at least 0.05. High-confidence errors have confidence at least 0.8 and correctness false. These are descriptive flags, not statistical significance or causal claims. Empty samples have zero metrics by convention and no measured accuracy.

Exact values are reduced numerator/denominator objects in JSON. Markdown prints exact terminating decimals or fractions, never rounded estimates. Result files retain observations and sorted filenames with SHA-256 hashes. Reports revalidate the observations and recompute metrics before trusting stored figures. Identical inputs and options produce byte-identical outputs. There is no randomness and no seed; the date cutoff defaults to the fixed brief date, 2026-09-30.

The synthetic fixture has ten groups of 20 records. Group k, for k=0..9, has confidence (2k+1)/20 and exactly 2k correct observations. The independent arithmetic is:

- Count 200; correct 90; incorrect 110; confidence sum 100.
- Accuracy 9/20; mean confidence 1/2.
- Squared error sum 33.5, so Brier score 67/400.
- Every group's confidence exceeds accuracy by 1/20, so ECE is 1/20 and all ten bins are flagged.
- Exactly six high-confidence errors: g8-r16, g8-r17, g8-r18, g8-r19, g9-r18, g9-r19.

These figures describe illustrative planted data, not real-world performance. Tests compare the computed figures and complete flag sets to literal expectations, reconcile bin totals, and corrupt an outcome to demonstrate the figures change. `EVIDENCE.md` records actual local validation and demo timing.

## Architecture

```text
fixtures.py -> labelled local input files
local input -> cli.py parser and validation -> core.py pure exact calculations
                                          -> atomic results file
results -> cli.py recomputation check -> report.py -> stdout or atomic report file
```

## Honesty boundary and fixture policy

The tool computes from supplied observations only. It cannot discover correctness, predict future outcomes, establish significance, or independently authenticate Henry's data. Synthetic figures are illustrative, labelled in every fixture with a header and `synthetic: true`, and in CLI output and report provenance banners. Mixed reports give synthetic and Henry-entered counts. Every generated fixture file carries the synthetic label, including the expectations file. Expectations are not used by the engine.

Time saved and money saved are unmeasured and not reported. This version does not accept baseline measurements or savings fields. No commercial outcome, real-use result, or future verdict is claimed. Do not use the synthetic scores as evidence of deployment accuracy.

## Failure modes and limits

Malformed JSON and CSV return `ParseError` with filename and line. JSON array schema errors identify the file, field and container line 1; JSONL provides the physical record line. Unsupported YAML names line 1. Missing directories return `MissingInput` with a usage hint. Schema drift returns `SchemaError` with the offending field. Corrupt stored results fail validation. File failures have named errors; report writes use a temporary sibling and atomic replace, cleaning temporary files on failure. Existing reports survive failed replacement.

The tool reads inputs into memory. Extremely large datasets are outside the tested 200-record outcome. The fixed bin design can hide within-bin variation; descriptive flags are sensitive to sample size and threshold choice. The fixed date cutoff must be advanced explicitly for later real observations.

## Evidence-based improvement hook and verdict

Start the two-week window at the first real use, not at this synthetic build. Record each real run locally: date, whether used, hand-checked sample size, number of incorrect toolkit outputs, and top failure cause. The primary metric is output error rate against a hand-checked sample: incorrect checked outputs / all checked outputs. Keep the definition of each checked output consistent and record it before the trial. With zero checked outputs, the rate is unmeasured.

After two weeks, if error rate exceeds 10 percent, fix the top measured failure cause or kill with a recorded reason. If never used, kill with that reason. Record one evidence-based improvement and retest it. `VERDICT.md` holds the pending verdict and recording template: expand for daily use or revenue; integrate for heavy sibling overlap; commercialise if a buyer would pay as-is; maintain as portfolio evidence otherwise; kill if unused or acceptance criteria cannot be met. A final verdict requires the two-week real-use evidence window.
