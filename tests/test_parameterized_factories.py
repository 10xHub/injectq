"""Tests for parameterized factory functionality."""

import pytest

from injectq import InjectQ
from injectq.utils import DependencyNotFoundError


class TestParameterizedFactories:
    """Test cases for get_factory and call_factory methods."""

    def test_get_factory_returns_raw_function(self):
        """Test that get_factory returns the raw factory function."""
        container = InjectQ()

        # Bind a parameterized factory
        factory_func = lambda x: x * 2  # noqa: E731
        container.bind_factory("doubler", factory_func)

        # Get the factory
        retrieved_factory = container.get_factory("doubler")

        # Should return the same function
        assert callable(retrieved_factory)
        assert retrieved_factory(5) == 10
        assert retrieved_factory(10) == 20

    def test_get_factory_with_string_key(self):
        """Test get_factory with string key."""
        container = InjectQ()

        data = {"key1": "value1", "key2": "value2"}
        container.bind_factory("data_store", lambda key: data.get(key))

        factory = container.get_factory("data_store")
        assert factory("key1") == "value1"
        assert factory("key2") == "value2"

    def test_get_factory_not_found(self):
        """Test that get_factory raises error for non-existent factory."""
        container = InjectQ()

        with pytest.raises(DependencyNotFoundError):
            container.get_factory("non_existent")

    def test_call_factory_with_single_arg(self):
        """Test call_factory with a single argument."""
        container = InjectQ()

        data = {"a": 1, "b": 2, "c": 3}
        container.bind_factory("getter", lambda key: data[key])

        assert container.call_factory("getter", "a") == 1
        assert container.call_factory("getter", "b") == 2
        assert container.call_factory("getter", "c") == 3

    def test_call_factory_with_multiple_args(self):
        """Test call_factory with multiple positional arguments."""
        container = InjectQ()

        container.bind_factory("adder", lambda a, b, c: a + b + c)

        assert container.call_factory("adder", 1, 2, 3) == 6
        assert container.call_factory("adder", 10, 20, 30) == 60

    def test_call_factory_with_kwargs(self):
        """Test call_factory with keyword arguments."""
        container = InjectQ()

        def create_user(name: str, age: int, active: bool = True) -> dict:
            return {"name": name, "age": age, "active": active}

        container.bind_factory("user_factory", create_user)

        user1 = container.call_factory("user_factory", name="Alice", age=30)
        assert user1 == {"name": "Alice", "age": 30, "active": True}

        user2 = container.call_factory("user_factory", name="Bob", age=25, active=False)
        assert user2 == {"name": "Bob", "age": 25, "active": False}

    def test_call_factory_with_mixed_args(self):
        """Test call_factory with both positional and keyword arguments."""
        container = InjectQ()

        def calculator(op: str, a: float, b: float, precision: int = 2) -> float:
            result = {
                "add": a + b,
                "sub": a - b,
                "mul": a * b,
                "div": a / b if b != 0 else 0,
            }[op]
            return round(result, precision)

        container.bind_factory("calc", calculator)

        assert container.call_factory("calc", "add", 10, 5) == 15
        assert container.call_factory("calc", "mul", 10, 5) == 50
        assert container.call_factory("calc", "div", 10, 3, precision=3) == 3.333

    def test_call_factory_not_found(self):
        """Test that call_factory raises error for non-existent factory."""
        container = InjectQ()

        with pytest.raises(DependencyNotFoundError):
            container.call_factory("non_existent", "arg")

    def test_chained_get_factory_call(self):
        """Test chaining get_factory with immediate call."""
        container = InjectQ()

        container.bind_factory("multiplier", lambda x, n: x * n)

        # Chain the call
        result = container.get_factory("multiplier")(5, 3)
        assert result == 15

    def test_factory_reuse(self):
        """Test that get_factory returns a reusable function."""
        container = InjectQ()

        counter = {"value": 0}

        def increment(amount: int = 1) -> int:
            counter["value"] += amount
            return counter["value"]

        container.bind_factory("counter", increment)

        # Get the factory once
        inc = container.get_factory("counter")

        # Use it multiple times
        assert inc(1) == 1
        assert inc(2) == 3
        assert inc(5) == 8

    def test_parameterized_vs_di_factories(self):
        """Test that parameterized and DI factories can coexist."""
        container = InjectQ()

        # DI factory (no parameters)
        container.bind_factory("timestamp", lambda: "2024-01-01")

        # Parameterized factory
        data = {"key": "value"}
        container.bind_factory("data", lambda key: data[key])

        # DI factory is invoked automatically
        timestamp = container.get("timestamp")
        assert timestamp == "2024-01-01"

        # Parameterized factory needs manual invocation
        factory = container.get_factory("data")
        value = factory("key")
        assert value == "value"

        # Or use call_factory
        value2 = container.call_factory("data", "key")
        assert value2 == "value"

    def test_thread_safe_get_factory(self):
        """Test that get_factory works with thread-safe containers."""
        container = InjectQ(thread_safe=True)

        container.bind_factory("doubler", lambda x: x * 2)

        factory = container.get_factory("doubler")
        assert factory(10) == 20

    def test_thread_safe_call_factory(self):
        """Test that call_factory works with thread-safe containers."""
        container = InjectQ(thread_safe=True)

        container.bind_factory("adder", lambda a, b: a + b)

        result = container.call_factory("adder", 10, 20)
        assert result == 30

    def test_factory_with_complex_return_type(self):
        """Test factory that returns complex objects."""
        container = InjectQ()

        class Config:
            def __init__(self, env: str, debug: bool):
                self.env = env
                self.debug = debug

        container.bind_factory("config", lambda env, debug: Config(env, debug))

        config = container.call_factory("config", "prod", False)
        assert isinstance(config, Config)
        assert config.env == "prod"
        assert config.debug is False

    def test_factory_with_no_args_using_get_factory(self):
        """Test that get_factory works even for factories with no args."""
        container = InjectQ()

        container.bind_factory("constant", lambda: 42)

        factory = container.get_factory("constant")
        assert factory() == 42

    def test_call_factory_with_zero_args(self):
        """Test call_factory with no arguments."""
        container = InjectQ()

        container.bind_factory("random", lambda: 123)

        result = container.call_factory("random")
        assert result == 123

    def test_factory_proxy_and_get_factory_consistency(self):
        """Test that factories proxy and get_factory access the same factory."""
        container = InjectQ()

        factory_func = lambda x: x + 1  # noqa: E731
        container.bind_factory("incrementer", factory_func)

        # Get via factories proxy
        proxy_factory = container.factories["incrementer"]

        # Get via get_factory
        direct_factory = container.get_factory("incrementer")

        # Both should be the same function
        assert proxy_factory is direct_factory
        assert proxy_factory(5) == 6
        assert direct_factory(5) == 6

    def test_multiple_containers_with_parameterized_factories(self):
        """Test parameterized factories work independently in multiple containers."""
        container1 = InjectQ()
        container2 = InjectQ()

        container1.bind_factory("multiplier", lambda x: x * 2)
        container2.bind_factory("multiplier", lambda x: x * 3)

        assert container1.call_factory("multiplier", 5) == 10
        assert container2.call_factory("multiplier", 5) == 15

    def test_error_handling_in_parameterized_factory(self):
        """Test that errors in parameterized factories are propagated correctly."""
        container = InjectQ()

        def divider(a: int, b: int) -> float:
            return a / b

        container.bind_factory("divider", divider)

        # Should work normally
        assert container.call_factory("divider", 10, 2) == 5.0

        # Should raise ZeroDivisionError
        with pytest.raises(ZeroDivisionError):
            container.call_factory("divider", 10, 0)
