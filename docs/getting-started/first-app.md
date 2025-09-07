# Your First App

Let's build a complete application with InjectQ! We'll create a simple user management system that demonstrates real-world patterns.

## 🎯 Application Overview

We'll build a user management API with:

- User repository for data access
- User service for business logic
- Configuration management
- Dependency injection throughout
- Proper error handling

## 📁 Project Structure

```
my_injectq_app/
├── main.py              # Application entry point
├── config.py            # Configuration classes
├── database.py          # Database layer
├── repository.py        # Data access layer
├── service.py           # Business logic layer
└── models.py            # Data models
```

## 🏗️ Step 1: Define Data Models

```python
# models.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    id: Optional[int]
    username: str
    email: str
    created_at: datetime
    is_active: bool = True

@dataclass
class CreateUserRequest:
    username: str
    email: str

@dataclass
class UpdateUserRequest:
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
```

## ⚙️ Step 2: Configuration

```python
# config.py
from injectq import singleton

@singleton
class DatabaseConfig:
    def __init__(self):
        self.host = "localhost"
        self.port = 5432
        self.database = "userdb"
        self.user = "postgres"
        self.password = "password"

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

@singleton
class AppConfig:
    def __init__(self):
        self.app_name = "User Management API"
        self.version = "1.0.0"
        self.debug = True
```

## 🗄️ Step 3: Database Layer

```python
# database.py
from typing import List, Optional
from injectq import singleton
import asyncio

from .config import DatabaseConfig
from .models import User

@singleton
class Database:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._users = {}  # In-memory storage for demo
        self._next_id = 1
        print(f"Database initialized with config: {config.connection_string}")

    async def create_user(self, user: User) -> User:
        """Create a new user."""
        user.id = self._next_id
        self._users[user.id] = user
        self._next_id += 1
        return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    async def get_all_users(self) -> List[User]:
        """Get all users."""
        return list(self._users.values())

    async def update_user(self, user_id: int, updates: dict) -> Optional[User]:
        """Update user."""
        user = self._users.get(user_id)
        if not user:
            return None

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        return user

    async def delete_user(self, user_id: int) -> bool:
        """Delete user."""
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False
```

## 📊 Step 4: Repository Layer

```python
# repository.py
from typing import List, Optional
from injectq import singleton

from .database import Database
from .models import User, CreateUserRequest, UpdateUserRequest

@singleton
class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, request: CreateUserRequest) -> User:
        """Create a new user."""
        from datetime import datetime
        user = User(
            id=None,
            username=request.username,
            email=request.email,
            created_at=datetime.now(),
            is_active=True
        )
        return await self.db.create_user(user)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.db.get_user(user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.db.get_user_by_username(username)

    async def get_all(self) -> List[User]:
        """Get all users."""
        return await self.db.get_all_users()

    async def update(self, user_id: int, request: UpdateUserRequest) -> Optional[User]:
        """Update user."""
        updates = {}
        if request.username is not None:
            updates["username"] = request.username
        if request.email is not None:
            updates["email"] = request.email
        if request.is_active is not None:
            updates["is_active"] = request.is_active

        return await self.db.update_user(user_id, updates)

    async def delete(self, user_id: int) -> bool:
        """Delete user."""
        return await self.db.delete_user(user_id)
```

## 🔧 Step 5: Service Layer

```python
# service.py
from typing import List, Optional
from injectq import singleton

from .repository import UserRepository
from .models import User, CreateUserRequest, UpdateUserRequest

@singleton
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def create_user(self, request: CreateUserRequest) -> User:
        """Create a new user with validation."""
        # Check if username already exists
        existing = await self.repo.get_by_username(request.username)
        if existing:
            raise ValueError(f"Username '{request.username}' already exists")

        # Check if email already exists
        # In a real app, you'd check this too
        return await self.repo.create(request)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.repo.get_by_id(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.repo.get_by_username(username)

    async def get_all_users(self) -> List[User]:
        """Get all users."""
        return await self.repo.get_all()

    async def update_user(self, user_id: int, request: UpdateUserRequest) -> Optional[User]:
        """Update user with validation."""
        # Check if user exists
        existing = await self.repo.get_by_id(user_id)
        if not existing:
            return None

        # Check username uniqueness if being updated
        if request.username and request.username != existing.username:
            duplicate = await self.repo.get_by_username(request.username)
            if duplicate:
                raise ValueError(f"Username '{request.username}' already exists")

        return await self.repo.update(user_id, request)

    async def delete_user(self, user_id: int) -> bool:
        """Delete user."""
        return await self.repo.delete(user_id)

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate user."""
        return await self.update_user(user_id, UpdateUserRequest(is_active=False))

    async def activate_user(self, user_id: int) -> Optional[User]:
        """Activate user."""
        return await self.update_user(user_id, UpdateUserRequest(is_active=True))
```

## 🚀 Step 6: Application Entry Point

```python
# main.py
import asyncio
from injectq import InjectQ, inject

from .config import DatabaseConfig, AppConfig
from .database import Database
from .repository import UserRepository
from .service import UserService
from .models import CreateUserRequest, UpdateUserRequest

async def setup_container() -> None:
    """Set up the dependency injection container using the public convenience container."""
    from injectq import InjectQ

    # use the global convenience container directly
    container = InjectQ.get_instance()

    # Bind configurations
    container[DatabaseConfig] = DatabaseConfig
    container[AppConfig] = AppConfig

    # Bind services (automatically resolved)
    container[Database] = Database
    container[UserRepository] = UserRepository
    container[UserService] = UserService


@inject
async def demo_user_operations(service: UserService, config: AppConfig):
    """Demonstrate user operations."""
    print(f"🚀 {config.app_name} v{config.version}")
    print("=" * 50)

    # Create users
    print("\n📝 Creating users...")
    user1 = await service.create_user(CreateUserRequest(
        username="john_doe",
        email="john@example.com"
    ))
    print(f"Created user: {user1.username} (ID: {user1.id})")

    user2 = await service.create_user(CreateUserRequest(
        username="jane_smith",
        email="jane@example.com"
    ))
    print(f"Created user: {user2.username} (ID: {user2.id})")

    # Get user
    print("\n🔍 Getting user...")
    retrieved = await service.get_user(user1.id)
    if retrieved:
        print(f"Retrieved user: {retrieved.username}")

    # Update user
    print("\n✏️  Updating user...")
    updated = await service.update_user(user1.id, UpdateUserRequest(
        email="john.doe@example.com"
    ))
    if updated:
        print(f"Updated user email: {updated.email}")

    # List all users
    print("\n📋 All users:")
    users = await service.get_all_users()
    for user in users:
        status = "Active" if user.is_active else "Inactive"
        print(f"  - {user.username} ({user.email}) - {status}")

    # Deactivate user
    print("\n🚫 Deactivating user...")
    deactivated = await service.deactivate_user(user2.id)
    if deactivated:
        print(f"Deactivated user: {deactivated.username}")

    # List users again
    print("\n📋 Users after deactivation:")
    users = await service.get_all_users()
    for user in users:
        status = "Active" if user.is_active else "Inactive"
        print(f"  - {user.username} ({user.email}) - {status}")

async def main():
    """Main application entry point."""
    # Set up container
    await setup_container()

    # Run demo
    await demo_user_operations()

    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🎯 Step 7: Running the Application

Create the files above and run:

```bash
python main.py
```

You should see output like:

```
🚀 User Management API v1.0.0
==================================================

📝 Creating users...
Database initialized with config: postgresql://postgres:password@localhost:5432/userdb
Created user: john_doe (ID: 1)
Created user: jane_smith (ID: 2)

🔍 Getting user...
Retrieved user: john_doe

✏️  Updating user...
Updated user email: john.doe@example.com

📋 All users:
  - john_doe (john.doe@example.com) - Active
  - jane_smith (jane@example.com) - Active

🚫 Deactivating user...
Deactivated user: jane_smith

📋 Users after deactivation:
  - john_doe (john.doe@example.com) - Active
  - jane_smith (jane@example.com) - Inactive

✅ Demo completed successfully!
```

## 🔧 Step 8: Adding Error Handling

Let's enhance our application with proper error handling:

```python
# Add to service.py
class UserServiceError(Exception):
    """Base exception for user service errors."""
    pass

class UserNotFoundError(UserServiceError):
    """Raised when a user is not found."""
    pass

class UserAlreadyExistsError(UserServiceError):
    """Raised when trying to create a user that already exists."""
    pass

# Update UserService methods
async def get_user(self, user_id: int) -> User:
    """Get user by ID."""
    user = await self.repo.get_by_id(user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found")
    return user

async def create_user(self, request: CreateUserRequest) -> User:
    """Create a new user with validation."""
    # Check if username already exists
    existing = await self.repo.get_by_username(request.username)
    if existing:
        raise UserAlreadyExistsError(f"Username '{request.username}' already exists")

    return await self.repo.create(request)
```

## 🧪 Step 9: Adding Tests

```python
# tests/test_user_service.py
import pytest
from injectq.testing import test_container, override_dependency

from ..service import UserService
from ..models import CreateUserRequest

class MockRepository:
    def __init__(self):
        self.users = {}

    async def create(self, request):
        # Mock implementation
        pass

    async def get_by_id(self, user_id):
        return self.users.get(user_id)

def test_create_user():
    with test_container() as container:
        # Override repository with mock
        mock_repo = MockRepository()
        container.bind_instance("UserRepository", mock_repo)

        service = container.get(UserService)

        # Test user creation
        request = CreateUserRequest(username="test", email="test@example.com")
        # ... test implementation

def test_get_user_not_found():
    with test_container() as container:
        mock_repo = MockRepository()
        container.bind_instance("UserRepository", mock_repo)

        service = container.get(UserService)

        with pytest.raises(UserNotFoundError):
            await service.get_user(999)
```

## 🚀 What's Next?

Congratulations! You've built a complete application with InjectQ. Here are some next steps:

1. **[Add FastAPI Integration](../integrations/fastapi.md)**: Turn this into a REST API
2. **[Add Database Integration](../examples/advanced-patterns.md)**: Use a real database
3. **[Add Authentication](../examples/real-world-apps.md)**: Secure your API
4. **[Add Testing](../testing/testing-overview.md)**: Write comprehensive tests
5. **[Explore Advanced Features](../advanced/resource-management.md)**: Add caching, logging, etc.

## 💡 Key Takeaways

- **Separation of Concerns**: Each layer has a single responsibility
- **Dependency Injection**: Clean, testable, and maintainable code
- **Type Safety**: Full type hints throughout
- **Async Support**: Modern Python async/await patterns
- **Error Handling**: Proper exception handling and validation
- **Testing**: Easy to test with dependency overrides

Your InjectQ journey has just begun! 🎉
