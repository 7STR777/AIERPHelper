from llama_cpp import Llama
from config import MISTRAL_MODEL

class MistralLLM:
    def __init__(self):
        self.model = Llama(
            model_path=MISTRAL_MODEL,
            n_gpu_layers=-1,  # всё на GPU если доступна CUDA
            n_ctx=4096,
            verbose=False
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
            echo=False
        )
        return output["choices"][0]["text"]