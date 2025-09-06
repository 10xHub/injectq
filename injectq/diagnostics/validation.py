"""Dependency validation and early error detection."""

import inspect
from collections import defaultdict
from typing import Any, get_type_hints

from injectq.core.container import InjectQ
from injectq.utils.exceptions import InjectQError
from injectq.utils.types import ServiceKey


class ValidationError(InjectQError):
    """Errors related to dependency validation."""


class MissingDependencyError(ValidationError):
    """Error for missing dependencies."""


class InvalidBindingError(ValidationError):
    """Error for invalid bindings."""


class TypeMismatchError(ValidationError):
    """Error for type mismatches in bindings."""


class DependencyValidator:
    """Validator for dependency injection configurations.

    Performs early validation of dependency graphs to catch configuration
    errors before runtime.

    Example:
        ```python
        from injectq.diagnostics import DependencyValidator

        validator = DependencyValidator(container)
        validation_result = validator.validate()

        if not validation_result.is_valid:
            for error in validation_result.errors:
                print(f"Validation error: {error}")
        ```
    """

    def __init__(self, container: InjectQ | None = None) -> None:
        """Initialize the validator.

        Args:
            container: The InjectQ container to validate
        """
        self.container = container
        self._dependency_graph: dict[ServiceKey, set[ServiceKey]] = defaultdict(set)
        self._binding_types: dict[ServiceKey, type] = {}
        self._validation_cache: dict[ServiceKey, bool] = {}

    def set_container(self, container: InjectQ) -> None:
        """Set the container to validate."""
        self.container = container
        self._clear_cache()

    def _clear_cache(self) -> None:
        """Clear validation cache."""
        self._dependency_graph.clear()
        self._binding_types.clear()
        self._validation_cache.clear()

    def validate(self) -> "ValidationResult":
        """Perform comprehensive dependency validation.

        Returns:
            ValidationResult with errors and warnings
        """
        if not self.container:
            return ValidationResult(
                errors=[ValidationError("No container set for validation")]
            )

        result = ValidationResult()

        # Build dependency graph
        self._build_dependency_graph()

        # Run validation checks
        self._validate_circular_dependencies(result)
        self._validate_missing_dependencies(result)
        self._validate_type_compatibility(result)
        self._validate_scope_consistency(result)
        self._validate_factory_signatures(result)

        return result

    def _build_dependency_graph(self) -> None:
        """Build the dependency graph from container bindings."""
        if not self.container:
            return

        # Use the container's public API to get dependency graph
        graph = self.container.get_dependency_graph()

        # Convert to our internal format
        for service_key, dependencies in graph.items():
            self._dependency_graph[service_key] = set(dependencies)

    def _analyze_binding_dependencies(
        self,
        service_key: ServiceKey,
        binding: Any,
    ) -> None:
        """Analyze dependencies for a service binding."""
        implementation = binding.implementation

        if inspect.isclass(implementation):
            # Analyze constructor dependencies
            try:
                init_signature = inspect.signature(implementation.__init__)
                type_hints = get_type_hints(implementation.__init__)

                for param_name, param in init_signature.parameters.items():
                    if param_name == "self":
                        continue

                    # Get type from annotation or type hint
                    param_type = type_hints.get(param_name, param.annotation)

                    if param_type != inspect.Parameter.empty:
                        self._dependency_graph[service_key].add(param_type)

                self._binding_types[service_key] = implementation

            except (ValueError, TypeError):
                # Skip if we can't analyze the signature
                pass

    def _analyze_factory_dependencies(
        self,
        service_key: ServiceKey,
        factory,
    ) -> None:
        """Analyze dependencies for a factory function."""
        try:
            factory_signature = inspect.signature(factory)
            type_hints = get_type_hints(factory)

            for param_name, param in factory_signature.parameters.items():
                # Skip container parameter
                if param_name in ("container", "c"):
                    continue

                param_type = type_hints.get(param_name, param.annotation)

                if param_type != inspect.Parameter.empty:
                    self._dependency_graph[service_key].add(param_type)

            # Try to determine return type
            return_type = type_hints.get("return")
            if return_type:
                self._binding_types[service_key] = return_type

        except (ValueError, TypeError):
            # Skip if we can't analyze the signature
            pass

    def _validate_circular_dependencies(self, result: "ValidationResult") -> None:
        """Validate that there are no circular dependencies."""
        visited = set()
        recursion_stack = set()

        def dfs(service_key: ServiceKey, path: list[ServiceKey]) -> bool:
            if service_key in recursion_stack:
                # Found circular dependency
                cycle_start = path.index(service_key)
                cycle = [*path[cycle_start:], service_key]
                # Convert to string for error message since CircularDependencyError expects Type list
                error_msg = f"Circular dependency detected: {' -> '.join(str(s) for s in cycle)}"
                result.errors.append(ValidationError(error_msg))
                return False

            if service_key in visited:
                return True

            visited.add(service_key)
            recursion_stack.add(service_key)

            for dependency in self._dependency_graph.get(service_key, set()):
                if not dfs(dependency, [*path, service_key]):
                    return False

            recursion_stack.remove(service_key)
            return True

        # Check all services
        for service_key in self._dependency_graph:
            if service_key not in visited:
                dfs(service_key, [])

    def _validate_missing_dependencies(self, result: "ValidationResult") -> None:
        """Validate that all dependencies can be resolved."""
        if not self.container:
            return

        for service_key, dependencies in self._dependency_graph.items():
            for dependency in dependencies:
                # Check if dependency is registered
                if not self._can_resolve_dependency(dependency):
                    result.errors.append(
                        MissingDependencyError(
                            f"Service '{service_key}' depends on '{dependency}' "
                            f"which is not registered"
                        )
                    )

    def _can_resolve_dependency(self, dependency: ServiceKey) -> bool:
        """Check if a dependency can be resolved."""
        if not self.container:
            return False

        # For validation purposes, we only consider explicitly registered services
        # as resolvable. Auto-resolution is not considered valid for validation.
        return dependency in self.container

    def _validate_type_compatibility(self, result: "ValidationResult") -> None:
        """Validate type compatibility between bindings and dependencies."""
        for service_key, dependencies in self._dependency_graph.items():
            for dependency in dependencies:
                if dependency in self._binding_types:
                    expected_type = dependency
                    actual_type = self._binding_types[dependency]

                    # Only check if both are types (not strings)
                    if (
                        inspect.isclass(expected_type)
                        and inspect.isclass(actual_type)
                        and not self._is_compatible_type(expected_type, actual_type)
                    ):
                        result.warnings.append(
                            TypeMismatchError(
                                f"Type mismatch: {service_key} expects {expected_type} "
                                f"but {dependency} provides {actual_type}"
                            )
                        )

    def _is_compatible_type(self, expected: type, actual: type) -> bool:
        """Check if two types are compatible."""
        if expected == actual:
            return True

        # Check if actual is a subclass of expected
        try:
            if inspect.isclass(actual) and inspect.isclass(expected):
                return issubclass(actual, expected)
        except TypeError:
            # Handle cases where issubclass fails (e.g., with generics)
            pass

        return False

    def _validate_scope_consistency(self, result: "ValidationResult") -> None:
        """Validate scope consistency across dependencies."""
        # Skip scope validation for now as we don't have public access to binding scopes
        pass  # noqa: PIE790

    def _is_scope_mismatch(self, consumer_scope: str, dependency_scope: str) -> bool:
        """Check if there's a scope mismatch between consumer and dependency."""
        scope_hierarchy = ["singleton", "application", "request", "action", "transient"]

        try:
            consumer_index = scope_hierarchy.index(consumer_scope)
            dependency_index = scope_hierarchy.index(dependency_scope)
        except ValueError:
            return False
        else:
            # Problem if consumer has longer lifetime than dependency
            return consumer_index < dependency_index

    def _validate_factory_signatures(self, result: "ValidationResult") -> None:
        """Validate factory function signatures."""
        # Skip factory validation for now as we don't have public access to factories
        pass  # noqa: PIE790

    def get_dependency_graph(self) -> dict[ServiceKey, set[ServiceKey]]:
        """Get the computed dependency graph."""
        if not self._dependency_graph:  # Only build if not already built
            self._build_dependency_graph()
        return dict(self._dependency_graph)

    def get_dependency_chain(self, service_key: ServiceKey) -> list[ServiceKey]:
        """Get the full dependency chain for a service."""
        if not self._dependency_graph:  # Only build if not already built
            self._build_dependency_graph()

        chain = []
        visited = set()

        def build_chain(key: ServiceKey) -> None:
            if key in visited:
                return
            visited.add(key)
            chain.append(key)

            for dependency in self._dependency_graph.get(key, set()):
                build_chain(dependency)

        build_chain(service_key)
        return chain

    def find_potential_cycles(self) -> list[list[ServiceKey]]:
        """Find all potential circular dependency cycles."""
        cycles = []
        visited = set()

        def dfs(
            service_key: ServiceKey, path: list[ServiceKey], ancestors: set[ServiceKey]
        ) -> None:
            if service_key in ancestors:
                # Found cycle
                cycle_start = path.index(service_key)
                cycle = path[cycle_start:]
                cycles.append(cycle)
                return

            if service_key in visited:
                return

            visited.add(service_key)
            ancestors.add(service_key)

            for dependency in self._dependency_graph.get(service_key, set()):
                dfs(dependency, [*path, service_key], ancestors.copy())

            ancestors.remove(service_key)

        for service_key in self._dependency_graph:
            dfs(service_key, [], set())

        return cycles


class ValidationResult:
    """Result of dependency validation."""

    def __init__(
        self,
        errors: list[Exception] | None = None,
        warnings: list[Exception] | None = None,
    ) -> None:
        self.errors = errors or []
        self.warnings = warnings or []

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def __str__(self) -> str:
        """String representation of validation result."""
        lines = []

        if self.is_valid:
            lines.append("✅ Validation passed")
        else:
            lines.append("❌ Validation failed")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. {error}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"  {i}. {warning}")

        return "\n".join(lines)


__all__ = [
    "DependencyValidator",
    "InvalidBindingError",
    "MissingDependencyError",
    "TypeMismatchError",
    "ValidationError",
    "ValidationResult",
]
