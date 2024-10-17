using System.Threading.Tasks;
using Grpc.Core;
using StackExchange.Redis;
using Newtonsoft.Json;
using PrincessSimulatorGateway.Protos;

namespace PrincessSimulatorGateway.Services
{
    public class ServiceDiscoveryImpl : ServiceDiscoveryService.ServiceDiscoveryServiceBase
    {
        private readonly IConnectionMultiplexer _redis;
        private const string ServiceListKey = "registered_services";

        public ServiceDiscoveryImpl(IConnectionMultiplexer redis)
        {
            _redis = redis;
        }

        public override async Task<RegisterServiceResponse> RegisterService(RegisterServiceRequest request, ServerCallContext context)
        {
            var database = _redis.GetDatabase();
            
            // Convert request to a JSON string
            var serviceInfo = JsonConvert.SerializeObject(new ServiceRegistration
            {
                Name = request.Name,
                Id = request.Id,
                Address = request.Address,
                Port = request.Port,
                Tags = { request.Tags }
            });

            // Add the service info to Redis under ServiceListKey
            await database.SetAddAsync(ServiceListKey, serviceInfo);
            
            return new RegisterServiceResponse
            {
                Success = true,
                Message = "Service registered successfully"
            };
        }

        public override async Task<GetServicesResponse> GetServices(GetServicesRequest request, ServerCallContext context)
        {
            var database = _redis.GetDatabase();
            var services = await database.SetMembersAsync(ServiceListKey);

            var response = new GetServicesResponse();
            foreach (var service in services)
            {
                // Deserialize each service and add to response
                var serviceRegistration = JsonConvert.DeserializeObject<ServiceRegistration>(service);
                response.Services.Add(serviceRegistration);
            }

            return response;
        }

        public override Task<StatusResponse> Status(StatusRequest request, ServerCallContext context)
        {
            return Task.FromResult(new StatusResponse
            {
                Message = "Service Discovery is running"
            });
        }
    }
}
