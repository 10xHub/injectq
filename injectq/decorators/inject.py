"""Inject decorator for automatic dependency injection."""

import functools
import inspect
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast

from injectq.core import InjectQ
from injectq.utils import (
    DependencyNotFoundError,
    InjectionError,
    get_function_dependencies,
)


F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def inject(func: F) -> F:
    """Decorator for automatic dependency injection.

    Analyzes function signature and automatically injects dependencies
    based on type hints.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with dependency injection

    Raises:
        InjectionError: If dependency injection fails
    """
    if not callable(func):
        msg = "@inject can only be applied to callable objects"
        raise InjectionError(msg)

    # Check if it's a function (not a class)
    if inspect.isclass(func):
        msg = "@inject can only be applied to functions, not classes"
        raise InjectionError(msg)

    # Analyze function dependencies
    try:
        dependencies = get_function_dependencies(func)
    except Exception as e:
        msg = f"Failed to analyze dependencies for {func.__name__}: {e}"
        raise InjectionError(msg)

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the container at call time (not decoration time)
            container = InjectQ.get_instance()
            return await _inject_and_call(func, dependencies, container, args, kwargs)

        return cast("F", async_wrapper)

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get the container at call time (not decoration time)
        container = InjectQ.get_instance()
        return _inject_and_call(func, dependencies, container, args, kwargs)

    return cast("F", sync_wrapper)


def _inject_and_call(
    func: Callable[..., Any],
    dependencies: dict[str, type],
    container: InjectQ,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """Helper function to inject dependencies and call the function."""
    try:
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)

        # Inject missing dependencies
        for param_name, param_type in dependencies.items():
            if param_name not in bound_args.arguments:
                try:
                    # If an explicit Inject(...) marker is provided as default, honor it
                    param = sig.parameters.get(param_name)
                    if param and isinstance(param.default, Inject):
                        dependency = container.get(param.default.service_type)
                        bound_args.arguments[param_name] = dependency
                        continue
                    # First try to resolve by parameter name (string key)
                    if container.has(param_name):
                        dependency = container.get(param_name)
                    else:
                        # Fall back to type-based resolution
                        dependency = container.get(param_type)
                    bound_args.arguments[param_name] = dependency
                except DependencyNotFoundError:
                    # Check if parameter has a default value
                    param = sig.parameters.get(param_name)
                    if param and param.default is not inspect.Parameter.empty:
                        # Skip parameters with default values
                        continue
                    # Re-raise if no default value
                    raise

        # Apply defaults for remaining parameters
        bound_args.apply_defaults()

        # Call the function
        return func(*bound_args.args, **bound_args.kwargs)

    except Exception as e:
        if isinstance(e, DependencyNotFoundError):
            msg = (
                f"Cannot inject dependency '{e.dependency_type}' for parameter "
                f"in function '{func.__name__}': {e}"
            )
            raise InjectionError(msg)
        if isinstance(e, InjectionError):
            raise
        msg = f"Injection failed for {func.__name__}: {e}"
        raise InjectionError(msg)


class Inject(Generic[T]):
    """Explicit dependency injection marker.

    Used as default parameter value to explicitly mark dependencies:

    def my_function(service=Inject(UserService)):
        # service will be injected
        pass
    """

    def __init__(self, service_type: type) -> None:
        self.service_type = service_type
        self._injected_value: T | None = None
        self._injected = False

    def __repr__(self) -> str:
        return f"Inject({self.service_type})"

    def __getattr__(self, name: str) -> Any:
        if not self._injected:
            container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        if self._injected_value is not None:
            return getattr(self._injected_value, name)
        msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
        raise AttributeError(msg)

    def __call__(self) -> T:
        """Allow Inject to be called to get the injected value."""
        if not self._injected:
            container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return self._injected_value  # type: ignore

    def __bool__(self) -> bool:
        """Make Inject truthy when injected."""
        return self._injected

    def __eq__(self, other: object) -> bool:
        """Compare with injected value."""
        if not self._injected:
            container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return self._injected_value == other

    def __hash__(self) -> int:
        """Hash based on injected value."""
        if not self._injected:
            container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return hash(self._injected_value)

    @classmethod
    def __class_getitem__(cls, item: type | tuple) -> "Inject":
        """Support generic syntax Inject[ServiceType]."""
        if isinstance(item, type):
            return cls(item)
        return super().__class_getitem__(item)  # type: ignore


def inject_into(container: InjectQ) -> Callable[[F], F]:
    """Create an inject decorator that uses a specific container.

    Args:
        container: The container to use for dependency resolution

    Returns:
        Inject decorator bound to the specified container
    """

    def decorator(func: F) -> F:
        if not callable(func):
            msg = "@inject can only be applied to callable objects"
            raise InjectionError(msg)

        # Analyze function dependencies
        try:
            dependencies = get_function_dependencies(func)
        except Exception as e:
            msg = f"Failed to analyze dependencies for {func.__name__}: {e}"
            raise InjectionError(msg)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await _inject_and_call(
                    func, dependencies, container, args, kwargs
                )

            return cast("F", async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _inject_and_call(func, dependencies, container, args, kwargs)

        return cast("F", sync_wrapper)

    return decorator
