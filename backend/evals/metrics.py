from __future__ import annotations


def exact_match(expected, predicted) -> float:
    return 1.0 if expected == predicted else 0.0


def accuracy(rows: list[tuple[object, object]]) -> float:
    if not rows:
        return 0.0
    return sum(exact_match(expected, predicted) for expected, predicted in rows) / len(rows)


def f1_for_list(expected: list[str], predicted: list[str]) -> dict:
    expected_set = set(expected)
    predicted_set = set(predicted)
    true_positive = len(expected_set & predicted_set)
    precision = true_positive / len(predicted_set) if predicted_set else (1.0 if not expected_set else 0.0)
    recall = true_positive / len(expected_set) if expected_set else 1.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def list_exact_match(expected: list[str], predicted: list[str]) -> float:
    return 1.0 if set(expected) == set(predicted) else 0.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
