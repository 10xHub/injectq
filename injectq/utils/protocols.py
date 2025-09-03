"""Protocol definitions for InjectQ type safety."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable


if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager, AbstractContextManager

    from injectq.core.container import InjectQ


T_co = TypeVar("T_co", covariant=True)
T = TypeVar("T")


@runtime_checkable
class Injectable(Protocol):
    """Protocol for classes that can be injected."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the injectable instance."""
        ...


@runtime_checkable
class Provider(Protocol[T_co]):
    """Protocol for dependency providers."""

    @abstractmethod
    def provide(self, container: InjectQ) -> T_co:
        """Provide an instance of the dependency."""
        ...


@runtime_checkable
class AsyncProvider(Protocol[T_co]):
    """Protocol for async dependency providers."""

    @abstractmethod
    async def provide(self, container: InjectQ) -> T_co:
        """Provide an instance of the dependency asynchronously."""
        ...


@runtime_checkable
class Factory(Protocol[T_co]):
    """Protocol for factory functions."""

    @abstractmethod
    def __call__(self, container: InjectQ) -> T_co:
        """Create an instance using the container."""
        ...


@runtime_checkable
class AsyncFactory(Protocol[T_co]):
    """Protocol for async factory functions."""

    @abstractmethod
    async def __call__(self, container: InjectQ) -> T_co:
        """Create an instance using the container asynchronously."""
        ...


@runtime_checkable
class ResourceProvider(Protocol[T_co]):
    """Protocol for resource providers with lifecycle management."""

    @abstractmethod
    def __call__(self) -> AbstractContextManager[T_co]:
        """Provide a resource with sync context management."""
        ...


@runtime_checkable
class AsyncResourceProvider(Protocol[T_co]):
    """Protocol for async resource providers with lifecycle management."""

    @abstractmethod
    def __call__(self) -> AbstractAsyncContextManager[T_co]:
        """Provide a resource with async context management."""
        ...


@runtime_checkable
class Resolvable(Protocol):
    """Protocol for types that can be resolved by the container."""

    @classmethod
    @abstractmethod
    def __injectq_resolve__(cls, container: InjectQ) -> object:
        """Custom resolution method for the container."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for configurable dependencies."""

    @abstractmethod
    def configure(self, **kwargs: object) -> None:
        """Configure the dependency with the given parameters."""
        ...


@runtime_checkable
class ScopeAware(Protocol):
    """Protocol for scope-aware dependencies."""

    @abstractmethod
    def enter_scope(self, scope_name: str) -> None:
        """Called when entering a scope."""
        ...

    @abstractmethod
    def exit_scope(self, scope_name: str) -> None:
        """Called when exiting a scope."""
        ...


class InjectableFunction(Protocol[T_co]):
    """Protocol for functions that support dependency injection."""

    def __call__(self, *args: object, **kwargs: object) -> T_co:
        """Call the function with injected dependencies."""
        ...

    @property
    def __injectq_dependencies__(self) -> dict[str, type[object]]:
        """Get the dependencies required by this function."""
        ...


class InjectableAsyncFunction(Protocol[T_co]):
    """Protocol for async functions that support dependency injection."""

    async def __call__(self, *args: object, **kwargs: object) -> T_co:
        """Call the async function with injected dependencies."""
        ...

    @property
    def __injectq_dependencies__(self) -> dict[str, type[object]]:
        """Get the dependencies required by this function."""
        ...


# Type aliases for common patterns
InjectableCallable = Callable[..., T] | InjectableFunction[T]
AsyncInjectableCallable = Callable[..., T] | InjectableAsyncFunction[T]
AnyProvider = Provider[T] | AsyncProvider[T]
AnyFactory = Factory[T] | AsyncFactory[T]
AnyResourceProvider = ResourceProvider[T] | AsyncResourceProvider[T]
