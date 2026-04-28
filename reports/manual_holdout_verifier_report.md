# Verifier SFT Report

| mode | json_valid | support_acc | unsupported_recall | false_approval |
| --- | ---: | ---: | ---: | ---: |
| prompt | 1.0 | 0.12 | 1.0 | 0.38 |
| lora | not_run | not_run | not_run | not_run |

Latest metrics:

```json
{
  "rows": 50,
  "json_valid_rate": 1.0,
  "support_accuracy": 0.12,
  "unsupported_claim_recall": 1.0,
  "citation_error_detection_accuracy": 0.5,
  "risk_detection_recall": 0.5128,
  "requires_approval_accuracy": 0.3,
  "false_approval_rate": 0.38,
  "mode": "prompt",
  "test_file": "data/eval/manual_holdout_verifier.jsonl"
}
```
