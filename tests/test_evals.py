from resume_agent.evals import score

def test_score_counts_caught_missed_and_false_positives():
    results = [
        {"id": "a", "expect": ["ESCALATION_WORD"], "got": ["ESCALATION_WORD"]},
        {"id": "b", "expect": ["ENTAILMENT"], "got": []},
        {"id": "c", "expect": [], "got": ["UNIT_MISMATCH"]},
        {"id": "d", "expect": [], "got": []},
    ]
    s = score(results)
    assert s["bad_cases"] == 2 and s["caught"] == 1
    assert s["recall"] == 0.5
    assert s["good_cases"] == 2 and s["false_positive_cases"] == 1
    assert s["by_code"]["ENTAILMENT"] == {"expected": 1, "caught": 0}
