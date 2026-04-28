from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from backend.llm.json_utils import extract_json_object, normalize_list_fields

LOGGER = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = "你是企业技术支持工单 Router。请只输出合法 JSON，不要输出解释。"
VERIFIER_SYSTEM_PROMPT = "你是企业 Agent 回复风险 Verifier。请只输出合法 JSON，不要输出解释。"


class LocalModelUnavailable(RuntimeError):
    """Raised when local LoRA inference cannot be initialized."""


class LocalLoRAJsonModel:
    """Local base-model runtime for Router and Verifier LoRA JSON inference."""

    def __init__(
        self,
        base_model_path_or_id: str = "models/Qwen2.5-3B-Instruct",
        router_adapter_path: str = "outputs/router-lora-v1",
        verifier_adapter_path: str = "outputs/verifier-lora-v1",
        device: str = "auto",
        torch_dtype: str = "auto",
        max_new_tokens: int = 256,
    ) -> None:
        self.base_model_path_or_id = base_model_path_or_id
        self.router_adapter_path = router_adapter_path
        self.verifier_adapter_path = verifier_adapter_path
        self.device_request = device
        self.torch_dtype_request = torch_dtype
        self.max_new_tokens = min(max_new_tokens, 256)

        self._loaded = False
        self._torch: Any = None
        self._tokenizer: Any = None
        self._model: Any = None
        self._router_model: Any = None
        self._verifier_model: Any = None
        self._multi_adapter = False
        self.device = "unknown"
        self.load_seconds = 0.0
        self.last_generation_ms = 0.0

    def predict_router(self, ticket_text: str) -> dict[str, Any]:
        raw = self._generate(
            adapter_name="router",
            system_prompt=ROUTER_SYSTEM_PROMPT,
            user_prompt=f"工单：{ticket_text}",
        )
        output = extract_json_object(raw)
        output = normalize_list_fields(output, ["missing_info", "required_tools"])
        output.setdefault("intent", "json_invalid")
        output.setdefault("product", "unknown")
        output.setdefault("priority", "P3")
        output.setdefault("suggested_team", "support_queue")
        output.setdefault("secondary_team", "")
        output.setdefault("needs_rag", True)
        output.setdefault("requires_human", False)
        output.setdefault("risk_level", "medium" if output.get("requires_human") else "low")
        output["raw_json_valid"] = bool(extract_json_object(raw))
        return output

    def predict_verifier(self, payload: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(payload, str):
            user_prompt = payload
        else:
            user_prompt = (
                "请检查以下企业工单回复是否被证据支持、是否有错误引用、是否包含敏感动作、是否需要人工审批。\n"
                "只输出 JSON。\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True)
            )
        raw = self._generate(
            adapter_name="verifier",
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        output = extract_json_object(raw)
        output = normalize_list_fields(output, ["unsupported_claims", "citation_errors"])
        output.setdefault("supported_by_evidence", False)
        output.setdefault("contains_sensitive_action", False)
        output.setdefault("requires_approval", True)
        output.setdefault("risk_level", "medium")
        output.setdefault("decision", "revise_before_reply")
        output["raw_json_valid"] = bool(extract_json_object(raw))
        return output

    def smoke_test(self) -> dict[str, Any]:
        router = self.predict_router(
            "我们调用模型 API 一直返回 429，提示 quota exceeded，昨天刚充值。request_id: req_20260427_001"
        )
        verifier = self.predict_verifier(
            {
                "ticket": "API 返回 429，用户称已充值。",
                "draft_reply": "我们已经确认订单支付成功，会立即恢复额度。",
                "evidence": [
                    {
                        "doc_id": "billing_recharge_sync",
                        "chunk_id": "billing_recharge_sync_001",
                        "content": "订单状态未知时不得承诺额度已恢复；修改额度需要人工审批。",
                    }
                ],
                "tool_results": [],
                "router_output": router,
                "plan": {"steps": ["补充 account_id 和 order_id 后查询订单状态。"]},
            }
        )
        return {
            "router": router,
            "verifier": verifier,
            "runtime": {
                "device": self.device,
                "multi_adapter": self._multi_adapter,
                "load_seconds": round(self.load_seconds, 3),
                "last_generation_ms": round(self.last_generation_ms, 3),
            },
        }

    def _generate(self, adapter_name: str, system_prompt: str, user_prompt: str) -> str:
        self._ensure_loaded()
        model = self._select_adapter(adapter_name)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if hasattr(self._tokenizer, "apply_chat_template"):
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
        else:
            prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n"
            inputs = self._tokenizer(prompt, return_tensors="pt")

        model_device = self._model_device(model)
        inputs = {key: value.to(model_device) for key, value in inputs.items()}

        started = time.perf_counter()
        with self._torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        self.last_generation_ms = (time.perf_counter() - started) * 1000
        LOGGER.info("local_lora_generation adapter=%s ms=%.2f", adapter_name, self.last_generation_ms)
        prompt_tokens = inputs["input_ids"].shape[-1]
        return self._tokenizer.decode(generated[0][prompt_tokens:], skip_special_tokens=True)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._validate_paths()
        started = time.perf_counter()
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - optional local dependency
            raise LocalModelUnavailable(
                "Local LoRA runtime dependencies are missing. Run: bash scripts/setup_local_model.sh"
            ) from exc

        self._torch = torch
        self.device = self._resolve_device(torch)
        dtype = self._resolve_dtype(torch)
        local_files_only = self._local_files_only()

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_path_or_id,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            base_model = self._load_base_model(AutoModelForCausalLM, dtype, local_files_only)
            model = PeftModel.from_pretrained(
                base_model,
                self.router_adapter_path,
                adapter_name="router",
            )
            model.load_adapter(self.verifier_adapter_path, adapter_name="verifier")
            model.eval()
            self._model = model
            self._multi_adapter = True
        except Exception as exc:
            LOGGER.warning("Multi-adapter local LoRA load failed; falling back to separate models: %s", exc)
            try:
                router_base = self._load_base_model(AutoModelForCausalLM, dtype, local_files_only)
                verifier_base = self._load_base_model(AutoModelForCausalLM, dtype, local_files_only)
                self._router_model = PeftModel.from_pretrained(
                    router_base,
                    self.router_adapter_path,
                    adapter_name="router",
                )
                self._verifier_model = PeftModel.from_pretrained(
                    verifier_base,
                    self.verifier_adapter_path,
                    adapter_name="verifier",
                )
                self._router_model.eval()
                self._verifier_model.eval()
                self._multi_adapter = False
            except Exception as fallback_exc:
                raise LocalModelUnavailable(
                    "Failed to load local base model with Router/Verifier adapters. "
                    "Check LOCAL_BASE_MODEL_PATH and run: bash scripts/check_local_model.sh"
                ) from fallback_exc

        self.load_seconds = time.perf_counter() - started
        LOGGER.info(
            "local_lora_loaded device=%s multi_adapter=%s seconds=%.2f",
            self.device,
            self._multi_adapter,
            self.load_seconds,
        )
        self._loaded = True

    def _validate_paths(self) -> None:
        base = Path(self.base_model_path_or_id).expanduser()
        if self._looks_like_local_path(self.base_model_path_or_id) and not (base / "config.json").exists():
            raise LocalModelUnavailable(
                f"Local base model is missing or incomplete at {base}. "
                "Run: DOWNLOAD_BASE_MODEL=1 bash scripts/setup_local_model.sh"
            )

        for label, path in {
            "router": self.router_adapter_path,
            "verifier": self.verifier_adapter_path,
        }.items():
            adapter = Path(path)
            if not adapter.exists():
                raise LocalModelUnavailable(f"{label} adapter path not found: {path}")
            if not (adapter / "adapter_config.json").exists():
                raise LocalModelUnavailable(f"{label} adapter_config.json not found in: {path}")
            if not ((adapter / "adapter_model.safetensors").exists() or (adapter / "adapter_model.bin").exists()):
                raise LocalModelUnavailable(f"{label} adapter weights not found in: {path}")

    def _load_base_model(self, model_cls: Any, dtype: Any, local_files_only: bool) -> Any:
        kwargs = {
            "trust_remote_code": True,
            "local_files_only": local_files_only,
            "low_cpu_mem_usage": True,
        }
        if dtype is not None:
            kwargs["torch_dtype"] = dtype
        model = model_cls.from_pretrained(self.base_model_path_or_id, **kwargs)
        if self.device in {"cuda", "mps"}:
            model.to(self.device)
        return model

    def _select_adapter(self, adapter_name: str) -> Any:
        if self._multi_adapter:
            self._model.set_adapter(adapter_name)
            return self._model
        if adapter_name == "router" and self._router_model is not None:
            return self._router_model
        if adapter_name == "verifier" and self._verifier_model is not None:
            return self._verifier_model
        raise LocalModelUnavailable(f"Adapter is not loaded: {adapter_name}")

    def _resolve_device(self, torch: Any) -> str:
        request = self.device_request.lower()
        if request != "auto":
            return request
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _resolve_dtype(self, torch: Any) -> Any:
        request = self.torch_dtype_request.lower()
        if request == "auto":
            if self.device == "cuda":
                return torch.bfloat16
            if self.device == "mps":
                return torch.float16
            return torch.float32
        if request in {"float16", "fp16"}:
            return torch.float16
        if request in {"bfloat16", "bf16"}:
            return torch.bfloat16
        if request in {"float32", "fp32"}:
            return torch.float32
        return torch.float32

    def _model_device(self, model: Any) -> Any:
        try:
            return next(model.parameters()).device
        except StopIteration:  # pragma: no cover
            return self._torch.device(self.device)

    def _local_files_only(self) -> bool:
        if os.getenv("SERVICEOPS_LOCAL_FILES_ONLY") == "1":
            return True
        return Path(self.base_model_path_or_id).expanduser().exists()

    @staticmethod
    def _looks_like_local_path(value: str) -> bool:
        return value.startswith((".", "/", "~", "models/")) or Path(value).exists()


def build_local_lora_runtime_from_env() -> LocalLoRAJsonModel:
    return LocalLoRAJsonModel(
        base_model_path_or_id=os.getenv("LOCAL_BASE_MODEL_PATH", "models/Qwen2.5-3B-Instruct"),
        router_adapter_path=os.getenv("ROUTER_ADAPTER_PATH", "outputs/router-lora-v1"),
        verifier_adapter_path=os.getenv("VERIFIER_ADAPTER_PATH", "outputs/verifier-lora-v1"),
        device=os.getenv("LOCAL_LORA_DEVICE", "auto"),
        torch_dtype=os.getenv("LOCAL_LORA_TORCH_DTYPE", "auto"),
        max_new_tokens=int(os.getenv("LOCAL_LORA_MAX_NEW_TOKENS", "256")),
    )
