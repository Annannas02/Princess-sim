using Ocelot.Cache;
using StackExchange.Redis;
using Newtonsoft.Json;
using System;

public class RedisCacheProvider : IOcelotCache<CachedResponse>
{
    private readonly IConnectionMultiplexer _redis;

    public RedisCacheProvider(IConnectionMultiplexer redis)
    {
        _redis = redis;
    }

    public void Add(string key, CachedResponse value, TimeSpan ttl, string region)
    {
        var database = _redis.GetDatabase();
        var serializedValue = JsonConvert.SerializeObject(value);
        database.StringSet(key, serializedValue, ttl);
    }

    public void AddAndDelete(string key, CachedResponse value, TimeSpan ttl, string region)
    {
        Add(key, value, ttl, region);  // Reuse Add logic
    }

    public CachedResponse Get(string key, string region)
    {
        var database = _redis.GetDatabase();
        var serializedValue = database.StringGet(key);

        if (string.IsNullOrEmpty(serializedValue))
        {
            return null;
        }

        return JsonConvert.DeserializeObject<CachedResponse>(serializedValue);
    }

    public void Remove(string key, string region)
    {
        var database = _redis.GetDatabase();
        database.KeyDelete(key);
    }

    public void ClearRegion(string region)
    {
        // Not implemented, as Redis doesn’t natively support regions
    }
}
