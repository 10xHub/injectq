"""Custom exceptions for InjectQ dependency injection library."""

from typing import Any


class InjectQError(Exception):
    """Base exception for all InjectQ errors."""


class DependencyNotFoundError(InjectQError):
    """Raised when a dependency cannot be found in the container."""

    def __init__(self, dependency_type: type[Any]) -> None:
        self.dependency_type = dependency_type
        super().__init__(f"No binding found for type: {dependency_type}")


class CircularDependencyError(InjectQError):
    """Raised when a circular dependency is detected."""

    def __init__(self, dependency_chain: list[type[Any]]) -> None:
        self.dependency_chain = dependency_chain
        chain_str = " -> ".join(str(dep) for dep in dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


class BindingError(InjectQError):
    """Raised when there's an error in service binding configuration."""


class InjectionError(InjectQError):
    """Raised when dependency injection fails."""


class ScopeError(InjectQError):
    """Raised when there's an error with scope management."""


class AlreadyRegisteredError(InjectQError):
    """Raised when trying to register a type that is already registered."""

    def __init__(self, dependency_type: Any) -> None:
        self.dependency_type = dependency_type
        super().__init__(f"Type already registered: {dependency_type}")
