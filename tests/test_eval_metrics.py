from backend.evals.metrics import f1_for_list


def test_list_f1_partial_match():
    score = f1_for_list(["account_id", "order_id"], ["account_id"])
    assert round(score["precision"], 2) == 1.0
    assert round(score["recall"], 2) == 0.5
    assert round(score["f1"], 2) == 0.67
