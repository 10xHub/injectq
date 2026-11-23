# Your First App

A small user-management app, built in layers (config, database, repository, service), wired together by InjectQ. It runs as a script and has tests.

## Layout

```
my_injectq_app/
├── __init__.py
├── models.py
├── config.py
├── database.py
├── repository.py
├── service.py
└── main.py
tests/
└── test_user_service.py
```

Run everything from the directory that contains `my_injectq_app/`.

## Models

```python
# my_injectq_app/models.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int | None
    username: str
    email: str
    created_at: datetime
    is_active: bool = True
```

## Configuration

```python
# my_injectq_app/config.py
from injectq import singleton


@singleton
class AppConfig:
    def __init__(self) -> None:
        self.app_name = "User Management"
        self.max_users = 100
```

## Database

```python
# my_injectq_app/database.py
from injectq import singleton

from .config import AppConfig
from .models import User


@singleton
class Database:
    """In-memory store standing in for a real database."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._users: dict[int, User] = {}
        self._next_id = 1

    async def save(self, user: User) -> User:
        if len(self._users) >= self.config.max_users:
            raise ValueError("user limit reached")
        user.id = self._next_id
        self._next_id += 1
        self._users[user.id] = user
        return user

    async def find_by_username(self, username: str) -> User | None:
        return next((u for u in self._users.values() if u.username == username), None)

    async def all(self) -> list[User]:
        return list(self._users.values())
```

`Database` asks for an `AppConfig` in its constructor. InjectQ reads the type hint and passes the singleton.

## Repository and service

```python
# my_injectq_app/repository.py
from datetime import datetime

from injectq import singleton

from .database import Database
from .models import User


@singleton
class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, username: str, email: str) -> User:
        user = User(id=None, username=username, email=email, created_at=datetime.now())
        return await self.db.save(user)

    async def get_by_username(self, username: str) -> User | None:
        return await self.db.find_by_username(username)

    async def list_all(self) -> list[User]:
        return await self.db.all()
```

```python
# my_injectq_app/service.py
from injectq import singleton

from .models import User
from .repository import UserRepository


class UserAlreadyExistsError(Exception):
    pass


@singleton
class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def create_user(self, username: str, email: str) -> User:
        if await self.repo.get_by_username(username):
            raise UserAlreadyExistsError(username)
        return await self.repo.create(username, email)

    async def list_users(self) -> list[User]:
        return await self.repo.list_all()
```

No manual bindings are needed. `@singleton` registers each class when its module is imported, and `UserService` -> `UserRepository` -> `Database` -> `AppConfig` is resolved from the constructor type hints.

## Entry point

```python
# my_injectq_app/main.py
import asyncio

from injectq import inject

from .config import AppConfig
from .service import UserAlreadyExistsError, UserService


@inject
async def run(service: UserService, config: AppConfig) -> None:
    print(config.app_name)
    await service.create_user("john_doe", "john@example.com")
    await service.create_user("jane_smith", "jane@example.com")
    try:
        await service.create_user("john_doe", "other@example.com")
    except UserAlreadyExistsError as exc:
        print(f"Rejected duplicate: {exc}")
    for user in await service.list_users():
        print(f"{user.id}: {user.username} <{user.email}>")


if __name__ == "__main__":
    asyncio.run(run())
```

`@inject` works on async functions. Calling `run()` with no arguments resolves `UserService` and `AppConfig` from the global container.

```bash
python -m my_injectq_app.main
```

```
User Management
Rejected duplicate: john_doe
1: john_doe <john@example.com>
2: jane_smith <jane@example.com>
```

## Tests

Replace the repository with a fake inside `isolated_container()`. The container is fresh for the block and the previous one is restored afterwards. `container[UserService] = UserService` binds the class so it is built from the fake repository.

```python
# tests/test_user_service.py
import pytest

from injectq.testing import isolated_container
from my_injectq_app.models import User
from my_injectq_app.repository import UserRepository
from my_injectq_app.service import UserAlreadyExistsError, UserService


class FakeRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def get_by_username(self, username):
        return self.users.get(username)

    async def create(self, username, email):
        user = User(id=len(self.users) + 1, username=username, email=email, created_at=None)
        self.users[username] = user
        return user


@pytest.mark.asyncio
async def test_create_user():
    with isolated_container() as container:
        container[UserRepository] = FakeRepository()
        container[UserService] = UserService
        service = container[UserService]
        user = await service.create_user("test", "test@example.com")
        assert user.username == "test"


@pytest.mark.asyncio
async def test_duplicate_username():
    with isolated_container() as container:
        container[UserRepository] = FakeRepository()
        container[UserService] = UserService
        service = container[UserService]
        await service.create_user("test", "a@example.com")
        with pytest.raises(UserAlreadyExistsError):
            await service.create_user("test", "b@example.com")
```

Run with `pytest` (async tests need `pytest-asyncio`, included in `injectq[dev]`).

## Next steps

- [FastAPI integration](../integrations/fastapi.md): expose the service over HTTP
- [Taskiq integration](../integrations/taskiq.md): run it from background tasks
- [Testing](../testing/overview.md)
- [Modules](../modules/overview.md): group bindings in larger apps
