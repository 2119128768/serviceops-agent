from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


def validate_prompt_completion(path: str | Path) -> dict[str, int]:
    rows = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        row = json.loads(line)
        if "prompt" not in row or "completion" not in row:
            raise ValueError(f"{path}:{line_no} missing prompt/completion")
        if not isinstance(row["prompt"], list) or not isinstance(row["completion"], list):
            raise ValueError(f"{path}:{line_no} prompt/completion must be conversational lists")
        content = row["completion"][0].get("content", "")
        json.loads(content)
        rows.append(row)
    return {"rows": len(rows)}


def train(config_path: str | Path, dry_run: bool = False, resume_from_checkpoint: str | None = None) -> None:
    config = load_config(config_path)
    train_stats = validate_prompt_completion(config["train_file"])
    val_stats = validate_prompt_completion(config["val_file"])
    print(
        f"validated task={config['task_name']} train_rows={train_stats['rows']} "
        f"val_rows={val_stats['rows']}"
    )
    if dry_run:
        print("dry-run complete; data format is valid")
        return

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:  # pragma: no cover - depends on optional training env
        raise SystemExit(
            "Training dependencies are not installed. Run: pip install -e '.[training]'"
        ) from exc

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU not detected. Use --dry-run locally or run on a GPU host.")

    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_cfg = None
    quantization = config.get("quantization", {})
    if quantization.get("load_in_4bit", False):
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=quantization.get("bnb_4bit_quant_type", "nf4"),
            bnb_4bit_compute_dtype=getattr(
                torch, quantization.get("bnb_4bit_compute_dtype", "bfloat16")
            ),
            bnb_4bit_use_double_quant=quantization.get("bnb_4bit_use_double_quant", True),
        )

    model = AutoModelForCausalLM.from_pretrained(
        config["base_model"],
        quantization_config=quant_cfg,
        device_map="auto",
        trust_remote_code=True,
    )

    dataset = load_dataset(
        "json",
        data_files={"train": config["train_file"], "validation": config["val_file"]},
    )

    def to_text(row: dict) -> dict:
        messages = row["prompt"] + row["completion"]
        row["text"] = tokenizer.apply_chat_template(messages, tokenize=False)
        return row

    dataset = dataset.map(to_text)

    peft_config = LoraConfig(
        r=config["lora"]["r"],
        lora_alpha=config["lora"]["alpha"],
        lora_dropout=config["lora"]["dropout"],
        target_modules=config["lora"]["target_modules"],
        task_type="CAUSAL_LM",
    )

    sft_config = _make_sft_config(SFTConfig, config)

    trainer_kwargs = {
        "model": model,
        "args": sft_config,
        "train_dataset": dataset["train"],
        "eval_dataset": dataset["validation"],
        "peft_config": peft_config,
    }
    trainer_signature = inspect.signature(SFTTrainer)
    if "tokenizer" in trainer_signature.parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    elif "processing_class" in trainer_signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    if "dataset_text_field" in trainer_signature.parameters:
        trainer_kwargs["dataset_text_field"] = "text"
    if "max_seq_length" in trainer_signature.parameters:
        trainer_kwargs["max_seq_length"] = config["max_seq_length"]

    trainer = SFTTrainer(**trainer_kwargs)
    trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    trainer.save_model(config["output_dir"])
    print(f"training complete; adapter saved to {config['output_dir']}")


def _make_sft_config(SFTConfig, config: dict[str, Any]):
    signature = inspect.signature(SFTConfig)
    kwargs = {
        "output_dir": config["output_dir"],
        "num_train_epochs": config["num_train_epochs"],
        "learning_rate": config["learning_rate"],
        "warmup_ratio": config.get("warmup_ratio", 0.03),
        "per_device_train_batch_size": config["per_device_train_batch_size"],
        "gradient_accumulation_steps": config["gradient_accumulation_steps"],
        "eval_steps": config["eval_steps"],
        "save_steps": config["save_steps"],
        "logging_steps": config["logging_steps"],
        "bf16": config.get("bf16", True),
        "gradient_checkpointing": config.get("gradient_checkpointing", True),
    }
    if "max_length" in signature.parameters:
        kwargs["max_length"] = config["max_seq_length"]
    if "max_seq_length" in signature.parameters:
        kwargs["max_seq_length"] = config["max_seq_length"]
    if "eval_strategy" in signature.parameters:
        kwargs["eval_strategy"] = "steps"
    elif "evaluation_strategy" in signature.parameters:
        kwargs["evaluation_strategy"] = "steps"
    if "dataset_text_field" in signature.parameters:
        kwargs["dataset_text_field"] = "text"
    filtered = {key: value for key, value in kwargs.items() if key in signature.parameters}
    return SFTConfig(**filtered)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume-from-checkpoint", default=None)
    args = parser.parse_args()
    train(args.config, dry_run=args.dry_run, resume_from_checkpoint=args.resume_from_checkpoint)


if __name__ == "__main__":
    main()
