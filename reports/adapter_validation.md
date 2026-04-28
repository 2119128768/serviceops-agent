# Adapter Validation

This report validates local PEFT/LoRA adapter directories without printing raw weights.

## Router LoRA

- directory: found `outputs/router-lora-v1`
- size: `129M`
- adapter_config.json: found
- adapter weights: found `adapter_model.safetensors`
- status: valid

## Verifier LoRA

- directory: found `outputs/verifier-lora-v1`
- size: `129M`
- adapter_config.json: found
- adapter weights: found `adapter_model.safetensors`
- status: valid

## Summary

- adapter_missing: false
- generated_by: `scripts/validate_adapters.sh`
