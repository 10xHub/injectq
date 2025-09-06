"""Inject decorator for automatic dependency injection."""

import functools
import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar, cast, overload

from injectq.core import InjectQ
from injectq.utils import (
    DependencyNotFoundError,
    InjectionError,
    get_function_dependencies,
)


# Import at module level to avoid repeated imports
try:
    from injectq.core.context import ContainerContext
except ImportError:
    # Handle circular import case if needed
    ContainerContext = None


F = TypeVar("F", bound=Callable)
T = TypeVar("T")


def inject(
    func: F | None = None, *, container: InjectQ | None = None
) -> F | Callable[[F], F]:
    """Decorator for automatic dependency injection.

    Analyzes function signature and automatically injects dependencies
    based on type hints.

    Args:
        func: Function to decorate
        container: Optional container to use for dependency resolution.
                  If not provided, uses context or default container.

    Returns:
        Decorated function with dependency injection or decorator factory

    Raises:
        InjectionError: If dependency injection fails

    Examples:
        @inject
        def my_function(service: MyService = Inject[MyService]):
            pass

        @inject(container=my_container)
        def my_function(service: MyService = Inject[MyService]):
            pass
    """

    def _inject_decorator(f: F) -> F:
        if not callable(f):
            msg = "@inject can only be applied to callable objects"
            raise InjectionError(msg)

        # Check if it's a function (not a class)
        if inspect.isclass(f):
            msg = "@inject can only be applied to functions, not classes"
            raise InjectionError(msg)

        # Analyze function dependencies
        try:
            dependencies = get_function_dependencies(f)
        except Exception as e:
            msg = f"Failed to analyze dependencies for {f.__name__}: {e}"
            raise InjectionError(msg) from e

        if inspect.iscoroutinefunction(f):

            @functools.wraps(f)
            async def async_wrapper(*args, **kwargs):
                # Get the container at call time
                target_container = container
                if not target_container:
                    target_container = (
                        ContainerContext.get_current() if ContainerContext else None
                    )
                if not target_container:
                    target_container = InjectQ.get_instance()
                return await _inject_and_call_async(
                    f, dependencies, target_container, args, kwargs
                )

            return cast("F", async_wrapper)

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            # Get the container at call time
            target_container = container
            if not target_container:
                target_container = (
                    ContainerContext.get_current() if ContainerContext else None
                )
            if not target_container:
                target_container = InjectQ.get_instance()
            return _inject_and_call(f, dependencies, target_container, args, kwargs)

        return cast("F", sync_wrapper)

    # If called without arguments, return the decorator
    if func is None:
        return _inject_decorator

    # If called with a function, apply the decorator directly
    return _inject_decorator(func)


async def _inject_and_call_async(
    func: Callable,
    dependencies: dict[str, type],
    container: InjectQ,
    args: tuple,
    kwargs: dict,
):
    """Helper function to inject dependencies and call the async function."""
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
                    if param and isinstance(param.default, Inject | InjectType):
                        dependency = await container.aget(param.default.service_type)
                        bound_args.arguments[param_name] = dependency
                        continue
                    # First try to resolve by parameter name (string key)
                    if container.has(param_name):
                        dependency = await container.aget(param_name)
                    else:
                        # Fall back to type-based resolution
                        dependency = await container.aget(param_type)
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
        return await func(*bound_args.args, **bound_args.kwargs)

    except Exception as e:
        if isinstance(e, DependencyNotFoundError):
            msg = (
                f"Cannot inject dependency '{e.dependency_type}' for parameter "
                f"in function '{func.__name__}': {e}"
            )
            raise InjectionError(msg) from e
        if isinstance(e, InjectionError):
            raise
        msg = f"Injection failed for {func.__name__}: {e}"
        raise InjectionError(msg) from e


def _inject_and_call(
    func: Callable,
    dependencies: dict[str, type],
    container: InjectQ,
    args: tuple,
    kwargs: dict,
):
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
                    if param and isinstance(param.default, Inject | InjectType):
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
            raise InjectionError(msg) from e
        if isinstance(e, InjectionError):
            raise
        msg = f"Injection failed for {func.__name__}: {e}"
        raise InjectionError(msg) from e


if TYPE_CHECKING:
    # Type-only base class that makes InjectType appear as T to type checkers
    class _InjectTypeBase(Generic[T]):
        def __new__(cls, service_type: type[T]) -> T:  # type: ignore[misc]
            # This will never be called at runtime
            return super().__new__(cls)  # type: ignore[return-value]
else:
    _InjectTypeBase = Generic


class InjectType(_InjectTypeBase[T]):
    """Type-safe injection marker for Inject[ServiceType] syntax."""

    def __init__(self, service_type: type[T]) -> None:
        self.service_type = service_type
        self._injected_value: T | None = None
        self._injected = False

    def __repr__(self) -> str:
        return f"Inject[{self.service_type.__name__}]"

    def __getattr__(self, name: str) -> object:
        if not self._injected:
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
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
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
                container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return self._injected_value  # type: ignore[return-value]

    def __bool__(self) -> bool:
        """Make Inject truthy when injected."""
        return self._injected

    def __eq__(self, other: object) -> bool:
        """Compare with injected value."""
        if not self._injected:
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
                container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return self._injected_value == other

    def __hash__(self) -> int:
        """Hash based on injected value."""
        if not self._injected:
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
                container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return hash(self._injected_value)


class _InjectMeta(type):
    """Metaclass for Inject that enables generic syntax."""

    def __getitem__(cls, item: type[T]) -> T:  # type: ignore[misc]
        """Support generic syntax Inject[ServiceType]."""
        if TYPE_CHECKING:
            # For type checking, return the actual type
            return item  # type: ignore[return-value]
        # At runtime, return InjectType instance
        return InjectType(item)  # type: ignore[return-value]


class InjectRequiresServiceTypeError(TypeError):
    """Exception raised when Inject() is called without service_type."""

    def __init__(self) -> None:
        super().__init__("Inject() requires service_type argument")


if TYPE_CHECKING:
    # Type-only base class that makes Inject appear as T to type checkers
    class _InjectBase(Generic[T]):
        def __new__(cls, service_type: type[T] | None = None) -> T:  # type: ignore[misc]
            # This will never be called at runtime
            return super().__new__(cls)  # type: ignore[return-value]
else:
    _InjectBase = Generic


class Inject(_InjectBase[T], metaclass=_InjectMeta):
    """Explicit dependency injection marker.

    Can be used in two ways:
    1. Inject(ServiceType) - traditional syntax
    2. Inject[ServiceType] - generic syntax (recommended for type safety)

    Examples:
        def my_function(service=Inject(UserService)):
            # service will be injected
            pass

        def my_function(service: UserService = Inject[UserService]):
            # service will be injected with proper type checking
            pass
    """

    @overload
    def __init__(self, service_type: type[T]) -> None: ...

    @overload
    def __init__(self) -> None: ...

    def __init__(self, service_type: type[T] | None = None) -> None:
        if service_type is None:
            # This should never happen at runtime, only for type checker satisfaction
            raise InjectRequiresServiceTypeError
        self.service_type = service_type
        self._injected_value: T | None = None
        self._injected = False

    def __repr__(self) -> str:
        return f"Inject({self.service_type})"

    def __getattr__(self, name: str) -> object:
        if not self._injected:
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
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
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
                container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return self._injected_value  # type: ignore[return-value]

    def __bool__(self) -> bool:
        """Make Inject truthy when injected."""
        return self._injected

    def __eq__(self, other: object) -> bool:
        """Compare with injected value."""
        if not self._injected:
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
                container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return self._injected_value == other

    def __hash__(self) -> int:
        """Hash based on injected value."""
        if not self._injected:
            # Get the container at call time, preferring context over singleton
            container = ContainerContext.get_current() if ContainerContext else None
            if not container:
                container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
            self._injected = True
        return hash(self._injected_value)
