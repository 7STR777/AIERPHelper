# RAG API (GPU + Docker + ASP.NET integration)

## 1) Start services

```bash
docker compose up --build
```

RAG API will be available at `http://localhost:8000`.
Qdrant will be available at `http://localhost:6333`.

## 2) Ingest chunks into Qdrant

Run once after startup:

```bash
docker compose exec rag-api python3 ingest.py
```

## 3) API endpoints

- `GET /health`
- `POST /ask`

Request:

```json
{
  "query": "Как создать новую карточку ДСЕ?"
}
```

Response:

```json
{
  "answer": "....",
  "contexts": ["...", "..."]
}
```

## 4) ASP.NET backend example

```csharp
using System.Net.Http.Json;

public sealed class RagClient
{
    private readonly HttpClient _httpClient;

    public RagClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<AskResponse?> AskAsync(string query, CancellationToken ct = default)
    {
        var response = await _httpClient.PostAsJsonAsync("/ask", new AskRequest(query), ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<AskResponse>(cancellationToken: ct);
    }
}

public sealed record AskRequest(string Query);
public sealed record AskResponse(string Answer, List<string> Contexts);
```

`Program.cs`:

```csharp
builder.Services.AddHttpClient<RagClient>(client =>
{
    client.BaseAddress = new Uri("http://localhost:8000");
});
```

## 5) GPU notes

- Requires NVIDIA Container Toolkit on host.
- If GPU is unavailable, set `EMBEDDING_DEVICE=cpu` and `LLM_GPU_LAYERS=0`.
