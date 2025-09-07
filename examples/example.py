"""
Example usage of InjectQ dependency injection library.

This example demonstrates the key features and API styles of InjectQ.
"""

import asyncio
import uuid
from datetime import datetime

from injectq import InjectQ, inject, singleton, transient


# Example 1: Simple dict-like interface
print("=== Example 1: Dict-like Interface ===")
container = InjectQ.get_instance()

# Simple value binding
container[str] = "postgresql://localhost:5432/mydb"
container[int] = 42

print(f"Database URL: {container[str]}")
print(f"Magic number: {container[int]}")

# Example 2: Class-based dependency injection
print("\n=== Example 2: Class Dependencies ===")


class DatabaseConfig:
    def __init__(self, url: str) -> None:
        self.url = url


class Database:
    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        print(f"Database connected to: {config.url}")

    def query(self, sql: str) -> str:
        return f"Query '{sql}' executed on {self.config.url}"


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def find_user(self, user_id: int) -> dict:
        result = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "name": f"User{user_id}", "query": result}


# Bind classes
container.bind(DatabaseConfig, DatabaseConfig)
container.bind(Database, Database)
container.bind(UserRepository, UserRepository)

# Resolve with automatic dependency injection
repo = container.get(UserRepository)
user = repo.find_user(123)
print(f"Found user: {user}")

# Example 3: @inject decorator
print("\n=== Example 3: @inject Decorator ===")


@inject
def get_user_service(repo: UserRepository) -> str:
    user = repo.find_user(456)
    return f"Service found: {user['name']}"


@inject
async def async_user_service(repo: UserRepository) -> str:
    user = repo.find_user(789)
    return f"Async service found: {user['name']}"


# Call functions - dependencies automatically injected
result = get_user_service()  # type: ignore[attr-defined]
print(result)

# Async example
async_result = asyncio.run(async_user_service())  # type: ignore[attr-defined]
print(async_result)

# Example 4: Singleton and Transient scopes
print("\n=== Example 4: Scopes ===")


@singleton
class CacheService:
    def __init__(self) -> None:
        self.data = {}
        self.instance_id = id(self)
        print(f"CacheService created with ID: {self.instance_id}")

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> str:
        return self.data.get(key, "Not found")


@transient
class RequestProcessor:
    def __init__(self, cache: CacheService) -> None:
        self.cache = cache
        self.instance_id = id(self)
        print(f"RequestProcessor created with ID: {self.instance_id}")

    def process(self, request_id: str) -> str:
        self.cache.set(request_id, f"processed_{request_id}")
        return f"Request {request_id} processed"


# Test singleton behavior
cache1 = container.get(CacheService)
cache2 = container.get(CacheService)
print(f"Same cache instance? {cache1 is cache2}")

# Test transient behavior
processor1 = container.get(RequestProcessor)
processor2 = container.get(RequestProcessor)
print(f"Different processor instances? {processor1 is not processor2}")
print(f"Same cache in both processors? {processor1.cache is processor2.cache}")

# Example 5: Factory functions
print("\n=== Example 5: Factory Functions ===")


def create_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:8]}"


def create_timestamp() -> str:
    return datetime.now().isoformat()


# Bind factories
container.factories[str] = create_request_id  # This will override previous str binding
container.bind_factory("timestamp", create_timestamp)

# Each call to factory creates new instance
req_id1 = container.get(str)
req_id2 = container.get(str)
print(f"Request ID 1: {req_id1}")
print(f"Request ID 2: {req_id2}")
print(f"Different IDs? {req_id1 != req_id2}")

timestamp = container.get("timestamp")
print(f"Timestamp: {timestamp}")

print("\n=== InjectQ Example Complete ===")
print("InjectQ provides a flexible, powerful dependency injection system!")
print("- Dict-like interface for simple usage")
print("- @inject decorator for automatic injection")
print("- @singleton/@transient for scope control")
print("- Factory functions for dynamic creation")
print("- Full type safety and mypy compliance")
