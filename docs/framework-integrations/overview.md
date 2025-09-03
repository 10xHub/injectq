# Framework Integrations

**Framework integrations** enable seamless dependency injection with popular Python frameworks like FastAPI, Taskiq, and FastMCP, providing automatic service resolution and request-scoped dependencies.

## 🎯 What are Framework Integrations?

Framework integrations automatically handle dependency injection within the framework's request/response lifecycle, eliminating manual container management and ensuring proper scope isolation.

```python
from injectq import InjectQ
from injectq.integrations.fastapi import InjectQDependency

# Set up container
container = InjectQ()
container.bind(IUserService, UserService())
container.bind(IOrderService, OrderService())

# FastAPI integration
app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    # user_service is automatically resolved from container
    # Each request gets properly scoped dependencies
    return user_service.get_user(user_id)

@app.post("/orders")
async def create_order(
    order_data: OrderCreate,
    order_service: IOrderService = InjectQDependency(IOrderService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    # Both services are injected automatically
    # Same request scope shared between services
    user = user_service.get_current_user()
    order = order_service.create_order(user.id, order_data)
    return order
```

## 🏗️ Integration Benefits

### ✅ Automatic Resolution

- **No manual container calls** - Services resolved automatically
- **Type hints drive injection** - Just add type hints
- **Framework lifecycle aware** - Proper cleanup and scoping

```python
# Without integration - manual resolution
@app.get("/users/{user_id}")
async def get_user_manual(user_id: int):
    user_service = container.get(IUserService)  # Manual
    return user_service.get_user(user_id)

# With integration - automatic resolution
@app.get("/users/{user_id}")
async def get_user_auto(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)  # Automatic
):
    return user_service.get_user(user_id)
```

### ✅ Request Scoping

- **Automatic scope management** - Per-request service instances
- **Isolation between requests** - No state leakage
- **Resource cleanup** - Automatic disposal at request end

```python
@scoped
class RequestCache:
    def __init__(self):
        self.data = {}

# Each request gets its own cache instance
@app.get("/data")
async def get_data(
    cache: RequestCache = InjectQDependency(RequestCache)
):
    if "data" not in cache.data:
        cache.data["data"] = expensive_operation()
    return cache.data["data"]
```

### ✅ Framework Compatibility

- **Works with existing code** - No framework modifications needed
- **Preserves framework features** - All FastAPI/Taskiq features work
- **Multiple integration support** - Use multiple frameworks together

## 🔧 Integration Types

### FastAPI Integration

**FastAPI integration** provides automatic dependency injection for web endpoints with proper request scoping.

```python
from fastapi import FastAPI
from injectq.integrations.fastapi import InjectQDependency, setup_fastapi_integration

# Set up container
container = InjectQ()
container.bind(IUserService, UserService())
container.bind(IAuthService, AuthService())

# Create FastAPI app with integration
app = FastAPI()
setup_fastapi_integration(app, container)

# Use in endpoints
@app.get("/users/me")
async def get_current_user(
    auth_service: IAuthService = InjectQDependency(IAuthService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    user_id = auth_service.get_current_user_id()
    return user_service.get_user(user_id)

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    user_service: IUserService = InjectQDependency(IUserService)
):
    return user_service.create_user(user_data)
```

### Taskiq Integration

**Taskiq integration** enables dependency injection for background tasks and workers.

```python
from taskiq import TaskiqScheduler
from injectq.integrations.taskiq import setup_taskiq_integration

# Set up container
container = InjectQ()
container.bind(IEmailService, EmailService())
container.bind(IUserService, UserService())

# Create scheduler with integration
scheduler = TaskiqScheduler()
setup_taskiq_integration(scheduler, container)

# Use in tasks
@scheduler.task
async def send_welcome_email(
    user_id: int,
    email_service: IEmailService = InjectQDependency(IEmailService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    user = user_service.get_user(user_id)
    await email_service.send_welcome_email(user.email)

# Schedule task
await scheduler.schedule_task(send_welcome_email, user_id=123)
```

### FastMCP Integration

**FastMCP integration** provides dependency injection for MCP (Model Context Protocol) servers.

```python
from fastmcp import FastMCP
from injectq.integrations.fastmcp import setup_fastmcp_integration

# Set up container
container = InjectQ()
container.bind(IDocumentService, DocumentService())
container.bind(IAIService, AIService())

# Create FastMCP server with integration
mcp = FastMCP("MyAIAssistant")
setup_fastmcp_integration(mcp, container)

# Use in tools
@mcp.tool()
async def analyze_document(
    document_id: str,
    doc_service: IDocumentService = InjectQDependency(IDocumentService),
    ai_service: IAIService = InjectQDependency(IAIService)
):
    document = doc_service.get_document(document_id)
    analysis = await ai_service.analyze_document(document)
    return analysis

# Run server
mcp.run()
```

## 🎨 Integration Patterns

### Middleware Integration

```python
from fastapi import Request
from injectq.integrations.fastapi import get_request_container

# Custom middleware with container access
@app.middleware("http")
async def container_middleware(request: Request, call_next):
    # Get request-scoped container
    container = get_request_container(request)

    # Add request-specific services
    container.bind(IRequestContext, RequestContext(request))

    response = await call_next(request)
    return response

# Use request context in endpoints
@app.get("/data")
async def get_data(
    request: Request,
    ctx: IRequestContext = InjectQDependency(IRequestContext)
):
    # Access request-specific data
    return {"user_agent": ctx.user_agent, "path": ctx.path}
```

### Authentication Integration

```python
from fastapi.security import HTTPBearer
from injectq.integrations.fastapi import InjectQDependency

security = HTTPBearer()

@singleton
class AuthService:
    def get_current_user(self, token: str) -> User:
        # Validate token and return user
        return decode_jwt_token(token)

# Protected endpoint with automatic auth
@app.get("/protected")
async def protected_endpoint(
    credentials = Depends(security),
    auth_service: IAuthService = InjectQDependency(IAuthService),
    user_service: IUserService = InjectQDependency(IUserService)
):
    user = auth_service.get_current_user(credentials.credentials)
    data = user_service.get_user_data(user.id)
    return data
```

### Database Transaction Integration

```python
@scoped
class DatabaseTransaction:
    def __init__(self, db: IDatabaseConnection):
        self.db = db
        self.transaction = db.begin_transaction()

    def commit(self):
        self.transaction.commit()

    def rollback(self):
        self.transaction.rollback()

# Automatic transaction management
@app.post("/orders")
async def create_order(
    order_data: OrderCreate,
    transaction: DatabaseTransaction = InjectQDependency(DatabaseTransaction),
    order_service: IOrderService = InjectQDependency(IOrderService)
):
    try:
        order = order_service.create_order(order_data)
        transaction.commit()
        return order
    except Exception:
        transaction.rollback()
        raise
```

## 🧪 Testing Framework Integrations

### Integration Testing

```python
from fastapi.testclient import TestClient
from injectq.integrations.fastapi import setup_fastapi_integration

def test_fastapi_integration():
    # Create test container
    container = InjectQ()
    container.bind(IUserService, MockUserService())

    # Create test app
    app = FastAPI()
    setup_fastapi_integration(app, container)

    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        return user_service.get_user(user_id)

    # Test with client
    client = TestClient(app)
    response = client.get("/users/123")

    assert response.status_code == 200
    assert response.json()["id"] == 123

def test_request_scoping():
    container = InjectQ()

    @scoped
    class RequestCounter:
        def __init__(self):
            self.count = 0

        def increment(self):
            self.count += 1
            return self.count

    container.bind(RequestCounter, RequestCounter())

    app = FastAPI()
    setup_fastapi_integration(app, container)

    @app.get("/count")
    async def get_count(
        counter: RequestCounter = InjectQDependency(RequestCounter)
    ):
        return {"count": counter.increment()}

    client = TestClient(app)

    # Each request should get its own counter
    response1 = client.get("/count")
    response2 = client.get("/count")

    assert response1.json()["count"] == 1
    assert response2.json()["count"] == 1  # New request, new counter
```

### Mock Integration

```python
def test_with_mocked_services():
    # Create container with mocks
    container = InjectQ()
    container.bind(IUserService, MockUserService())
    container.bind(IEmailService, MockEmailService())

    app = FastAPI()
    setup_fastapi_integration(app, container)

    @app.post("/users")
    async def create_user(
        user_data: UserCreate,
        user_service: IUserService = InjectQDependency(IUserService),
        email_service: IEmailService = InjectQDependency(IEmailService)
    ):
        user = user_service.create_user(user_data)
        email_service.send_welcome_email(user.email)
        return user

    client = TestClient(app)

    # Test endpoint
    response = client.post("/users", json={"name": "Test", "email": "test@example.com"})

    assert response.status_code == 200

    # Verify mocks were called
    mock_user_service = container.get(IUserService)
    mock_email_service = container.get(IEmailService)

    assert len(mock_user_service.created_users) == 1
    assert len(mock_email_service.sent_emails) == 1
```

## 🚨 Integration Considerations

### Scope Management

```python
# ✅ Good: Proper scoping
@scoped
class RequestService:
    def __init__(self):
        self.data = {}

# ❌ Bad: Singleton in request context
@singleton
class RequestService:
    def __init__(self):
        self.data = {}  # Shared across requests!
```

### Error Handling

```python
# ✅ Good: Integration handles errors gracefully
@app.get("/data")
async def get_data(
    service: IService = InjectQDependency(IService)
):
    try:
        return service.get_data()
    except ServiceError:
        raise HTTPException(status_code=500, detail="Service error")

# ❌ Bad: Let integration errors bubble up
@app.get("/data")
async def get_data(
    service: IService = InjectQDependency(IService)
):
    return service.get_data()  # May raise unexpected errors
```

### Performance Considerations

```python
# ✅ Good: Efficient resolution
@transient
class LightweightService:
    def process(self, data):
        return data.upper()

# ❌ Bad: Heavy services per request
@transient
class HeavyService:
    def __init__(self):
        self.model = load_ml_model()  # 500MB model per request!
```

## ⚡ Advanced Integration Features

### Custom Dependency Resolvers

```python
from injectq.integrations.fastapi import InjectQDependencyResolver

class CustomResolver(InjectQDependencyResolver):
    def resolve_dependency(self, dependency_type: Type[T]) -> T:
        # Custom resolution logic
        if dependency_type == ISpecialService:
            return self.create_special_service()

        # Fall back to default
        return super().resolve_dependency(dependency_type)

# Use custom resolver
setup_fastapi_integration(app, container, resolver=CustomResolver())
```

### Integration Plugins

```python
class MetricsIntegration:
    """Integration that adds metrics to all endpoints."""

    def __init__(self, metrics_service: IMetricsService):
        self.metrics = metrics_service

    def setup(self, app: FastAPI):
        @app.middleware("http")
        async def metrics_middleware(request, call_next):
            start_time = time.time()

            response = await call_next(request)

            duration = time.time() - start_time
            self.metrics.record_request(
                method=request.method,
                path=request.url.path,
                duration=duration,
                status=response.status_code
            )

            return response

# Use metrics integration
metrics_integration = MetricsIntegration(metrics_service)
metrics_integration.setup(app)
```

### Multi-Framework Support

```python
# Application using multiple frameworks
container = InjectQ()

# Set up FastAPI
fastapi_app = FastAPI()
setup_fastapi_integration(fastapi_app, container)

# Set up Taskiq
taskiq_scheduler = TaskiqScheduler()
setup_taskiq_integration(taskiq_scheduler, container)

# Set up FastMCP
mcp_server = FastMCP("MyAssistant")
setup_fastmcp_integration(mcp_server, container)

# All frameworks share the same container
# Services are properly scoped per framework context
```

## 🎯 Summary

Framework integrations provide:

- **Automatic dependency resolution** - No manual container calls
- **Request-scoped services** - Proper isolation per request
- **Framework lifecycle integration** - Automatic cleanup
- **Type-driven injection** - Just add type hints
- **Multi-framework support** - Use FastAPI, Taskiq, FastMCP together

**Key benefits:**
- Seamless integration with existing frameworks
- Proper scoping and resource management
- Reduced boilerplate code
- Enhanced testability
- Framework-agnostic service definitions

**Supported frameworks:**
- **FastAPI** - Web API dependency injection
- **Taskiq** - Background task dependency injection
- **FastMCP** - MCP server dependency injection

Ready to explore [FastAPI integration](fastapi-integration.md) in detail?
