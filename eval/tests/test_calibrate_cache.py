import pytest

from eval.calibrate_cache import summarise_pairs


def test_calibration_reports_false_hits_and_selects_a_safe_measured_threshold():
    result = summarise_pairs([
        {"id": "paraphrase", "equivalent": True, "similarity": .99},
        {"id": "regular-vs-summer", "equivalent": False, "similarity": .94},
        {"id": "min-vs-max", "equivalent": False, "similarity": .91},
    ])
    assert len(result["trials"]) == 3
    assert result["trials"][0]["false_hits"]
    assert .94 < result["selected_threshold"] < .99
    assert result["trials"][-1]["true_hits"] == ["paraphrase"]
    assert result["trials"][-1]["false_hits"] == []


def test_calibration_fails_closed_if_every_tested_threshold_has_false_hits():
    with pytest.raises(ValueError, match="no tested threshold"):
        summarise_pairs([{"id": "positive", "equivalent": True, "similarity": 1.0},
                         {"id": "negative", "equivalent": False, "similarity": .99}])
