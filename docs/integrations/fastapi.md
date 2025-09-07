# FastAPI Integration

**FastAPI integration** provides seamless dependency injection for FastAPI applications, enabling automatic service resolution with proper request scoping and lifecycle management.

## 🎯 Getting Started

### Basic Setup

```python
from fastapi import FastAPI
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi_integration, InjectQDependency

# 1. Create container and bind services
container = InjectQ()
container.bind(IUserService, UserService())
container.bind(IOrderService, OrderService())

# 2. Create FastAPI app
app = FastAPI(title="My API", version="1.0.0")

# 3. Set up integration
setup_fastapi_integration(app, container)

# 4. Use dependency injection in endpoints
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    return user_service.get_user(user_id)

@app.post("/orders")
async def create_order(
    order_data: OrderCreate,
    order_service: IOrderService = InjectQDependency(IOrderService)
):
    return order_service.create_order(order_data)
```

### Service Definitions

```python
from typing import Protocol

# Define service interfaces
class IUserService(Protocol):
    def get_user(self, user_id: int) -> User: ...
    def create_user(self, user_data: UserCreate) -> User: ...

class IOrderService(Protocol):
    def create_order(self, order_data: OrderCreate) -> Order: ...
    def get_order(self, order_id: int) -> Order: ...

# Implement services
class UserService:
    def __init__(self, db: IDatabaseConnection):
        self.db = db

    def get_user(self, user_id: int) -> User:
        return self.db.query(User).filter(id=user_id).first()

    def create_user(self, user_data: UserCreate) -> User:
        user = User(**user_data.dict())
        self.db.add(user)
        self.db.commit()
        return user

class OrderService:
    def __init__(self, db: IDatabaseConnection, user_service: IUserService):
        self.db = db
        self.user_service = user_service

    def create_order(self, order_data: OrderCreate) -> Order:
        # Validate user exists
        user = self.user_service.get_user(order_data.user_id)

        order = Order(**order_data.dict())
        self.db.add(order)
        self.db.commit()
        return order

    def get_order(self, order_id: int) -> Order:
        return self.db.query(Order).filter(id=order_id).first()
```

## 🔧 Advanced Configuration

### Custom Container Setup

```python
from injectq import InjectQ, Module

class ApplicationModule(Module):
    def __init__(self, config: AppConfig):
        self.config = config

    def configure(self, binder):
        # Database
        binder.bind(IDatabaseConnection, create_database_connection(self.config.database))

        # Services
        binder.bind(IUserService, UserService())
        binder.bind(IOrderService, OrderService())

        # External services
        binder.bind(IEmailService, SmtpEmailService(self.config.email))
        binder.bind(IPaymentService, StripePaymentService(self.config.payment))

def create_app(config: AppConfig) -> FastAPI:
    # Create container with modules
    container = InjectQ()
    container.install(ApplicationModule(config))

    # Create FastAPI app
    app = FastAPI(
        title=config.app_name,
        version=config.version,
        debug=config.debug
    )

    # Set up integration
    setup_fastapi_integration(app, container)

    return app

# Usage
config = AppConfig.from_env()
app = create_app(config)
```

### Environment-Specific Setup

```python
def create_container_for_env(env: str) -> InjectQ:
    container = InjectQ()

    if env == "production":
        container.install(ProductionDatabaseModule())
        container.install(RedisCacheModule())
        container.install(SmtpEmailModule())
    elif env == "testing":
        container.install(TestDatabaseModule())
        container.install(InMemoryCacheModule())
        container.install(MockEmailModule())
    else:  # development
        container.install(DevDatabaseModule())
        container.install(InMemoryCacheModule())
        container.install(ConsoleEmailModule())

    return container

def create_app() -> FastAPI:
    env = os.getenv("ENV", "development")
    container = create_container_for_env(env)

    app = FastAPI()
    setup_fastapi_integration(app, container)

    return app
```

## 🎨 Dependency Injection Patterns

### Constructor Injection

```python
# Services with dependencies
@singleton
class DatabaseConnection:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = create_connection(config)

@scoped
class UserService:
    def __init__(self, db: IDatabaseConnection, cache: ICache):
        self.db = db
        self.cache = cache

# Bind in module
class ServiceModule(Module):
    def configure(self, binder):
        binder.bind(DatabaseConfig, DatabaseConfig.from_env())
        binder.bind(IDatabaseConnection, DatabaseConnection())
        binder.bind(ICache, RedisCache())
        binder.bind(IUserService, UserService())

# Use in endpoints
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    return user_service.get_user(user_id)
```

### Request-Scoped Services

```python
@scoped
class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.user_id = None

    def set_user(self, user_id: int):
        self.user_id = user_id
        self.request_time = time.time() - self.start_time

@scoped
class RequestCache:
    def __init__(self):
        self.data = {}

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value):
        self.cache[key] = value

# Automatic request scoping
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    ctx: RequestContext = InjectQDependency(RequestContext),
    cache: RequestCache = InjectQDependency(RequestCache),
    user_service: IUserService = InjectQDependency(IUserService)
):
    ctx.set_user(user_id)  # Context is scoped to this request

    # Cache is also scoped to this request
    cache_key = f"user:{user_id}"
    user = cache.get(cache_key)

    if user is None:
        user = user_service.get_user(user_id)
        cache.set(cache_key, user)

    return user
```

### Authentication Integration

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

security = HTTPBearer()

@singleton
class AuthService:
    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret

    def verify_token(self, token: str) -> User:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return User(id=payload["user_id"], email=payload["email"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: IAuthService = InjectQDependency(IAuthService)
) -> User:
    return auth_service.verify_token(credentials.credentials)

@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: IUserService = InjectQDependency(IUserService)
):
    # current_user is authenticated user from JWT
    # user_service is injected from container
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    return user_service.get_user(user_id)
```

## 🧪 Testing FastAPI Integration

### Unit Testing Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from injectq.integrations.fastapi import setup_fastapi_integration

@pytest.fixture
def test_app():
    # Create test container
    container = InjectQ()
    container.bind(IUserService, MockUserService())
    container.bind(IOrderService, MockOrderService())

    # Create test app
    app = FastAPI()
    setup_fastapi_integration(app, container)

    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        return user_service.get_user(user_id)

    return app

def test_get_user(test_app):
    client = TestClient(test_app)

    response = client.get("/users/123")

    assert response.status_code == 200
    assert response.json()["id"] == 123

def test_request_scoping(test_app):
    client = TestClient(test_app)

    # Each request should be isolated
    response1 = client.get("/users/1")
    response2 = client.get("/users/2")

    # Both should succeed (no state leakage)
    assert response1.status_code == 200
    assert response2.status_code == 200
```

### Integration Testing

```python
@pytest.fixture
def integration_app():
    # Real container with test database
    container = InjectQ()
    container.install(TestDatabaseModule())
    container.install(UserModule())
    container.install(OrderModule())

    app = FastAPI()
    setup_fastapi_integration(app, container)

    @app.post("/users")
    async def create_user(
        user_data: UserCreate,
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        return user_service.create_user(user_data)

    @app.post("/orders")
    async def create_order(
        order_data: OrderCreate,
        order_service: IOrderService = InjectQDependency(IOrderService)
    ):
        return order_service.create_order(order_data)

    return app

def test_user_order_workflow(integration_app):
    client = TestClient(integration_app)

    # Create user
    user_response = client.post("/users", json={
        "name": "Test User",
        "email": "test@example.com"
    })
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    # Create order for user
    order_response = client.post("/orders", json={
        "user_id": user_id,
        "items": [{"product_id": 1, "quantity": 2}]
    })
    assert order_response.status_code == 201

    order = order_response.json()
    assert order["user_id"] == user_id
```

### Mock Testing

```python
class MockUserService:
    def __init__(self):
        self.users = {}
        self.call_count = 0

    def get_user(self, user_id: int):
        self.call_count += 1
        return self.users.get(user_id, {"id": user_id, "name": "Mock User"})

    def create_user(self, user_data):
        user_id = len(self.users) + 1
        user = {"id": user_id, **user_data.dict()}
        self.users[user_id] = user
        return user

def test_with_mocks():
    container = InjectQ()
    mock_user_service = MockUserService()
    container.bind(IUserService, mock_user_service)

    app = FastAPI()
    setup_fastapi_integration(app, container)

    @app.get("/users/{user_id}")
    async def get_user(
        user_id: int,
        user_service: IUserService = InjectQDependency(IUserService)
    ):
        return user_service.get_user(user_id)

    client = TestClient(app)

    # Test endpoint
    response = client.get("/users/123")
    assert response.status_code == 200

    # Verify mock was called
    assert mock_user_service.call_count == 1
```

## 🚨 Common Patterns and Pitfalls

### ✅ Good Patterns

#### 1. Proper Scoping

```python
# ✅ Good: Use scoped for request-specific data
@scoped
class RequestMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.queries = []

    def record_query(self, query: str, duration: float):
        self.queries.append({"query": query, "duration": duration})

# ✅ Good: Use singleton for shared resources
@singleton
class DatabasePool:
    def __init__(self, config: DatabaseConfig):
        self.pool = create_pool(config)

# ✅ Good: Use transient for stateless operations
@transient
class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

#### 2. Error Handling

```python
# ✅ Good: Handle service errors gracefully
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    try:
        return user_service.get_user(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ServiceError:
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### 3. Middleware Integration

```python
# ✅ Good: Use middleware for cross-cutting concerns
from fastapi import Request

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    # Get request-scoped logger if available
    try:
        logger = get_request_container(request).get(ILogger)
        logger.info(f"Request started: {request.method} {request.url}")
    except:
        pass  # Logger not available, continue

    response = await call_next(request)

    duration = time.time() - start_time
    print(f"Request completed in {duration:.2f}s")

    return response
```

### ❌ Bad Patterns

#### 1. Manual Container Access

```python
# ❌ Bad: Manual container access in endpoints
container = InjectQ()  # Global container

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user_service = container.get(IUserService)  # Manual resolution
    return user_service.get_user(user_id)

# ✅ Good: Use dependency injection
@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user_service: IUserService = InjectQDependency(IUserService)
):
    return user_service.get_user(user_id)
```

#### 2. Singleton Abuse

```python
# ❌ Bad: Singleton for request-specific data
@singleton
class CurrentUser:
    def __init__(self):
        self.user = None

    def set_user(self, user):
        self.user = user  # Shared across requests!

# ❌ Bad: Singleton for mutable state
@singleton
class RequestCache:
    def __init__(self):
        self.data = {}  # Shared and accumulates forever!

# ✅ Good: Scoped for request-specific data
@scoped
class CurrentUser:
    def __init__(self):
        self.user = None

@scoped
class RequestCache:
    def __init__(self):
        self.data = {}  # Isolated per request
```

#### 3. Heavy Services per Request

```python
# ❌ Bad: Heavy service per request
@transient
class MLModelService:
    def __init__(self):
        self.model = load_ml_model()  # 2GB model loaded per request!

# ✅ Good: Singleton for heavy resources
@singleton
class MLModelService:
    def __init__(self):
        self.model = load_ml_model()  # Loaded once

    def predict(self, data):
        return self.model.predict(data)
```

## ⚡ Advanced Features

### Custom Dependency Resolver

```python
from injectq.integrations.fastapi import InjectQDependencyResolver

class CustomResolver(InjectQDependencyResolver):
    def resolve_dependency(self, dependency_type: Type[T]) -> T:
        # Custom resolution logic
        if dependency_type == ISpecialService:
            # Create special service with custom logic
            return SpecialServiceImpl(custom_config)

        # Fall back to container resolution
        return super().resolve_dependency(dependency_type)

# Use custom resolver
setup_fastapi_integration(app, container, resolver=CustomResolver())
```

### Request Container Access

```python
from injectq.integrations.fastapi import get_request_container

@app.get("/debug")
async def debug_endpoint(request: Request):
    # Get the request-scoped container
    request_container = get_request_container(request)

    # Access request-scoped services
    ctx = request_container.get(RequestContext)
    cache = request_container.get(RequestCache)

    return {
        "request_id": ctx.request_id,
        "cache_size": len(cache.data),
        "services": list(request_container._bindings.keys())
    }
```

### Background Tasks Integration

```python
from fastapi import BackgroundTasks

@singleton
class BackgroundTaskService:
    def __init__(self, email_service: IEmailService):
        self.email_service = email_service

    async def send_welcome_email(self, user_email: str):
        await self.email_service.send_email(
            to=user_email,
            subject="Welcome!",
            body="Welcome to our platform!"
        )

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    user_service: IUserService = InjectQDependency(IUserService),
    task_service: BackgroundTaskService = InjectQDependency(BackgroundTaskService)
):
    # Create user
    user = user_service.create_user(user_data)

    # Send welcome email in background
    background_tasks.add_task(
        task_service.send_welcome_email,
        user.email
    )

    return user
```

### WebSocket Support

```python
from fastapi import WebSocket

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    ws_service: IWebSocketService = InjectQDependency(IWebSocketService)
):
    await websocket.accept()

    # WebSocket connection gets its own scoped services
    ctx = websocket.scope.get("injectq_container")
    if ctx:
        # Services are scoped to this WebSocket connection
        session_service = ctx.get(ISessionService)
        session_service.set_client_id(client_id)

    while True:
        data = await websocket.receive_text()
        # Handle WebSocket messages with injected services
        response = ws_service.process_message(client_id, data)
        await websocket.send_text(response)
```

## 🎯 Summary

FastAPI integration provides:

- **Automatic dependency injection** - No manual container management
- **Request-scoped services** - Proper isolation per HTTP request
- **Type-driven injection** - Just add type hints to endpoint parameters
- **Framework lifecycle integration** - Automatic cleanup and resource management
- **Testing support** - Easy mocking and test isolation

**Key features:**
- Seamless integration with FastAPI's dependency system
- Support for all InjectQ scopes (singleton, scoped, transient)
- Request-scoped container access
- Custom dependency resolvers
- Background task integration
- WebSocket support

**Best practices:**
- Use scoped services for request-specific data
- Use singleton for shared resources and heavy objects
- Use transient for stateless operations
- Handle errors gracefully in endpoints
- Test thoroughly with mocked dependencies
- Avoid manual container access in endpoints

Ready to explore [Taskiq integration](taskiq-integration.md)?
