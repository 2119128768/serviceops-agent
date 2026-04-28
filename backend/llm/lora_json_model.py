from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.llm.json_utils import extract_json_object


class LoraJsonModel:
    """Lazy PEFT adapter runner for short deterministic JSON generations."""

    def __init__(
        self,
        base_model: str,
        adapter_path: str,
        system_prompt: str,
        max_new_tokens: int = 256,
    ) -> None:
        self.base_model = base_model
        self.adapter_path = adapter_path
        self.system_prompt = system_prompt
        self.max_new_tokens = min(max_new_tokens, 256)
        self._loaded = False
        self._torch: Any = None
        self._tokenizer: Any = None
        self._model: Any = None

    def generate_json(self, user_prompt: str) -> dict[str, Any]:
        self._ensure_loaded()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        templated = self._tokenizer.apply_chat_template(
            messages,
            return_tensors="pt",
            add_generation_prompt=True,
        )
        if hasattr(templated, "keys"):
            inputs = dict(templated)
            if "attention_mask" not in inputs:
                inputs["attention_mask"] = self._torch.ones_like(inputs["input_ids"])
        else:
            inputs = {
                "input_ids": templated,
                "attention_mask": self._torch.ones_like(templated),
            }
        inputs = {key: value.to(self._model.device) for key, value in inputs.items()}
        with self._torch.inference_mode():
            generated = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        text = self._tokenizer.decode(
            generated[0][inputs["input_ids"].shape[-1] :],
            skip_special_tokens=True,
        )
        return extract_json_object(text)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        adapter = Path(self.adapter_path)
        if not adapter.exists():
            raise RuntimeError(f"LoRA adapter path not found: {self.adapter_path}")
        if not (adapter / "adapter_config.json").exists():
            raise RuntimeError(f"LoRA adapter_config.json not found: {adapter / 'adapter_config.json'}")
        if not ((adapter / "adapter_model.safetensors").exists() or (adapter / "adapter_model.bin").exists()):
            raise RuntimeError(f"LoRA adapter weights not found in: {self.adapter_path}")

        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("Install LoRA runtime dependencies with: pip install -e '.[training]'") from exc

        try:
            local_files_only = os.getenv("SERVICEOPS_LOCAL_FILES_ONLY", "0") == "1"
            tokenizer = AutoTokenizer.from_pretrained(
                self.base_model,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                device_map="auto",
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            model = PeftModel.from_pretrained(model, self.adapter_path)
        except Exception as exc:  # pragma: no cover - depends on local model availability
            raise RuntimeError(
                f"Failed to load base model '{self.base_model}' with adapter '{self.adapter_path}'. "
                "Provide a local base model path or run on a machine with the model cached."
            ) from exc

        model.eval()
        model.generation_config.do_sample = False
        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model
        self._loaded = True
