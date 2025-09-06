"""Singleton decorator for automatic service registration."""

from collections.abc import Callable
from typing import TypeVar

from injectq.core import InjectQ, ScopeType
from injectq.core.context import ContainerContext
from injectq.utils import BindingError


T = TypeVar("T", bound=type)


def singleton(cls: T, container: InjectQ | None = None) -> T:
    """Decorator to automatically register a class as a singleton service.

    The decorated class will be automatically bound to itself in the
    global container with singleton scope.

    Args:
        cls: Class to register as singleton
        container: Optional container to use (defaults to global or context container)

    Returns:
        The same class (unmodified)

    Example:
        @singleton
        class UserService:
            def __init__(self, db: Database):
                self.db = db
    """
    if not isinstance(cls, type):
        msg = "@singleton can only be applied to classes"
        raise BindingError(msg)

    # Get the global container
    target_container = container
    if not target_container:
        target_container = ContainerContext.get_current() if ContainerContext else None
    if not target_container:
        target_container = InjectQ.get_instance()

    # Register the class as a singleton binding to itself
    target_container.bind(cls, cls, scope=ScopeType.SINGLETON)

    return cls


def transient(cls: T, container: InjectQ | None = None) -> T:
    """Decorator to automatically register a class as a transient service.

    The decorated class will be automatically bound to itself in the
    global container with transient scope (new instance each time).

    Args:
        cls: Class to register as transient
        container: Optional container to use (defaults to global or context container)

    Returns:
        The same class (unmodified)

    Example:
        @transient
        class OrderProcessor:
            def __init__(self, db: Database):
                self.db = db
    """
    if not isinstance(cls, type):
        msg = "@transient can only be applied to classes"
        raise BindingError(msg)

    target_container = container
    if not target_container:
        target_container = ContainerContext.get_current() if ContainerContext else None
    if not target_container:
        target_container = InjectQ.get_instance()

    # Register the class as a transient binding to itself
    target_container.bind(cls, cls, scope=ScopeType.TRANSIENT)

    return cls


def scoped(scope_name: str, container: InjectQ | None = None) -> Callable:
    """Decorator factory to register a class with a specific scope.

    Args:
        scope_name: Name of the scope to use
        container: Optional container to use (defaults to global or context container)

    Returns:
        Decorator function

    Example:
        @scoped("request")
        class RequestContext:
            def __init__(self, request_id: str):
                self.request_id = request_id
    """

    def decorator(cls: T) -> T:
        if not isinstance(cls, type):
            msg = f"@scoped('{scope_name}') can only be applied to classes"
            raise BindingError(msg)

        # Get the global container
        target_container = container
        if not target_container:
            target_container = (
                ContainerContext.get_current() if ContainerContext else None
            )
        if not target_container:
            target_container = InjectQ.get_instance()

        # Register the class with the specified scope
        target_container.bind(cls, cls, scope=scope_name)

        return cls

    return decorator


def register_as(
    service_type: type,
    scope: str = "singleton",
    container: InjectQ | None = None,
) -> Callable:
    """Decorator factory to register a class as an implementation of a service type.

    Args:
        service_type: The service type/interface to register as
        scope: The scope to use for the service
        container: Optional container to use (defaults to global or context container)

    Returns:
        Decorator function

    Example:
        @register_as(UserRepository, scope="singleton")
        class SqlUserRepository:
            def __init__(self, db: Database):
                self.db = db
    """

    def decorator(cls: T) -> T:
        if not isinstance(cls, type):
            msg = f"@register_as({service_type}) can only be applied to classes"
            raise BindingError(msg)

        # Get the global container
        target_container = container
        if not target_container:
            target_container = (
                ContainerContext.get_current() if ContainerContext else None
            )
        if not target_container:
            target_container = InjectQ.get_instance()

        # Register the class as implementation of service_type
        target_container.bind(service_type, cls, scope=scope)

        return cls

    return decorator
