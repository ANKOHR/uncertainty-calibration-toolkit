"""Pure calibration logic. All metrics measure supplied observations only.

No inference, savings estimates, or confidence adjustment is performed.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction


class SchemaError(ValueError):
    """An input field violates the documented observation schema."""


def confidence_value(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise SchemaError("confidence: expected a finite decimal between 0 and 1")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise SchemaError("confidence: expected a finite decimal between 0 and 1") from None
    if not number.is_finite() or not 0 <= number <= 1:
        raise SchemaError("confidence: expected a finite decimal between 0 and 1")
    if len(str(value)) > 100 or abs(number.as_tuple().exponent) > 100:
        raise SchemaError("confidence: decimal precision exceeds 100 digits")
    return Fraction(number)


def validate_records(records, as_of="2026-09-30"):
    """Validate without modifying or dropping records; dates use explicit cutoff."""
    try:
        cutoff = date.fromisoformat(as_of)
    except (ValueError, TypeError):
        raise SchemaError("as_of: expected ISO date YYYY-MM-DD") from None
    seen = set()
    result = []
    allowed = {"id", "confidence", "correct", "synthetic", "source", "observed_on", "note"}
    for index, record in enumerate(records, 1):
        prefix = f"record {index}: "
        if not isinstance(record, dict):
            raise SchemaError(prefix + "record: expected object")
        extra = set(record) - allowed
        if extra:
            raise SchemaError(prefix + "unknown field: " + ", ".join(sorted(extra)))
        for field in ("id", "confidence", "correct", "synthetic", "source"):
            if field not in record:
                raise SchemaError(prefix + field + ": required field missing")
        ident = record["id"]
        if not isinstance(ident, str) or not ident.strip() or len(ident) > 1024:
            raise SchemaError(prefix + "id: expected nonempty string, at most 1024 characters")
        if ident in seen:
            raise SchemaError(prefix + "id: duplicate " + repr(ident))
        seen.add(ident)
        try:
            confidence_value(record["confidence"])
        except SchemaError as exc:
            raise SchemaError(prefix + str(exc)) from None
        for field in ("correct", "synthetic"):
            if type(record[field]) is not bool:
                raise SchemaError(prefix + field + ": expected boolean")
        source = record["source"]
        expected = "synthetic_fixture" if record["synthetic"] else "henry_entered"
        if source != expected:
            raise SchemaError(prefix + f"source: expected {expected}")
        if "note" in record and (not isinstance(record["note"], str) or len(record["note"]) > 10000):
            raise SchemaError(prefix + "note: expected string, at most 10000 characters")
        if "observed_on" in record:
            try:
                observed = date.fromisoformat(record["observed_on"])
            except (ValueError, TypeError):
                raise SchemaError(prefix + "observed_on: expected ISO date YYYY-MM-DD") from None
            if observed > cutoff:
                raise SchemaError(prefix + "observed_on: future date relative to as_of " + as_of)
        result.append(dict(record))
    return sorted(result, key=lambda item: item["id"])


def ratio(value):
    """Exact fraction; zero denominators for empty samples are handled upstream."""
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def analyze(records, as_of="2026-09-30"):
    records = validate_records(records, as_of)
    buckets = [[] for _ in range(10)]
    for record in records:
        p = confidence_value(record["confidence"])
        buckets[min(int(p * 10), 9)].append(record)
    count = len(records)
    correct = sum(r["correct"] for r in records)
    confidence_sum = sum((confidence_value(r["confidence"]) for r in records), Fraction())
    brier_sum = sum(((confidence_value(r["confidence"]) - int(r["correct"])) ** 2 for r in records), Fraction())
    bins = []
    ece_sum = Fraction()
    for index, bucket in enumerate(buckets):
        size = len(bucket)
        hits = sum(r["correct"] for r in bucket)
        mean = sum((confidence_value(r["confidence"]) for r in bucket), Fraction()) / (size or 1)
        accuracy = Fraction(hits, size or 1)
        gap = mean - accuracy
        ece_sum += abs(gap) * size
        bins.append({"index": index, "lower": ratio(Fraction(index, 10)),
                     "upper": ratio(Fraction(index + 1, 10)), "upper_inclusive": index == 9,
                     "count": size, "correct": hits, "accuracy": ratio(accuracy),
                     "mean_confidence": ratio(mean), "gap": ratio(gap),
                     "overconfident": bool(size and gap >= Fraction(1, 20))})
    synthetic = sum(r["synthetic"] for r in records)
    return {"schema_version": 1, "as_of": as_of, "count": count, "correct": correct,
            "incorrect": count - correct, "accuracy": ratio(Fraction(correct, count or 1)),
            "mean_confidence": ratio(confidence_sum / (count or 1)),
            "brier_score": ratio(brier_sum / (count or 1)), "ece": ratio(ece_sum / (count or 1)),
            "bins": bins, "overconfident_bins": [b["index"] for b in bins if b["overconfident"]],
            "high_confidence_error_ids": [r["id"] for r in records if not r["correct"] and confidence_value(r["confidence"]) >= Fraction(4, 5)],
            "provenance": {"synthetic_records": synthetic, "real_henry_entered_records": count - synthetic},
            "boundaries": {"scope": "Measured from supplied observations only; correctness and provenance are user declarations, not independently verified.",
                           "empty_metrics": "Zero by convention when no observations exist; no measured accuracy.",
                           "savings": "Time saved and money saved are unmeasured and are not reported.",
                           "illustrative": "Fixture outcomes are synthetic and illustrative, not real-world performance."}}
