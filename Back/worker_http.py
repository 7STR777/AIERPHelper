import json
import threading
import time
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import (
    LLM_MAX_TOKENS,
    RAG_MAX_CONTEXT_CHARS,
    RAG_TOP_K,
    WORKER_HOST,
    WORKER_PORT,
)
from rag import RAGPipeline

rag: RAGPipeline | None = None
rag_lock = threading.Lock()

def load_chunks():
    path = os.getenv("CHUNKS_PATH", "chunks.json")

    print(f"[chunks] loading from {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # если chunks.json = [{"text":"..."}, ...]
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        chunks = [x["text"] for x in data if "text" in x]

    # если chunks.json = ["text1", "text2"]
    else:
        chunks = data

    print(f"[chunks] loaded: {len(chunks)}")

    return chunks

def get_rag() -> RAGPipeline:
    global rag

    if rag is None:
        chunks = load_chunks()
        rag = RAGPipeline(chunks)

    return rag


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args):
        return

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return {}
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self):
        if self.path == "/":
            self._send_json(200, {"service": "rag-worker", "status": "up"})
            return
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "rag_initialized": rag is not None})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        try:
            payload = self._read_json()
        except Exception as exc:
            self._send_json(400, {"error": f"Invalid JSON: {exc}"})
            return

        if self.path == "/warmup":
            started = time.perf_counter()
            try:
                with rag_lock:
                    get_rag()
                elapsed = time.perf_counter() - started
                self._send_json(200, {"status": "warmed", "seconds": round(elapsed, 3)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if self.path not in {"/ask", "/rag/ask"}:
            self._send_json(404, {"error": "Not found"})
            return

        query = (payload.get("query") or "").strip()
        if not query:
            self._send_json(400, {"error": "query is required"})
            return

        max_tokens = payload.get("max_tokens")
        rag_top_k = payload.get("rag_top_k")
        max_context_chars = payload.get("max_context_chars")
        temperature = payload.get("temperature")
        top_p = payload.get("top_p")
        top_k = payload.get("top_k")
        repeat_penalty = payload.get("repeat_penalty")

        started = time.perf_counter()
        try:
            with rag_lock:
                pipeline = get_rag()
                result = pipeline.generate(query=query)
            elapsed = time.perf_counter() - started
            print(f"[timing] ask_total_seconds={elapsed:.3f}")
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


if __name__ == "__main__":
    print(
        f"[worker] starting on {WORKER_HOST}:{WORKER_PORT} "
        f"(defaults: tokens={LLM_MAX_TOKENS}, k={RAG_TOP_K}, ctx_chars={RAG_MAX_CONTEXT_CHARS})"
    )
    server = ThreadingHTTPServer((WORKER_HOST, WORKER_PORT), Handler)
    server.serve_forever()
