"""Stable serialization and provenance-labelled report rendering."""
import json
from decimal import Decimal
from fractions import Fraction


def banner(result):
    provenance = result["provenance"]
    return ("DATA PROVENANCE: SYNTHETIC illustrative fixtures: " + str(provenance["synthetic_records"])
            + "; REAL Henry-entered observations: " + str(provenance["real_henry_entered_records"])
            + ". Labels are declared by the input author; they are not verified.")


def json_text(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"


def exact(value):
    fraction = Fraction(value["numerator"], value["denominator"])
    denominator = fraction.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator == 1:
        # At most 200 digits in input squares; avoid rounding exact decimals.
        from decimal import localcontext
        with localcontext() as context:
            context.prec = 500
            return format(Decimal(fraction.numerator) / Decimal(fraction.denominator), "f")
    return str(fraction)


def render(result, format="md"):
    if format == "json":
        return json_text({"provenance_banner": banner(result), **result})
    if format != "md":
        raise ValueError("format must be md or json")
    lines = ["# Uncertainty Calibration Toolkit", "", banner(result), "",
             "All values are computed from supplied observations. Synthetic figures are illustrative.",
             "Correctness is supplied, not independently measured by this tool.", "",
             f"Observations: {result['count']}; correct: {result['correct']}; incorrect: {result['incorrect']}.", "",
             "| Metric | Exact value |", "| --- | --- |"]
    for field in ("accuracy", "mean_confidence", "brier_score", "ece"):
        lines.append(f"| {field} | {exact(result[field])} |")
    lines += ["", "Ten fixed bins: lower inclusive, upper exclusive, except 1 is in the last bin.", "",
              "| Bin | Count | Correct | Accuracy | Mean confidence | Confidence minus accuracy | Overconfident |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for b in result["bins"]:
        lines.append(f"| {b['index']} | {b['count']} | {b['correct']} | {exact(b['accuracy'])} | {exact(b['mean_confidence'])} | {exact(b['gap'])} | {str(b['overconfident']).lower()} |")
    lines += ["", "Overconfident bins (gap >= 0.05): " + json.dumps(result["overconfident_bins"]),
              "High-confidence errors (confidence >= 0.8): " + json.dumps(result["high_confidence_error_ids"], ensure_ascii=True), "",
              "These are descriptive flags, not predictions or statistical significance tests.",
              "Empty samples use zero metrics by convention, not measured accuracy.",
              "Time saved and money saved: unmeasured; not reported.", ""]
    lines += ["Input files and SHA-256 fingerprints:"]
    for item in result.get("inputs", []):
        lines.append(json.dumps(item, ensure_ascii=True, sort_keys=True))
    lines.append("")
    return "\n".join(lines).replace(chr(0x2014), "\\u2014")
