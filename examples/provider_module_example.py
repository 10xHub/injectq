"""
Simple Provider Module Example

This example demonstrates how to use the @provider decorator
and ProviderModule to organize complex dependency creation.
"""

from injectq import InjectQ
from injectq.modules import ProviderModule, provider


# === Simple Domain Models ===


class Config:
    """Application configuration."""

    def __init__(self, api_url: str, timeout: int) -> None:
        self.api_url = api_url
        self.timeout = timeout


class ApiClient:
    """API client that requires configuration."""

    def __init__(self, config: Config) -> None:
        self.config = config
        print(f"✅ API Client initialized: {config.api_url}")

    def call(self, endpoint: str) -> dict:
        return {
            "url": f"{self.config.api_url}/{endpoint}",
            "timeout": self.config.timeout,
            "status": "success",
        }


class Service:
    """Service that depends on the API client."""

    def __init__(self, client: ApiClient, service_name: str) -> None:
        self.client = client
        self.name = service_name
        print(f"✅ Service '{service_name}' initialized")

    def fetch_data(self, resource: str) -> dict:
        result = self.client.call(resource)
        return {"service": self.name, "data": result}


# === Provider Module ===


class AppModule(ProviderModule):
    """
    Application module using providers.

    Provider methods are decorated with @provider and their
    parameters are automatically injected from the container.
    """

    @provider
    def provide_config(self, api_url: str, timeout: int) -> Config:
        """
        Create application configuration.

        The parameters (api_url, timeout) will be injected
        from bindings in the container.
        """
        print("🔧 Creating Config...")
        return Config(api_url=api_url, timeout=timeout)

    @provider
    def provide_api_client(self, config: Config) -> ApiClient:
        """
        Create API client with configuration.

        The config parameter is injected - it's created by
        the provide_config provider above.
        """
        print("🔧 Creating ApiClient...")
        return ApiClient(config=config)

    @provider
    def provide_service(self, client: ApiClient, service_name: str) -> Service:
        """
        Create service with API client.

        Both client and service_name are injected.
        """
        print("🔧 Creating Service...")
        return Service(client=client, service_name=service_name)


# === Usage Example ===


def main():
    print("🚀 Provider Module Example\n")

    # Create container
    container = InjectQ()

    # Bind configuration values
    # These will be injected into provider methods
    container.bind_instance("api_url", "https://api.example.com")
    container.bind_instance("timeout", 30)
    container.bind_instance("service_name", "UserService")

    # Install the provider module
    container.install_module(AppModule())

    print("\n📦 Getting Service from container...\n")

    # Get the service - all providers are called automatically
    # in the right order to satisfy dependencies
    service = container.get(Service)

    print("\n🔍 Using the service...\n")

    # Use the service
    result = service.fetch_data("users/123")
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
