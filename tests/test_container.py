"""Test basic functionality of InjectQ container."""


import pytest

from injectq import InjectQ, inject, singleton, transient
from injectq.utils import CircularDependencyError, DependencyNotFoundError


class Database:
    """Mock database service."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string


class UserRepository:
    """Mock user repository."""

    def __init__(self, db: Database):
        self.db = db

    def get_user(self, user_id: int) -> str:
        return f"User {user_id} from {self.db.connection_string}"


class UserService:
    """Mock user service."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user_name(self, user_id: int) -> str:
        return self.repo.get_user(user_id)


def test_container_creation():
    """Test basic container creation."""
    container = InjectQ()
    assert container is not None
    assert len(container._registry) == 0


def test_global_container():
    """Test global container singleton."""
    container1 = InjectQ.get_instance()
    container2 = InjectQ.get_instance()
    assert container1 is container2


def test_dict_like_interface():
    """Test container dict-like interface."""
    container = InjectQ()

    # Test setting and getting
    container[str] = "hello"
    assert container[str] == "hello"

    # Test contains
    assert str in container

    # Test deletion
    del container[str]
    assert str not in container


def test_bind_and_resolve():
    """Test basic binding and resolution."""
    container = InjectQ()

    # Bind concrete instance
    db = Database("test://connection")
    container.bind_instance(Database, db)

    # Resolve instance
    resolved_db = container.get(Database)
    assert resolved_db is db


def test_bind_class():
    """Test binding and resolving classes."""
    container = InjectQ()

    # Setup dependencies
    container[str] = "test://connection"
    container.bind(Database, Database)
    container.bind(UserRepository, UserRepository)

    # Resolve with dependencies
    repo = container.get(UserRepository)
    assert isinstance(repo, UserRepository)
    assert isinstance(repo.db, Database)
    assert repo.db.connection_string == "test://connection"


def test_auto_resolution():
    """Test automatic class resolution without explicit binding."""
    container = InjectQ()

    # Only bind the primitive dependency
    container[str] = "test://connection"

    # Auto-resolve should work for classes with injectable constructors
    repo = container.get(UserRepository)
    assert isinstance(repo, UserRepository)
    assert isinstance(repo.db, Database)


def test_inject_decorator():
    """Test @inject decorator functionality."""
    container = InjectQ()

    # Setup dependencies
    container[str] = "test://connection"
    container.bind(UserService, UserService)

    @inject(container=container)
    def process_user(user_id: int, service: UserService) -> str:
        return service.get_user_name(user_id)

    # Call function - dependencies should be injected
    result = process_user(123)  # type: ignore
    assert "User 123" in result
    assert "test://connection" in result


def test_inject_with_args():
    """Test @inject with mixed arguments."""
    container = InjectQ()
    container[str] = "test://connection"
    container.bind(UserService, UserService)

    @inject(container=container)
    def process_user(user_id: int, message: str, service: UserService) -> str:
        return f"{message}: {service.get_user_name(user_id)}"

    # Call with some args provided, some injected
    result = process_user(123, "Result")  # type: ignore
    assert "Result: User 123" in result


def test_singleton_decorator():
    """Test @singleton decorator."""
    container = InjectQ()
    container[str] = "test://connection"

    @singleton
    class SingletonService:
        def __init__(self, db: Database):
            self.db = db

    # Bind to local container for testing
    container.bind(SingletonService, SingletonService, scope="singleton")

    # Multiple resolutions should return same instance
    service1 = container.get(SingletonService)
    service2 = container.get(SingletonService)
    assert service1 is service2


def test_transient_decorator():
    """Test @transient decorator."""
    container = InjectQ()
    container[str] = "test://connection"

    @transient
    class TransientService:
        def __init__(self, db: Database):
            self.db = db

    # Multiple resolutions should return different instances
    service1 = container.get(TransientService)
    service2 = container.get(TransientService)
    assert service1 is not service2
    assert isinstance(service1.db, Database)
    assert isinstance(service2.db, Database)


def test_factory_binding():
    """Test factory function binding."""
    container = InjectQ()

    def create_database() -> Database:
        return Database("factory://connection")

    container.factories[Database] = create_database

    db = container.get(Database)
    assert isinstance(db, Database)
    assert db.connection_string == "factory://connection"


def test_dependency_not_found():
    """Test error when dependency not found."""
    container = InjectQ()

    with pytest.raises(DependencyNotFoundError):
        container.get(Database)


def test_circular_dependency_detection():
    """Test circular dependency detection."""
    container = InjectQ()

    # Define B first
    class B:
        def __init__(self, a):  # No type hint to avoid forward reference
            self.a = a

    class A:
        def __init__(self, b: B):  # B is already defined
            self.b = b

    # Now add the type hint to B
    B.__init__.__annotations__ = {"a": A}

    container.bind(A, A)
    container.bind(B, B)

    with pytest.raises(CircularDependencyError):
        container.get(A)


def test_scope_management():
    """Test scope management functionality."""
    container = InjectQ()
    container[str] = "test://connection"

    container.bind(Database, Database, scope="singleton")
    container.bind(UserRepository, UserRepository, scope="transient")

    # Singleton should return same instance
    db1 = container.get(Database)
    db2 = container.get(Database)
    assert db1 is db2

    # Transient should return different instances
    repo1 = container.get(UserRepository)
    repo2 = container.get(UserRepository)
    assert repo1 is not repo2


def test_container_override():
    """Test container override functionality for testing."""
    container = InjectQ()
    container[str] = "original"

    with container.override(str, "overridden"):
        assert container.get(str) == "overridden"

    # Should be restored after context
    assert container.get(str) == "original"


def test_container_validation():
    """Test container validation."""
    container = InjectQ()

    # Valid setup
    container[str] = "test"
    container.bind(Database, Database)

    # Should not raise
    container.validate()

    # Invalid setup - missing dependency
    container.clear()
    container.bind(Database, Database)  # Missing str dependency

    with pytest.raises(Exception):  # Should fail validation
        container.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
