from llama_cpp import Llama

from config import LLM_GPU_LAYERS, LLM_N_CTX, MISTRAL_MODEL


class MistralLLM:
    def __init__(self):
        self.model = Llama(
            model_path=MISTRAL_MODEL,
            n_gpu_layers=LLM_GPU_LAYERS,
            n_ctx=LLM_N_CTX,
            verbose=False,
        )

    def generate(self, prompt: str) -> str:
        output = self.model(
            prompt,
            max_tokens=512,
            temperature=0.3,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            stop=["Question:", "Вопрос:", "</s>"],
            echo=False,
        )
        return output["choices"][0]["text"]
