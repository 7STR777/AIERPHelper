from pathlib import Path

from llama_cpp import Llama

from config import (
    LLM_FLASH_ATTN,
    LLM_GPU_LAYERS,
    LLM_MAX_TOKENS,
    LLM_MODEL_PATH,
    LLM_N_BATCH,
    LLM_N_CTX,
    LLM_N_THREADS,
    LLM_N_UBATCH,
    LLM_REPEAT_PENALTY,
    LLM_TEMPERATURE,
    LLM_TOP_K,
    LLM_TOP_P,
    LLM_VERBOSE,
)


def resolve_model_path(model_path: str) -> str:
    direct = Path(model_path)
    if direct.exists():
        return str(direct)

    model_dir = direct.parent if direct.parent.exists() else Path("/models")
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    files = [p for p in model_dir.glob("*.gguf") if p.is_file()]
    if not files:
        raise FileNotFoundError(f"No .gguf files found in {model_dir}")

    # Prefer Qwen 3B instruct quantized files if present.
    ranked = sorted(
        files,
        key=lambda p: (
            "qwen" not in p.name.lower(),
            "3b" not in p.name.lower(),
            "instruct" not in p.name.lower(),
            "q4_k_m" not in p.name.lower(),
            p.name.lower(),
        ),
    )
    return str(ranked[0])


class QwenLLM:
    def __init__(self):
        model_path = resolve_model_path(LLM_MODEL_PATH)
        print(f"[llm] using model: {model_path}")

        self.model = Llama(
            model_path=model_path,
            n_gpu_layers=LLM_GPU_LAYERS,
            n_ctx=LLM_N_CTX,
            n_batch=LLM_N_BATCH,
            n_ubatch=LLM_N_UBATCH,
            n_threads=LLM_N_THREADS,
            offload_kqv=True,
            flash_attn=LLM_FLASH_ATTN,
            verbose=LLM_VERBOSE,
        )

    def generate(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repeat_penalty: float | None = None,
    ) -> str:
        output = self.model(
            prompt,
            max_tokens=max_tokens if max_tokens is not None else LLM_MAX_TOKENS,
            temperature=temperature if temperature is not None else LLM_TEMPERATURE,
            top_p=top_p if top_p is not None else LLM_TOP_P,
            top_k=top_k if top_k is not None else LLM_TOP_K,
            repeat_penalty=repeat_penalty if repeat_penalty is not None else LLM_REPEAT_PENALTY,
            stop=[
                "</s>",
                "<|im_end|>",
                "CONTEXT:",
                "QUESTION:"
            ],
            echo=False,
        )
        return output["choices"][0]["text"]