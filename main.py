from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag import RAGPipeline

app = FastAPI(title="RAG API", version="1.0.0")
rag: RAGPipeline | None = None


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    contexts: list[str]


def get_rag() -> RAGPipeline:
    global rag
    if rag is None:
        rag = RAGPipeline()
    return rag


@app.get("/")
def root():
    return {"service": "rag-api", "status": "up"}


@app.get("/health")
def health():
    return {"status": "ok", "rag_initialized": rag is not None}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    try:
        result = get_rag().generate(payload.query)
        return AskResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
