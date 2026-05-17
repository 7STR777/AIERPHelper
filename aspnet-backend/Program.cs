using System.IdentityModel.Tokens.Jwt;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Data.SqlClient;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;

const string NoInfoText = "Нет информации в базе";
const string SupportMessage = "Нет информации в базе. Обратитесь в техподдержку. Запрос сохранен для разбора.";

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("rag", client =>
{
    var baseUrl = builder.Configuration["Rag:BaseUrl"] ?? "http://rag-api:9000";
    var timeoutSeconds = builder.Configuration.GetValue("Rag:TimeoutSeconds", 900);
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(timeoutSeconds);
});

var jwtKey = builder.Configuration["Jwt:Key"] ?? "DEV_SECRET_KEY_CHANGE_ME_1234567890";
var jwtIssuer = builder.Configuration["Jwt:Issuer"] ?? "rag-api";
var jwtAudience = builder.Configuration["Jwt:Audience"] ?? "rag-client";
var jwtExpire = builder.Configuration.GetValue("Jwt:ExpireMinutes", 60);

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwtIssuer,
            ValidAudience = jwtAudience,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
        };
    });

builder.Services.AddAuthorization();

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "RAG API Gateway",
        Version = "v1",
        Description = "JWT: POST /login с login/password, затем Authorize в Swagger (Bearer token)."
    });

    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Name = "Authorization",
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT",
        In = ParameterLocation.Header,
        Description = "JWT из ответа POST /login"
    });

    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

var supportDbConnectionString =
    builder.Configuration.GetConnectionString("SupportDb")
    ?? builder.Configuration["SupportDb:ConnectionString"];

if (!string.IsNullOrWhiteSpace(supportDbConnectionString))
{
    _ = await TryEnsureSupportTableAsync(supportDbConnectionString);
}

var users = new Dictionary<string, (string Password, string Role)>(StringComparer.OrdinalIgnoreCase)
{
    ["user"] = ("user123", "user"),
    ["admin"] = ("admin123", "admin")
};

var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI();

app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/", () => Results.Json(new { service = "aspnet-api", status = "up" }))
    .WithTags("System");

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
})
.WithTags("System");

app.MapPost("/login", (LoginRequest req) =>
{
    if (string.IsNullOrWhiteSpace(req.Login)
        || !users.TryGetValue(req.Login, out var user)
        || user.Password != req.Password)
    {
        return Results.Unauthorized();
    }

    var claims = new[]
    {
        new Claim(ClaimTypes.Name, req.Login),
        new Claim(ClaimTypes.Role, user.Role)
    };

    var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey));
    var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

    var token = new JwtSecurityToken(
        issuer: jwtIssuer,
        audience: jwtAudience,
        claims: claims,
        expires: DateTime.UtcNow.AddMinutes(jwtExpire),
        signingCredentials: creds);

    return Results.Ok(new LoginResponse(new JwtSecurityTokenHandler().WriteToken(token)));
})
.WithTags("Auth");

app.MapPost("/chat", async (
    ChatRequest request,
    HttpContext httpContext,
    IHttpClientFactory httpClientFactory,
    CancellationToken ct) =>
{
    var query = request.Query;
    if (string.IsNullOrWhiteSpace(query))
    {
        query = await ReadQueryAsync(httpContext.Request, ct);
    }

    if (string.IsNullOrWhiteSpace(query))
    {
        return Results.BadRequest(new { error = "query is required. expected JSON: {\"query\":\"...\"}" });
    }

    return await ForwardChatAsync(
        query,
        supportDbConnectionString,
        httpContext,
        httpClientFactory,
        ct);
})
.RequireAuthorization()
.WithTags("Chat")
.Accepts<ChatRequest>("application/json")
.Produces<ChatMessageResponse>(StatusCodes.Status200OK)
.Produces(StatusCodes.Status400BadRequest)
.Produces(StatusCodes.Status401Unauthorized);

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
})
.WithTags("RAG");

app.Run();

static async Task<IResult> ForwardChatAsync(
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
        var response = await client.PostAsync("/ask", content, ct);
        var body = await response.Content.ReadAsStringAsync(ct);

        if (!response.IsSuccessStatusCode)
        {
            return Results.Problem(
                detail: body,
                statusCode: (int)response.StatusCode,
                title: "RAG service error");
        }

        var workerResponse = ParseWorkerResponse(body);
        var messageId = Guid.NewGuid().ToString("N");
        var timestamp = DateTime.UtcNow;

        if (workerResponse is null)
        {
            return Results.Json(new ChatMessageResponse(messageId, body, timestamp));
        }

        if (IsNoInfoAnswer(workerResponse.Answer))
        {
            _ = await TrySaveSupportRequestAsync(
                supportDbConnectionString,
                query,
                "/chat",
                workerResponse.Answer,
                workerResponse.Contexts,
                httpContext,
                ct);

            return Results.Json(new ChatMessageResponse(messageId, SupportMessage, timestamp));
        }

        return Results.Json(new ChatMessageResponse(messageId, workerResponse.Answer, timestamp));
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

internal sealed record LoginRequest(string Login, string Password);

internal sealed record LoginResponse(string Token);

internal sealed record ChatRequest(string Query);

internal sealed record ChatMessageResponse(
    [property: JsonPropertyName("messageID")] string MessageId,
    [property: JsonPropertyName("content")] string Content,
    [property: JsonPropertyName("timestamp")] DateTime Timestamp);

internal sealed record WorkerResponse(string Answer, List<string> Contexts);
