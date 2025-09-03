"""Inject decorator for automatic dependency injection."""

import functools
import inspect
from typing import Any, Callable, TypeVar, cast

from ..core import InjectQ
from ..utils import (
    get_function_dependencies,
    InjectionError,
    DependencyNotFoundError,
)

F = TypeVar("F", bound=Callable[..., Any])


def inject(func: F) -> F:
    """
    Decorator for automatic dependency injection.

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
        raise InjectionError("@inject can only be applied to callable objects")

    # Check if it's a function (not a class)
    if inspect.isclass(func):
        raise InjectionError("@inject can only be applied to functions, not classes")

    # Analyze function dependencies
    try:
        dependencies = get_function_dependencies(func)
    except Exception as e:
        raise InjectionError(f"Failed to analyze dependencies for {func.__name__}: {e}")

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the container at call time (not decoration time)
            container = InjectQ.get_instance()
            return await _inject_and_call(func, dependencies, container, args, kwargs)

        return cast(F, async_wrapper)
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the container at call time (not decoration time)
            container = InjectQ.get_instance()
            return _inject_and_call(func, dependencies, container, args, kwargs)

        return cast(F, sync_wrapper)


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
                    else:
                        # Re-raise if no default value
                        raise

        # Apply defaults for remaining parameters
        bound_args.apply_defaults()

        # Call the function
        return func(*bound_args.args, **bound_args.kwargs)

    except Exception as e:
        if isinstance(e, DependencyNotFoundError):
            raise InjectionError(
                f"Cannot inject dependency '{e.dependency_type}' for parameter "
                f"in function '{func.__name__}': {e}"
            )
        elif isinstance(e, InjectionError):
            raise
        else:
            raise InjectionError(f"Injection failed for {func.__name__}: {e}")


class Inject:
    """
    Explicit dependency injection marker.

    Used as default parameter value to explicitly mark dependencies:

    def my_function(service=Inject(UserService)):
        # service will be injected
        pass
    """

    def __init__(self, service_type: type) -> None:
        """
        Initialize injection marker.

        Args:
            service_type: The type of service to inject
        """
        self.service_type = service_type

    def __repr__(self) -> str:
        return f"Inject({self.service_type})"


def inject_into(container: InjectQ) -> Callable[[F], F]:
    """
    Create an inject decorator that uses a specific container.

    Args:
        container: The container to use for dependency resolution

    Returns:
        Inject decorator bound to the specified container
    """

    def decorator(func: F) -> F:
        if not callable(func):
            raise InjectionError("@inject can only be applied to callable objects")

        # Analyze function dependencies
        try:
            dependencies = get_function_dependencies(func)
        except Exception as e:
            raise InjectionError(
                f"Failed to analyze dependencies for {func.__name__}: {e}"
            )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await _inject_and_call(
                    func, dependencies, container, args, kwargs
                )

            return cast(F, async_wrapper)
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return _inject_and_call(func, dependencies, container, args, kwargs)

            return cast(F, sync_wrapper)

    return decorator
