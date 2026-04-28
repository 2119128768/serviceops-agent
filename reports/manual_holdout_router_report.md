# Router SFT Report

| mode | json_valid | intent_acc | priority_acc | routing_acc | missing_f1 | tools_acc | human_acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Rule Router | 1.0 | 0.8 | 0.92 | 0.86 | 0.9267 | 0.88 | 0.92 |
| Prompt Router | not_run | not_run | not_run | not_run | not_run | not_run | not_run |
| Router LoRA | not_run | not_run | not_run | not_run | not_run | not_run | not_run |

Latest metrics:

```json
{
  "rows": 50,
  "json_valid_rate": 1.0,
  "intent_accuracy": 0.8,
  "priority_accuracy": 0.92,
  "routing_accuracy": 0.86,
  "missing_info_precision": 0.93,
  "missing_info_recall": 0.93,
  "missing_info_f1": 0.9267,
  "required_tools_accuracy": 0.88,
  "requires_human_accuracy": 0.92,
  "mode": "rule",
  "test_file": "data/eval/manual_holdout_router.jsonl"
}
```
