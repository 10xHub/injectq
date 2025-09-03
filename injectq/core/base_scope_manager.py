"""Base scope manager interface for InjectQ dependency injection library."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Union


class BaseScopeManager(ABC):
    """Abstract base class for scope managers."""

    @abstractmethod
    def register_scope(self, scope: Any) -> None:
        """Register a new scope."""
        pass

    @abstractmethod
    def get_scope(self, scope_name: str) -> Any:
        """Get a scope by name."""
        pass

    @abstractmethod
    def resolve_scope_name(self, scope: Any) -> str:
        """Resolve scope name from various input types."""
        pass

    @abstractmethod
    def scope_context(self, scope_name: Union[str, Any]) -> Any:
        """Context manager for entering/exiting a scope."""
        pass

    @abstractmethod
    def get_instance(
        self, key: Any, factory: Callable[[], Any], scope_name: str = "singleton"
    ) -> Any:
        """Get an instance from the specified scope."""
        pass

    @abstractmethod
    def clear_scope(self, scope_name: Union[str, Any]) -> None:
        """Clear all instances in a scope."""
        pass

    @abstractmethod
    def clear_all_scopes(self) -> None:
        """Clear all instances in all scopes."""
        pass
