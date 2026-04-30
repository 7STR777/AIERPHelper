using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Microsoft.Data.SqlClient;

const string NoInfoText = "\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438 \u0432 \u0431\u0430\u0437\u0435";
const string SupportMessage = "\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438 \u0432 \u0431\u0430\u0437\u0435. \u041e\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044c \u0432 \u0442\u0435\u0445\u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443. \u0417\u0430\u043f\u0440\u043e\u0441 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d \u0434\u043b\u044f \u0440\u0430\u0437\u0431\u043e\u0440\u0430.";

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("rag", client =>
{
    var baseUrl = builder.Configuration["Rag:BaseUrl"] ?? "http://rag-api:9000";
    var timeoutSeconds = builder.Configuration.GetValue("Rag:TimeoutSeconds", 900);
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(timeoutSeconds);
});

var supportDbConnectionString =
    builder.Configuration.GetConnectionString("SupportDb")
    ?? builder.Configuration["SupportDb:ConnectionString"];

if (!string.IsNullOrWhiteSpace(supportDbConnectionString))
{
    _ = await TryEnsureSupportTableAsync(supportDbConnectionString);
}

var app = builder.Build();

app.MapGet("/", () => Results.Json(new
{
    service = "aspnet-api",
    status = "up"
}));

app.MapGet("/health", async (IHttpClientFactory httpClientFactory, CancellationToken ct) =>
{
    try
    {
        var client = httpClientFactory.CreateClient("rag");
        var response = await client.GetAsync("/health", ct);
        var body = await response.Content.ReadAsStringAsync(ct);
        return Results.Content(body, "application/json");
    }
    catch (TaskCanceledException)
    {
        return Results.Problem(
            detail: "RAG health check timed out.",
            statusCode: StatusCodes.Status504GatewayTimeout,
            title: "Gateway timeout");
    }
});

app.MapPost("/rag/ask", async (HttpContext httpContext, IHttpClientFactory httpClientFactory, CancellationToken ct) =>
{
    var query = await ReadQueryAsync(httpContext.Request, ct);
    if (string.IsNullOrWhiteSpace(query))
    {
        return Results.BadRequest(new { error = "query is required. expected JSON: {\"query\":\"...\"}" });
    }

    return await ForwardAskAsync(
        endpoint: "/ask",
        query: query,
        supportDbConnectionString: supportDbConnectionString,
        httpContext: httpContext,
        httpClientFactory: httpClientFactory,
        ct: ct);
});

app.MapPost("/rag/warmup", async (IHttpClientFactory httpClientFactory, CancellationToken ct) =>
{
    try
    {
        var client = httpClientFactory.CreateClient("rag");
        using var content = BuildJsonContent(new { });
        var response = await client.PostAsync("/warmup", content, ct);
        var body = await response.Content.ReadAsStringAsync(ct);

        if (!response.IsSuccessStatusCode)
        {
            return Results.Problem(
                detail: body,
                statusCode: (int)response.StatusCode,
                title: "RAG worker error");
        }

        return Results.Content(body, "application/json");
    }
    catch (TaskCanceledException)
    {
        return Results.Problem(
            detail: "RAG warmup timed out.",
            statusCode: StatusCodes.Status504GatewayTimeout,
            title: "Gateway timeout");
    }
});

app.Run();

static async Task<IResult> ForwardAskAsync(
    string endpoint,
    string query,
    string? supportDbConnectionString,
    HttpContext httpContext,
    IHttpClientFactory httpClientFactory,
    CancellationToken ct)
{
    try
    {
        var client = httpClientFactory.CreateClient("rag");
        using var content = BuildJsonContent(new { query });
        var response = await client.PostAsync(endpoint, content, ct);
        var body = await response.Content.ReadAsStringAsync(ct);

        if (!response.IsSuccessStatusCode)
        {
            return Results.Problem(
                detail: body,
                statusCode: (int)response.StatusCode,
                title: "RAG service error");
        }

        var workerResponse = ParseWorkerResponse(body);
        if (workerResponse is null)
        {
            return Results.Content(body, "application/json");
        }

        if (IsNoInfoAnswer(workerResponse.Answer))
        {
            var logged = await TrySaveSupportRequestAsync(
                supportDbConnectionString,
                query,
                endpoint,
                workerResponse.Answer,
                workerResponse.Contexts,
                httpContext,
                ct);

            return Results.Json(new
            {
                answer = SupportMessage,
                contexts = workerResponse.Contexts,
                support_request_logged = logged
            });
        }

        return Results.Json(new
        {
            answer = workerResponse.Answer,
            contexts = workerResponse.Contexts
        });
    }
    catch (TaskCanceledException)
    {
        return Results.Problem(
            detail: "RAG request timed out.",
            statusCode: StatusCodes.Status504GatewayTimeout,
            title: "Gateway timeout");
    }
}

static bool IsNoInfoAnswer(string answer)
{
    if (string.IsNullOrWhiteSpace(answer))
    {
        return true;
    }

    var normalized = answer.Trim().ToLowerInvariant();
    return normalized.Contains("no_info_in_db") || normalized.Contains(NoInfoText.ToLowerInvariant());
}

static WorkerResponse? ParseWorkerResponse(string body)
{
    try
    {
        var parsed = JsonSerializer.Deserialize<WorkerResponse>(body, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        });
        if (parsed is null)
        {
            return null;
        }
        return parsed with { Contexts = parsed.Contexts ?? [] };
    }
    catch
    {
        return null;
    }
}

static async Task<string?> ReadQueryAsync(HttpRequest request, CancellationToken ct)
{
    if (request.Query.TryGetValue("query", out var queryFromQs) && !string.IsNullOrWhiteSpace(queryFromQs))
    {
        return queryFromQs.ToString();
    }

    if (request.ContentLength is null or 0)
    {
        return null;
    }

    try
    {
        var body = await JsonSerializer.DeserializeAsync<JsonElement>(request.Body, cancellationToken: ct);
        if (body.ValueKind == JsonValueKind.Object)
        {
            foreach (var prop in body.EnumerateObject())
            {
                if (string.Equals(prop.Name, "query", StringComparison.OrdinalIgnoreCase) &&
                    prop.Value.ValueKind == JsonValueKind.String)
                {
                    return prop.Value.GetString();
                }
            }
        }
    }
    catch
    {
        return null;
    }

    return null;
}

static StringContent BuildJsonContent(object payload)
{
    var json = JsonSerializer.Serialize(payload);
    var content = new StringContent(json, Encoding.UTF8, "application/json");
    content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
    return content;
}

static async Task EnsureSupportTableAsync(string connectionString)
{
    const string sql = """
IF OBJECT_ID('dbo.RagSupportRequests', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RagSupportRequests (
        Id BIGINT IDENTITY(1,1) PRIMARY KEY,
        Question NVARCHAR(2000) NOT NULL,
        Endpoint NVARCHAR(128) NOT NULL,
        WorkerAnswer NVARCHAR(MAX) NULL,
        ContextsJson NVARCHAR(MAX) NULL,
        ClientIp NVARCHAR(64) NULL,
        UserAgent NVARCHAR(512) NULL,
        CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
""";

    await using var conn = new SqlConnection(connectionString);
    await conn.OpenAsync();
    await using var cmd = new SqlCommand(sql, conn);
    await cmd.ExecuteNonQueryAsync();
}

static async Task<bool> TryEnsureSupportTableAsync(string connectionString)
{
    const int maxAttempts = 20;
    for (var attempt = 1; attempt <= maxAttempts; attempt++)
    {
        try
        {
            await EnsureSupportTableAsync(connectionString);
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[support-db] init attempt {attempt}/{maxAttempts} failed: {ex.Message}");
            await Task.Delay(TimeSpan.FromSeconds(3));
        }
    }

    Console.WriteLine("[support-db] init skipped after retries.");
    return false;
}

static async Task<bool> TrySaveSupportRequestAsync(
    string? connectionString,
    string query,
    string endpoint,
    string workerAnswer,
    List<string> contexts,
    HttpContext httpContext,
    CancellationToken ct)
{
    if (string.IsNullOrWhiteSpace(connectionString))
    {
        return false;
    }

    const string insertSql = """
INSERT INTO dbo.RagSupportRequests
(
    Question,
    Endpoint,
    WorkerAnswer,
    ContextsJson,
    ClientIp,
    UserAgent
)
VALUES
(
    @Question,
    @Endpoint,
    @WorkerAnswer,
    @ContextsJson,
    @ClientIp,
    @UserAgent
);
""";

    try
    {
        await using var conn = new SqlConnection(connectionString);
        await conn.OpenAsync(ct);
        await using var cmd = new SqlCommand(insertSql, conn);
        cmd.Parameters.AddWithValue("@Question", query);
        cmd.Parameters.AddWithValue("@Endpoint", endpoint);
        cmd.Parameters.AddWithValue("@WorkerAnswer", (object?)workerAnswer ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@ContextsJson", JsonSerializer.Serialize(contexts));
        cmd.Parameters.AddWithValue("@ClientIp", (object?)httpContext.Connection.RemoteIpAddress?.ToString() ?? DBNull.Value);
        cmd.Parameters.AddWithValue("@UserAgent", (object?)httpContext.Request.Headers.UserAgent.ToString() ?? DBNull.Value);
        await cmd.ExecuteNonQueryAsync(ct);
        return true;
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[support-db] save failed: {ex.Message}");
        return false;
    }
}

internal sealed record WorkerResponse(string Answer, List<string> Contexts);
