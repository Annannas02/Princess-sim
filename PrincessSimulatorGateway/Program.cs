using Ocelot.DependencyInjection;
using Ocelot.Middleware;
using Ocelot.Provider.Polly;
using StackExchange.Redis;
using Ocelot.Cache;

var builder = WebApplication.CreateBuilder(args);

// Add Ocelot configuration
builder.Configuration.AddJsonFile("ocelot.json", optional: false, reloadOnChange: true);

// Configure Redis connection
var redis = ConnectionMultiplexer.Connect("localhost:6379");
builder.Services.AddSingleton<IConnectionMultiplexer>(redis);

// Register the Redis cache provider with Ocelot
builder.Services.AddSingleton<IOcelotCache<CachedResponse>, RedisCacheProvider>();

// Add Ocelot with Polly for QoS (Quality of Service)
builder.Services.AddOcelot().AddPolly();

var app = builder.Build();

// Enable Ocelot middleware
await app.UseOcelot();

app.Run();
