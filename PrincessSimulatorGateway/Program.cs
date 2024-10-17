using Ocelot.DependencyInjection;
using Ocelot.Middleware;
using Ocelot.Provider.Polly;
using StackExchange.Redis;
using Ocelot.Cache;
using PrincessSimulatorGateway.Services;
using Microsoft.AspNetCore.Server.Kestrel.Core;

var builder = WebApplication.CreateBuilder(args);

// Add Ocelot configuration
builder.Configuration.AddJsonFile("ocelot.json", optional: false, reloadOnChange: true);
// Configure Kestrel to support both HTTP/1.1 (for Ocelot) and HTTP/2 (for gRPC)
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenLocalhost(5080, o => o.Protocols = HttpProtocols.Http1); // HTTP/1.1 for Ocelot
    options.ListenLocalhost(5081, o => o.Protocols = HttpProtocols.Http2); // HTTP/2 for gRPC
});
builder.Services.AddGrpc();
builder.Services.AddGrpcReflection();

// Configure Redis connection
var redis = ConnectionMultiplexer.Connect("localhost:6379");
builder.Services.AddSingleton<IConnectionMultiplexer>(redis);

// Register the Redis cache provider with Ocelot
builder.Services.AddSingleton<IOcelotCache<CachedResponse>, RedisCacheProvider>();

// Add Ocelot with Polly for QoS (Quality of Service)
builder.Services.AddOcelot().AddPolly();

var app = builder.Build();

// gRPC
app.MapGrpcService<ServiceDiscoveryImpl>().RequireHost("localhost:5081");
app.MapGrpcReflectionService().RequireHost("localhost:5081");

// Enable Ocelot middleware
await app.UseOcelot();

app.Run();
