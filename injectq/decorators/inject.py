import functools
import inspect
from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast, overload

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
    ContainerContext = None


F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


@overload
def inject(func: F) -> F: ...


@overload
def inject(*, container: "InjectQ") -> Callable[[F], F]: ...


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
                    if param and isinstance(param.default, Inject):
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
            raise InjectionError(msg) from e
        if isinstance(e, InjectionError):
            raise
        msg = f"Injection failed for {func.__name__}: {e}"
        raise InjectionError(msg) from e


class _InjectMeta(type):
    """Metaclass to enable the `Inject[ServiceType]` syntax."""

    def __getitem__(cls, item: type[T]) -> T:
        return cls(item)


class Inject(Generic[T], metaclass=_InjectMeta):
    """A lazy proxy object that resolves a dependency from the container on first use.

    This works both with and without the @inject decorator.

    Usage:
        # The parameter `a` will be an instance of `Inject`.
        # When `a.hello()` is called, it will fetch `A` from the
        # container and delegate the call.
        def my_function(a: A = Inject[A]):
            a.hello()
    """

    def __init__(self, service_type: type[T]) -> None:
        self.service_type = service_type
        # Use a special object to signify that the value has not been resolved yet.
        self._injected_value: Any = None

    def _resolve(self) -> T:
        """Resolves the dependency from the container if it hasn't been already."""
        if self._injected_value is None:
            # Get the container at the last possible moment.
            container = InjectQ.get_instance()
            self._injected_value = container.get(self.service_type)
        return self._injected_value

    @property
    def __class__(self):  # type: ignore  # noqa: ANN204, PGH003
        # Before resolution -> looks like NoneType (or keep it as Inject)
        self._resolve()
        if self._injected_value is None:
            return type(None)  # or `Inject`
        # After resolution -> looks like the resolved object's type
        return self._injected_value.__class__

    def __repr__(self) -> str:
        self._resolve()
        if self._injected_value:
            return f"{self._injected_value.__class__.__name__}"
        return "None"

    def __getattr__(self, name: str) -> Any:
        """Called when an attribute is accessed (e.g., `a.hello`).

        This is the magic. It resolves the real object and gets the attribute from it.
        """
        resolved_instance = self._resolve()
        if name == "__class__":
            if resolved_instance is None:
                return type(None)
            return resolved_instance.__class__

        return getattr(resolved_instance, name)

    def __bool__(self) -> bool:
        """Allows `if a:` to work correctly.

        It resolves the dependency and checks the truthiness of the real object.

        Args:
            a: The injected dependency (optional).

        Returns:
            bool: Truthiness of the resolved object

        Raises:
            DependencyNotFoundError: If the dependency cannot be resolved
        """
        try:
            return bool(self._resolve())
        except DependencyNotFoundError:
            # If the dependency cannot be found, the proxy is considered Falsy.
            return False

    def __eq__(self, other: object) -> bool:
        """Compares the resolved object to another object."""
        if self._injected_value is None:
            # If not yet resolved, it can't be equal to anything.
            # You could resolve here, but it might have side effects.
            # A simple comparison is safer.
            return False
        return self._injected_value == other

    def __hash__(self) -> int:
        return hash(self._resolve())

    def __instancecheck__(self, instance: Any) -> bool:
        """Support isinstance(proxy, ResolvedType)."""
        return isinstance(self._resolve(), instance)

    def __subclasscheck__(self, subclass: Any) -> bool:
        """Support issubclass(proxy_type, ResolvedType)."""
        return issubclass(self._resolve().__class__, subclass)

    def __getattribute__(self, name: str):
        # Special handling for __class__ to spoof type()
        if name == "__class__":
            resolved_instance = self._resolve()
            if resolved_instance is None:
                return type(None)
            return resolved_instance.__class__
        return object.__getattribute__(self, name)
