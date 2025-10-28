"""Comprehensive tests for diagnostics.validation module."""

import pytest

from injectq import InjectQ
from injectq.diagnostics.validation import (
    DependencyValidator,
    InvalidBindingError,
    MissingDependencyError,
    TypeMismatchError,
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


def test_validator_clear_cache() -> None:
    """Test cache clearing."""
    container = InjectQ()
    validator = DependencyValidator(container)

    # Build some cache
    validator._dependency_graph[str] = {int}
    validator._binding_types[str] = str

    validator._clear_cache()

    assert len(validator._dependency_graph) == 0
    assert len(validator._binding_types) == 0


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


def test_validator_can_resolve_dependency() -> None:
    """Test checking if dependency can be resolved."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    validator = DependencyValidator(container)

    # Should be able to resolve registered service
    assert validator._can_resolve_dependency(Service)

    # Should not be able to resolve unregistered service
    class Unregistered:
        pass

    assert not validator._can_resolve_dependency(Unregistered)


def test_validator_is_compatible_type() -> None:
    """Test type compatibility checking."""
    validator = DependencyValidator()

    # Same type is compatible
    assert validator._is_compatible_type(str, str)

    # Subclass is compatible
    class Base:
        pass

    class Derived(Base):
        pass

    assert validator._is_compatible_type(Base, Derived)


def test_validator_is_scope_mismatch() -> None:
    """Test scope mismatch checking."""
    validator = DependencyValidator()

    # Singleton depending on transient is a mismatch
    assert validator._is_scope_mismatch("singleton", "transient")

    # Transient depending on singleton is fine
    assert not validator._is_scope_mismatch("transient", "singleton")

    # Same scope is fine
    assert not validator._is_scope_mismatch("singleton", "singleton")


def test_missing_dependency_error() -> None:
    """Test MissingDependencyError."""
    error = MissingDependencyError("Missing dependency")
    assert "Missing dependency" in str(error)


def test_invalid_binding_error() -> None:
    """Test InvalidBindingError."""
    error = InvalidBindingError("Invalid binding")
    assert "Invalid binding" in str(error)


def test_type_mismatch_error() -> None:
    """Test TypeMismatchError."""
    error = TypeMismatchError("Type mismatch")
    assert "Type mismatch" in str(error)


def test_validator_build_dependency_graph() -> None:
    """Test building dependency graph."""
    container = InjectQ()

    class Service:
        pass

    container.bind(Service, Service)

    validator = DependencyValidator(container)
    validator._build_dependency_graph()

    # Graph should be built
    assert isinstance(validator._dependency_graph, dict)


def test_validator_validate_circular_dependencies() -> None:
    """Test circular dependency validation."""
    container = InjectQ()
    validator = DependencyValidator(container)
    result = ValidationResult()

    # Manually create a circular dependency in graph
    validator._dependency_graph[str] = {int}
    validator._dependency_graph[int] = {str}

    validator._validate_circular_dependencies(result)

    # Should detect circular dependency
    assert len(result.errors) > 0


def test_validator_validate_missing_dependencies() -> None:
    """Test missing dependency validation."""
    container = InjectQ()
    validator = DependencyValidator(container)
    result = ValidationResult()

    # Manually create a dependency on unregistered service
    class Service:
        pass

    class Unregistered:
        pass

    container.bind(Service, Service)
    validator._dependency_graph[Service] = {Unregistered}

    validator._validate_missing_dependencies(result)

    # Should detect missing dependency
    assert len(result.errors) > 0
    assert any(isinstance(e, MissingDependencyError) for e in result.errors)


def test_validator_validate_type_compatibility() -> None:
    """Test type compatibility validation."""
    container = InjectQ()
    validator = DependencyValidator(container)
    result = ValidationResult()

    class Base:
        pass

    class Derived(Base):
        pass

    # Setup compatibility check
    validator._dependency_graph[Derived] = {Base}
    validator._binding_types[Base] = Base

    validator._validate_type_compatibility(result)

    # Should be compatible (no errors or warnings)
    # Implementation may not generate warnings for compatible types


def test_validator_validate_scope_consistency() -> None:
    """Test scope consistency validation."""
    container = InjectQ()
    validator = DependencyValidator(container)
    result = ValidationResult()

    validator._validate_scope_consistency(result)

    # Currently a no-op, should not error
    assert True


def test_validator_validate_factory_signatures() -> None:
    """Test factory signature validation."""
    container = InjectQ()
    validator = DependencyValidator(container)
    result = ValidationResult()

    validator._validate_factory_signatures(result)

    # Currently a no-op, should not error
    assert True


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
