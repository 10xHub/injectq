"""
Final working example demonstrating InjectQ's core features.

This example showcases the main capabilities of InjectQ:
- Dict-like container interface
- Class dependency injection
- Singleton and transient scopes
- @inject decorator
- Module system
- Testing utilities
"""

import injectq


def main():
    """Demonstrate InjectQ's core features."""
    print("🚀 InjectQ - Modern Python Dependency Injection")
    print("=" * 60)

    # === 1. Basic Container Usage ===
    print("\n📦 1. Basic Container Interface:")
    container = injectq.injectq

    # Dict-like interface for simple values
    container[str] = "postgresql://localhost:5432/myapp"
    container[int] = 8080
    container["app_name"] = "MyApplication"

    print(f"Database URL: {container[str]}")
    print(f"Port: {container[int]}")
    print(f"App Name: {container['app_name']}")

    # === 2. Class Dependency Injection ===
    print("\n🔧 2. Class Dependency Injection:")

    class DatabaseConfig:
        def __init__(self, connection_string: str):
            self.connection_string = connection_string

        def __str__(self):
            return f"DatabaseConfig({self.connection_string})"

    class ApiServer:
        def __init__(self, config: DatabaseConfig, port: int):
            self.config = config
            self.port = port

        def start(self):
            return f"Server starting on port {self.port} with {self.config}"

    # Bind dependencies using parameter names
    container.bind_instance("connection_string", container[str])
    container.bind(DatabaseConfig, DatabaseConfig)
    container.bind(ApiServer, ApiServer)

    # Resolve with automatic dependency injection
    server = container.get(ApiServer)
    print(server.start())

    # === 3. Scope Management ===
    print("\n🎯 3. Scope Management:")

    @injectq.singleton
    class Logger:
        def __init__(self):
            self.logs = []
            self.instance_id = id(self)
            print(f"  Logger singleton created (ID: {self.instance_id})")

        def log(self, message: str):
            self.logs.append(message)
            print(f"  LOG: {message}")

    @injectq.transient
    class RequestHandler:
        def __init__(self, logger: Logger):
            self.logger = logger
            self.handler_id = id(self)

        def handle(self, request: str):
            self.logger.log(f"Handler {self.handler_id} processing: {request}")

    # Test singleton behavior
    logger1 = container.get(Logger)
    logger2 = container.get(Logger)
    print(f"Same logger instance: {logger1 is logger2}")

    # Test transient behavior
    handler1 = container.get(RequestHandler)
    handler2 = container.get(RequestHandler)
    print(f"Different handlers: {handler1 is not handler2}")
    print(f"Same logger in handlers: {handler1.logger is handler2.logger}")

    handler1.handle("GET /users")
    handler2.handle("POST /users")

    # === 4. Function Injection ===
    print("\n💉 4. Function Injection:")

    @injectq.inject
    def process_request(request_type: str, handler: RequestHandler):
        handler.handle(f"Injected {request_type}")
        return f"Processed {request_type} request"

    container["request_type"] = "DELETE /users/123"
    result = process_request()  # type: ignore
    print(f"Result: {result}")

    # === 5. Factory Functions ===
    print("\n🏭 5. Factory Functions:")

    import uuid
    from datetime import datetime

    def create_request_id():
        return f"req_{uuid.uuid4().hex[:8]}"

    def create_timestamp():
        return datetime.now().isoformat()

    container.factories["request_id"] = create_request_id
    container.factories["timestamp"] = create_timestamp

    # Each call creates a new instance
    req_id1 = container.get("request_id")
    req_id2 = container.get("request_id")
    timestamp = container.get("timestamp")

    print(f"Request ID 1: {req_id1}")
    print(f"Request ID 2: {req_id2}")
    print(f"Timestamp: {timestamp}")
    print(f"Different IDs: {req_id1 != req_id2}")

    # === 6. Module System ===
    print("\n📚 6. Module System:")

    class DatabaseModule(injectq.Module):
        def configure(self, binder):
            binder.bind_instance("host", "db.example.com")
            binder.bind_instance("username", "admin")
            binder.bind_instance("password", "secret123")

    config_module = injectq.ConfigurationModule(
        {"debug": True, "max_connections": 100, "timeout": 30}
    )

    # Create container with modules
    module_container = injectq.InjectQ([DatabaseModule(), config_module])

    print(f"Host: {module_container.get('host')}")
    print(f"Debug mode: {module_container.get('debug')}")
    print(f"Max connections: {module_container.get('max_connections')}")

    # === 7. Testing Support ===
    print("\n🧪 7. Testing Support:")

    # Test with isolated container
    with injectq.testing.test_container() as test_cont:
        test_cont.bind_instance(str, "sqlite://test.db")
        test_cont.bind_instance(int, 3000)

        test_config = test_cont.get(DatabaseConfig)
        test_server = test_cont.get(ApiServer)

        print(f"Test config: {test_config}")
        print(f"Test server: {test_server.start()}")

    # === 8. Override for Testing ===
    print("\n🔧 8. Override Testing:")

    class MockLogger:
        def __init__(self):
            self.instance_id = "MOCK"

        def log(self, message: str):
            print(f"  MOCK LOG: {message}")

    with injectq.testing.override_dependency(Logger, MockLogger()):
        mock_handler = container.get(RequestHandler)
        mock_handler.handle("Mock request")
        print(f"Mock logger ID: {mock_handler.logger.instance_id}")

    # === Summary ===
    print("\n🎉 Summary:")
    print("InjectQ provides:")
    print("  ✓ Simple dict-like interface for basic usage")
    print("  ✓ Powerful class dependency injection")
    print("  ✓ Flexible scoping (singleton, transient)")
    print("  ✓ Function injection with @inject decorator")
    print("  ✓ Factory functions for dynamic creation")
    print("  ✓ Module system for organization")
    print("  ✓ Testing utilities and mocking support")
    print("  ✓ Type-safe dependency resolution")
    print("  ✓ Performance optimized with caching")

    print(f"\nContainer has {len(container._registry)} registered services")

    # Validation
    try:
        container.validate()
        print("✅ Container validation passed!")
    except Exception as e:
        print(f"❌ Container validation failed: {e}")


if __name__ == "__main__":
    main()
