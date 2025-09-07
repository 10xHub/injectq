# @inject Decorator

The **`@inject` decorator** is InjectQ's most powerful and recommended way to inject dependencies. It automatically resolves and injects dependencies based on type hints, making your code clean and declarative.

## 🎯 Basic Usage

The `@inject` decorator eliminates manual dependency management:

```python
from injectq import InjectQ, inject

container = InjectQ.get_instance()

# Set up container
container[Database] = Database
container[UserService] = UserService

# Use @inject decorator
@inject
def process_user(service: UserService, db: Database) -> None:
    # Dependencies automatically injected
    user = service.get_user(1)
    db.save(user)

# Call without parameters - dependencies injected automatically
process_user()
```

## 🏗️ How It Works

### Automatic Resolution

The `@inject` decorator analyzes function signatures and resolves dependencies:

```python
@inject
def create_report(
    user_service: UserService,
    analytics: AnalyticsService,
    cache: Cache,
    config: AppConfig
) -> Report:
    # InjectQ automatically:
    # 1. Gets UserService from container
    # 2. Gets AnalyticsService from container
    # 3. Gets Cache from container
    # 4. Gets AppConfig from container
    # 5. Calls the function with all dependencies
    pass
```

### Type-Based Resolution

Dependencies are resolved based on type hints:

```python
from injectq import InjectQ

container = InjectQ.get_instance()

class IUserRepository(Protocol):
    def get_by_id(self, id: int) -> Optional[User]: ...

class UserRepository:
    def get_by_id(self, id: int) -> Optional[User]:
        # Implementation
        pass

# Register implementation
container.bind(IUserRepository, UserRepository)

@inject
def get_user(repo: IUserRepository) -> Optional[User]:
    # InjectQ finds UserRepository for IUserRepository
    return repo.get_by_id(1)
```

## 🎨 Advanced Patterns

### Async Functions

Works seamlessly with async functions:

```python
@inject
async def process_user_async(service: UserService, user_id: int) -> User:
    # All dependencies injected
    user = await service.get_user_async(user_id)
    return user

# Usage
result = await process_user_async(user_id=123)
```

### Class Methods

Can be used on class methods:

```python
class UserController:
    @inject
    def get_user(self, service: UserService, user_id: int) -> User:
        # 'self' is not injected, other parameters are
        return service.get_user(user_id)

    @classmethod
    @inject
    def create_user(cls, service: UserService, data: dict) -> User:
        # 'cls' is not injected
        return service.create_user(data)
```

### Static Methods

Works with static methods:

```python
class UserUtils:
    @staticmethod
    @inject
    def validate_user(service: UserService, user_id: int) -> bool:
        user = service.get_user(user_id)
        return user is not None and user.is_active
```

### Nested Injection

Dependencies can have their own dependencies:

```python
class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config

class UserRepository:
    def __init__(self, db: Database):
        self.db = db

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

# Register only the top-level service
container[UserService] = UserService

@inject
def use_service(service: UserService) -> None:
    # InjectQ automatically creates:
    # 1. DatabaseConfig
    # 2. Database (with DatabaseConfig)
    # 3. UserRepository (with Database)
    # 4. UserService (with UserRepository)
    pass
```

## 🔧 Integration Patterns

### With FastAPI

```python
from fastapi import FastAPI
from injectq.integrations.fastapi import Injected

app = FastAPI()

@app.get("/users/{user_id}")
@inject
def get_user(user_id: int, service: UserService) -> User:
    return service.get_user(user_id)

# Or using Injected type
@app.get("/users/{user_id}")
def get_user(user_id: int, service: Injected[UserService]) -> User:
    return service.get_user(user_id)
```

### With Classes

Use `@inject` on `__init__` methods:

```python
class UserController:
    @inject
    def __init__(self, service: UserService, logger: Logger):
        self.service = service
        self.logger = logger

    def get_user(self, user_id: int) -> User:
        self.logger.info(f"Getting user {user_id}")
        return self.service.get_user(user_id)

# Usage
controller = UserController()  # Dependencies automatically injected
```

### With Context Managers

```python
class DatabaseTransaction:
    @inject
    def __init__(self, db: Database):
        self.db = db

    def __enter__(self):
        self.db.begin_transaction()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()

@inject
def process_with_transaction(service: UserService) -> None:
    with DatabaseTransaction() as tx:
        # Transaction automatically injected
        service.update_user(1, {"name": "New Name"})
```

## 🧪 Testing with @inject

### Mock Dependencies

```python
from injectq import InjectQ
from injectq.testing import override_dependency

def test_user_service():
    mock_service = MockUserService()

    with override_dependency(UserService, mock_service):
        # @inject decorated functions use the mock
        result = get_user(user_id=1)
        assert result.name == "Mock User"
```

### Test Containers

```python
from injectq import InjectQ
from injectq.testing import test_container

def test_with_isolation():
    with test_container() as container:
        # Set up test dependencies
        container.bind(UserService, MockUserService)
        container.bind(Database, MockDatabase)

        # Test the function
        result = get_user(user_id=1)
        assert result is not None
```

## 🚨 Error Handling

### Missing Dependencies

```python
@inject
def process_data(service: UserService) -> None:
    pass

# If UserService is not registered
try:
    process_data()
except DependencyNotFoundError as e:
    print(f"Missing dependency: {e}")
```

### Circular Dependencies

```python
class A:
    def __init__(self, b: B):
        self.b = b

class B:
    def __init__(self, a: A):  # Circular!
        self.a = a

container.bind(A, A)
container.bind(B, B)

@inject
def use_a(a: A) -> None:
    pass

# Will raise CircularDependencyError
use_a()
```

## ⚡ Performance Considerations

### Compilation

For better performance in production:

```python
# Pre-compile dependency resolution
container.compile()

# Now @inject functions resolve faster
@inject
def fast_function(service: UserService) -> None:
    pass
```

### Caching

Resolved instances are cached based on scope:

```python
@inject
def use_service(service: UserService) -> None:
    pass

# First call - creates UserService
use_service()

# Second call - reuses cached UserService (if singleton)
use_service()
```

## 🏆 Best Practices

### 1. Use Type Hints

```python
# ✅ Good - explicit type hints
@inject
def process_user(service: UserService, user_id: int) -> User:
    pass

# ❌ Avoid - missing type hints
@inject
def process_user(service, user_id):
    pass
```

### 2. Prefer Protocols

```python
# ✅ Good - depend on abstractions
class IUserService(Protocol):
    def get_user(self, id: int) -> User: ...

@inject
def process_user(service: IUserService) -> None:
    pass

# ❌ Avoid - depend on concrete classes
@inject
def process_user(service: UserService) -> None:
    pass
```

### 3. Keep Functions Focused

```python
# ✅ Good - single responsibility
@inject
def create_user(service: UserService, data: CreateUserRequest) -> User:
    return service.create_user(data)

@inject
def send_welcome_email(email_service: EmailService, user: User) -> None:
    email_service.send_welcome(user)

# ❌ Avoid - multiple responsibilities
@inject
def create_user_and_send_email(
    user_service: UserService,
    email_service: EmailService,
    data: CreateUserRequest
) -> User:
    user = user_service.create_user(data)
    email_service.send_welcome(user)  # Multiple concerns
    return user
```

### 4. Handle Optional Dependencies

```python
# ✅ Good - optional dependencies
@inject
def log_request(logger: Optional[Logger], request: Request) -> None:
    if logger:
        logger.info(f"Request: {request.path}")

# ✅ Good - default values
@inject
def process_data(cache: Optional[Cache] = None) -> None:
    if cache:
        # Use cache
        pass
    else:
        # Cache not available
        pass
```

### 5. Use Descriptive Names

```python
# ✅ Good - descriptive parameter names
@inject
def authenticate_user(
    auth_service: AuthenticationService,
    user_credentials: UserCredentials
) -> AuthResult:
    pass

# ❌ Avoid - unclear names
@inject
def auth(s: AuthenticationService, c: UserCredentials) -> AuthResult:
    pass
```

## 🔄 Comparison with Other Patterns

### @inject vs Dict Interface

```python
# Dict interface - manual resolution
def process_user(user_id: int) -> User:
    service = container[UserService]
    return service.get_user(user_id)

# @inject - automatic resolution
@inject
def process_user(service: UserService, user_id: int) -> User:
    return service.get_user(user_id)
```

### @inject vs Inject() Function

```python
# Inject() function - explicit injection
def process_user(user_id: int, service=Inject(UserService)) -> User:
    return service.get_user(user_id)

# @inject - implicit injection
@inject
def process_user(service: UserService, user_id: int) -> User:
    return service.get_user(user_id)
```

## 🎯 When to Use @inject

### ✅ Ideal For

- **Most applications** - Recommended default approach
- **Complex dependency graphs** - Automatic resolution
- **Type safety** - Full mypy support
- **Clean code** - Declarative dependency specification
- **Testing** - Easy to mock and override

### ⚠️ Considerations

- **Performance** - Slight overhead for resolution (can be optimized)
- **Debugging** - Dependencies not visible in function calls
- **Learning curve** - Need to understand type hints

## 🎉 Summary

The `@inject` decorator provides:

- **Automatic dependency resolution** - No manual wiring
- **Type-based injection** - Uses type hints for resolution
- **Clean syntax** - Declarative and readable
- **Full type safety** - Works with mypy and IDEs
- **Async support** - Works with async functions
- **Testing friendly** - Easy to override dependencies

**Key benefits:**
- Eliminates boilerplate dependency management
- Makes dependencies explicit through type hints
- Enables easy testing with dependency overrides
- Works seamlessly with all InjectQ features
- Provides excellent IDE support and autocomplete

Ready to explore the [Inject() function](inject-function.md)?
