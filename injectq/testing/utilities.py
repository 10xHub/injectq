"""Testing utilities for InjectQ dependency injection library."""

from __future__ import annotations

import sys
import warnings
from contextlib import AbstractContextManager, contextmanager
from typing import TYPE_CHECKING, Any

from injectq.core import InjectQ
from injectq.modules import Module


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from injectq.core.container import ModuleBinder
    from injectq.utils import ServiceKey

if sys.version_info >= (3, 11):
    from typing import Self
else:  # pragma: no cover
    from typing_extensions import Self


@contextmanager
def override_dependency(
    service_type: ServiceKey,
    override_value: Any,
    container: InjectQ | None = None,
) -> Iterator[None]:
    """Context manager to temporarily override a dependency for testing.

    Args:
        service_type: The service type to override
        override_value: The value to use as override
        container: Optional container to use (defaults to global instance)

    Yields:
        None

    Example:
        with override_dependency(Database, MockDatabase()):
            service = container.get(UserService)
            # service will use MockDatabase
    """
    if container is None:
        container = InjectQ.get_instance()

    with container.override(service_type, override_value):
        yield


@contextmanager
def isolated_container() -> Iterator[InjectQ]:
    """Use a fresh container for the duration of the block.

    The container becomes both the global instance and the current context
    container (``InjectQ.test_mode()``), so ``InjectQ.get_instance()``,
    ``@inject`` and the registration decorators use it, even inside an
    outer ``ContainerContext``. Both are restored on exit.

    Yields:
        A temporary InjectQ container

    Example:
        with isolated_container() as container:
            container.bind(Database, MockDatabase)
            # Use container for testing
    """
    with InjectQ.test_mode() as container:
        yield container


class MockFactory:
    """Factory for creating mock services.

    Useful for creating test doubles that implement the same interface
    as the real services but with controlled behavior. Mocks are cached per
    ``(service_type, kwargs)``: the same arguments give the same mock,
    different arguments a different one. ``reset()`` drops them all.
    """

    def __init__(self) -> None:
        self._instances: dict[type, list[tuple[dict[str, Any], Any]]] = {}

    def create_mock(self, service_type: type, **kwargs: Any) -> Any:
        """Create (or reuse) a mock instance of a service type.

        Args:
            service_type: The type to mock
            **kwargs: Attributes to set on the mock

        Returns:
            A mock instance: the given attributes, and any other method
            returns ``"mock_<name>_result"``.
        """
        cached = self._instances.setdefault(service_type, [])
        for known, instance in cached:
            if known == kwargs:
                return instance

        class MockService:
            def __init__(self, **init_kwargs: Any) -> None:
                for key, value in init_kwargs.items():
                    setattr(self, key, value)

            def __getattr__(self, name: str) -> Callable[..., Any]:
                # Return a simple mock function for any method
                def mock_method(*args: Any, **method_kwargs: Any) -> str:  # noqa: ARG001
                    return f"mock_{name}_result"

                return mock_method

        MockService.__name__ = MockService.__qualname__ = (
            f"Mock{getattr(service_type, '__name__', 'Service')}"
        )
        instance = MockService(**kwargs)
        cached.append((dict(kwargs), instance))
        return instance

    def reset(self) -> None:
        """Reset all mock instances."""
        self._instances.clear()


# Global mock factory instance
mock_factory = MockFactory()


def create_test_module(bindings: dict[ServiceKey, Any]) -> Module:
    """Create a module with the specified instance bindings.

    Args:
        bindings: Dictionary of service type to instance

    Returns:
        A module configured with the bindings

    Example:
        module = create_test_module({
            Database: MockDatabase(),
            str: "test_connection_string"
        })
        container = InjectQ([module])
    """
    module = MockModule()
    for service_type, implementation in bindings.items():
        module.bind_value(service_type, implementation)
    return module


class MockModule(Module):
    """A module for tests: binds mocks and fixed values.

    Example:
        container.install_module(MockModule().mock(Database).bind_value("url", "x"))
    """

    def __init__(self) -> None:
        self._bindings: list[tuple[ServiceKey, Any]] = []

    def mock(self, service_type: type, **kwargs: Any) -> Self:
        """Bind a mock (see ``MockFactory.create_mock``) for a service type.

        Args:
            service_type: The service type to mock
            **kwargs: Attributes of the mock

        Returns:
            Self for fluent API
        """
        self._bindings.append(
            (service_type, mock_factory.create_mock(service_type, **kwargs))
        )
        return self

    def bind_value(self, service_type: ServiceKey, value: Any) -> Self:
        """Bind a fixed value.

        Args:
            service_type: The service type to bind
            value: The value to bind

        Returns:
            Self for fluent API
        """
        self._bindings.append((service_type, value))
        return self

    def configure(self, binder: ModuleBinder) -> None:
        """Bind every mock and value as an instance."""
        for service_type, value in self._bindings:
            binder.bind_instance(service_type, value)


def container_fixture(name: str = "container") -> Any:
    """Create a pytest fixture yielding an ``isolated_container()``.

    Args:
        name: The fixture name (default ``"container"``).

    Returns:
        A pytest fixture; assign it to a module-level name in
        ``conftest.py`` (or a test module).

    Example:
        # In conftest.py
        from injectq.testing import container_fixture

        container = container_fixture()

        # In test files
        def test_service(container):
            container.bind(Database, MockDatabase)
    """
    import pytest  # noqa: PLC0415

    def fixture() -> Iterator[InjectQ]:
        with isolated_container() as test_cont:
            yield test_cont

    return pytest.fixture(name=name)(fixture)


# --------------------------------------------------------------------------
# Deprecated names (removed in 0.8). They are served by the module
# ``__getattr__`` below rather than defined at module level, so pytest never
# sees them here; each warns when used.


def _deprecated(old: str, new: str) -> None:
    warnings.warn(
        f"injectq.testing.{old} is deprecated since 0.6 and will be removed in "
        f"0.8; use {new} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def _test_container() -> AbstractContextManager[InjectQ]:
    _deprecated("test_container", "isolated_container")
    return isolated_container()


_test_container.__name__ = _test_container.__qualname__ = "test_container"
# A test module importing this name must not get it collected as a test.
_test_container.__test__ = False  # type: ignore[attr-defined]


def _pytest_container_fixture() -> Any:
    _deprecated(
        "pytest_container_fixture",
        "container_fixture (a conftest.py name starting with 'pytest_' is "
        "taken for a pytest hook)",
    )
    return container_fixture()


_pytest_container_fixture.__name__ = "pytest_container_fixture"
_pytest_container_fixture.__qualname__ = "pytest_container_fixture"


class _TestModule(MockModule):
    """Deprecated alias of ``MockModule``."""

    __test__ = False  # never collected when imported into a test module

    def __init__(self) -> None:
        _deprecated("TestModule", "MockModule")
        super().__init__()


_TestModule.__name__ = _TestModule.__qualname__ = "TestModule"

DEPRECATED: dict[str, Any] = {
    "test_container": _test_container,
    "TestModule": _TestModule,
    "pytest_container_fixture": _pytest_container_fixture,
}


def __getattr__(name: str) -> Any:
    try:
        return DEPRECATED[name]
    except KeyError:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from None
