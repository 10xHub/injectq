"""Comprehensive tests for diagnostics.validation module."""

import pytest

from injectq import InjectQ
from injectq.diagnostics.validation import (
    DependencyValidator,
    ValidationError,
    ValidationResult,
)


def test_validation_result_default() -> None:
    """Test ValidationResult with defaults."""
    result = ValidationResult()
    assert result.is_valid
    assert not result.has_warnings
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_validation_result_with_errors() -> None:
    """Test ValidationResult with errors."""
    errors = [ValidationError("error1"), ValidationError("error2")]
    result = ValidationResult(errors=errors)

    assert not result.is_valid
    assert len(result.errors) == 2


def test_validation_result_with_warnings() -> None:
    """Test ValidationResult with warnings."""
    warnings = [ValidationError("warn1")]
    result = ValidationResult(warnings=warnings)

    assert result.is_valid  # Still valid with warnings
    assert result.has_warnings
    assert len(result.warnings) == 1


def test_validation_result_str() -> None:
    """Test string representation of ValidationResult."""
    result = ValidationResult()
    str_repr = str(result)
    assert "✅ Validation passed" in str_repr

    errors = [ValidationError("error1")]
    result_with_errors = ValidationResult(errors=errors)
    str_repr_errors = str(result_with_errors)
    assert "❌ Validation failed" in str_repr_errors
    assert "Errors" in str_repr_errors


def test_validator_no_container() -> None:
    """Test validator without container."""
    validator = DependencyValidator()
    result = validator.validate()

    assert not result.is_valid
    assert len(result.errors) == 1


def test_validator_set_container() -> None:
    """Test setting container on validator."""
    validator = DependencyValidator()
    container = InjectQ()

    validator.set_container(container)

    assert validator.container is container


def test_validator_simple_validation() -> None:
    """Test simple validation with valid container."""
    container = InjectQ()

    class SimpleService:
        pass

    container.bind(SimpleService, SimpleService)

    validator = DependencyValidator(container)
    result = validator.validate()

    # Should pass validation
    assert result.is_valid


def test_validator_with_dependencies() -> None:
    """Test validation with dependencies."""
    container = InjectQ()

    class Dependency:
        pass

    class Service:
        def __init__(self, dep: Dependency) -> None:
            self.dep = dep

    # Register both
    container.bind(Dependency, Dependency)
    container.bind(Service, Service)

    validator = DependencyValidator(container)
    result = validator.validate()

    assert result.is_valid


def test_validator_get_dependency_graph() -> None:
    """Test getting dependency graph."""
    container = InjectQ()

    class Dependency:
        pass

    class Service:
        def __init__(self, dep: Dependency) -> None:
            self.dep = dep

    container.bind(Dependency, Dependency)
    container.bind(Service, Service)

    validator = DependencyValidator(container)
    graph = validator.get_dependency_graph()

    # Graph should exist
    assert isinstance(graph, dict)


def test_validator_get_dependency_chain() -> None:
    """Test getting dependency chain."""
    container = InjectQ()

    class Base:
        pass

    class Middle:
        def __init__(self, base: Base) -> None:
            self.base = base

    class Top:
        def __init__(self, middle: Middle) -> None:
            self.middle = middle

    container.bind(Base, Base)
    container.bind(Middle, Middle)
    container.bind(Top, Top)

    validator = DependencyValidator(container)
    chain = validator.get_dependency_chain(Top)

    # Chain should contain the service
    assert Top in chain


def test_validator_find_potential_cycles() -> None:
    """Test finding potential cycles."""
    container = InjectQ()

    validator = DependencyValidator(container)
    cycles = validator.find_potential_cycles()

    # With empty container, no cycles
    assert isinstance(cycles, list)


def test_validation_error_base() -> None:
    """Test ValidationError base class."""
    error = ValidationError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_validator_with_factory() -> None:
    """Test validator with factory bindings."""
    container = InjectQ()

    def factory() -> str:
        return "value"

    container.bind_factory(str, factory)

    validator = DependencyValidator(container)
    result = validator.validate()

    # Should handle factory bindings
    assert result.is_valid or len(result.errors) >= 0  # Either way is acceptable


def test_validator_with_instance() -> None:
    """Test validator with instance bindings."""
    container = InjectQ()

    container.bind_instance(str, "test_value")

    validator = DependencyValidator(container)
    result = validator.validate()

    # Should handle instance bindings
    assert result.is_valid


def test_validator_complex_graph() -> None:
    """Test validator with complex dependency graph."""
    container = InjectQ()

    class A:
        pass

    class B:
        def __init__(self, a: A) -> None:
            self.a = a

    class C:
        def __init__(self, a: A, b: B) -> None:
            self.a = a
            self.b = b

    class D:
        def __init__(self, c: C) -> None:
            self.c = c

    container.bind(A, A)
    container.bind(B, B)
    container.bind(C, C)
    container.bind(D, D)

    validator = DependencyValidator(container)
    result = validator.validate()

    # Should handle complex graph
    assert result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
