"""Unit tests for every pure metric function in evals/harness/metrics.py."""

from evals.harness.metrics import (
    PRF,
    claim_key,
    keys_match,
    match_predictions,
    normalize_text,
    precision_recall_f1,
    rate,
)


class TestNormalizeText:
    def test_lowercases_and_collapses_whitespace(self):
        assert normalize_text("  Senior   Python\tEngineer ") == "senior python engineer"

    def test_keeps_language_punctuation(self):
        assert normalize_text("C++") == "c++"
        assert normalize_text("Node.js") == "node.js"
        assert normalize_text("C#") == "c#"

    def test_drops_other_punctuation(self):
        assert normalize_text("PostgreSQL, (WCAG 2.1)!") == "postgresql wcag 2.1"


class TestClaimKey:
    def test_prefers_normalized_skill_over_text(self):
        assert claim_key("6 years of Python", "Python") == "python"

    def test_falls_back_to_text_when_no_skill(self):
        assert claim_key("Senior Engineer at Cloudhatch") == "senior engineer at cloudhatch"

    def test_blank_skill_falls_back_to_text(self):
        assert claim_key("Rust", "   ") == "rust"


class TestKeysMatch:
    def test_exact(self):
        assert keys_match("python", "python")

    def test_containment_on_long_keys(self):
        assert keys_match("node.js", "node.js runtime")

    def test_short_keys_do_not_substring_match(self):
        # 'go' must not match 'golang' via containment (length gate protects against this).
        assert not keys_match("go", "golang")

    def test_empty_never_matches(self):
        assert not keys_match("", "python")
        assert not keys_match("python", "")


class TestMatchPredictions:
    def test_perfect_match(self):
        result = match_predictions(["python", "go"], ["python", "go"])
        assert (result.true_positives, result.false_positives, result.false_negatives) == (2, 0, 0)

    def test_false_positive_and_negative(self):
        # predicted jest (spurious), missed spark.
        result = match_predictions(["python", "jest"], ["python", "spark"])
        assert result.true_positives == 1
        assert result.false_positives == 1
        assert result.false_negatives == 1
        assert result.unmatched_pred_keys == ["jest"]
        assert result.unmatched_truth_keys == ["spark"]

    def test_each_truth_consumes_at_most_one_prediction(self):
        result = match_predictions(["python", "python"], ["python"])
        assert result.true_positives == 1
        assert result.false_positives == 1  # the duplicate prediction is spurious

    def test_empty_inputs(self):
        result = match_predictions([], [])
        assert (result.true_positives, result.false_positives, result.false_negatives) == (0, 0, 0)


class TestPrecisionRecallF1:
    def test_perfect(self):
        prf = precision_recall_f1(10, 0, 0)
        assert prf == PRF(1.0, 1.0, 1.0, 10, 0, 0)

    def test_balanced(self):
        prf = precision_recall_f1(8, 2, 2)
        assert prf.precision == 0.8
        assert prf.recall == 0.8
        assert abs(prf.f1 - 0.8) < 1e-9

    def test_zero_denominator_is_zero_not_crash(self):
        # 5 spurious predictions, no true positives, no ground-truth positives: precision is
        # 0/5 = 0.0, and recall's denominator is 0 so it degrades to 0.0 (not a crash).
        prf = precision_recall_f1(0, 5, 0)
        assert prf.precision == 0.0
        assert prf.recall == 0.0
        assert prf.f1 == 0.0

    def test_recall_one_when_no_false_negatives_but_some_tp(self):
        prf = precision_recall_f1(3, 2, 0)
        assert prf.recall == 1.0
        assert prf.precision == 0.6

    def test_all_zero_is_vacuous_one(self):
        assert precision_recall_f1(0, 0, 0).f1 == 1.0


class TestRate:
    def test_fraction_true(self):
        assert rate([True, True, False, False]) == 0.5

    def test_all_true(self):
        assert rate([True, True]) == 1.0

    def test_empty_is_one(self):
        assert rate([]) == 1.0
