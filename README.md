# RAG MVP: Python Worker + ASP.NET API + SQL Support Log

## Architecture

- `mssql` (`localhost:1433`) stores unanswered user questions.
- `qdrant` (`localhost:6333`) stores vectors.
- `rag-api` is Python worker (internal only, no public port).
- `aspnet-api` (`localhost:8080`) is the only public backend.

Flow: `Client -> ASP.NET (/rag/ask) -> Python worker -> Qdrant`.

## Run (final release build)

```bash
docker compose -f docker-compose.release.yml up -d --build
```

## Fast dev loop (without rebuild)

After first successful `rag-api` image build (from release file), use dev compose:

```bash
docker compose up -d --force-recreate rag-api aspnet-api
```

Why no rebuild is needed:
- `rag-api` mounts project folder to `/app`
- `aspnet-api` runs `dotnet run` from mounted `./aspnet-backend`
- HuggingFace/SentenceTransformer cache is persisted in `./hf_cache` to avoid repeated long warmup after container recreate

## Model

Default model path:
- `/models/qwen2.5-3b-instruct-q4_k_m.gguf`

Local model folder:
- `D:\ragproject\rag_test\models`

If filename is different, worker auto-selects the best matching `.gguf` from `/models`.

## Re-index vectors (recommended after embedding/retrieval changes)

```bash
docker compose exec -e RECREATE_COLLECTION=true rag-api python3 ingest.py
```

## API (ASP.NET only)

- `GET /health`
- `POST /rag/warmup`
- `POST /rag/ask`

Request example:

```json
{
  "query": "Как открыть список редакций техпроцесса?"
}
```

PowerShell examples (`curl.exe`, not alias):

```powershell
curl.exe -X POST http://localhost:8080/rag/warmup
curl.exe -X POST http://localhost:8080/rag/ask -H "Content-Type: application/json" -d "{\"query\":\"Что такое ДСЕ?\"}"
```

## Unanswered questions in MS SQL

When worker returns "Нет информации в базе", ASP.NET:
1. returns support message to user;
2. writes the question into `dbo.RagSupportRequests`.

Table is auto-created on ASP.NET startup.

Columns:
- `Id` (identity, PK)
- `Question` (nvarchar(2000))
- `Endpoint` (nvarchar(128))
- `WorkerAnswer` (nvarchar(max))
- `ContextsJson` (nvarchar(max))
- `ClientIp` (nvarchar(64))
- `UserAgent` (nvarchar(512))
- `CreatedAtUtc` (datetime2, default `SYSUTCDATETIME()`)

Check saved requests:

```sql
SELECT TOP (100) *
FROM dbo.RagSupportRequests
ORDER BY CreatedAtUtc DESC;
```

## Speed defaults

- `LLM_N_CTX=1536`
- `LLM_MAX_TOKENS=200`
- `LLM_TEMPERATURE=0.1`
- `LLM_REPEAT_PENALTY=1.15`
- `RAG_TOP_K=4`
- `RAG_MAX_CONTEXT_CHARS=2600`

## Quality tuning

Run benchmark and parameter sweep:

```bash
docker compose exec rag-api python3 tune_params.py
```

Results are saved to `tune_results.json` inside the project root.
