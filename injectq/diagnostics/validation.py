"""Dependency validation and early error detection.

A thin presenter over the container's own validation: the answers are those
of ``InjectQ.validate()`` (auto-injectable classes and defaulted parameters
are fine, cycles and unresolvable annotations are errors), reported as a
``ValidationResult`` instead of an exception.
"""

from injectq.core.container import InjectQ
from injectq.utils.exceptions import InjectQError
from injectq.utils.graph import find_cycles, reachable
from injectq.utils.types import ServiceKey


class ValidationError(InjectQError):
    """A problem found while validating a container."""


class DependencyValidator:
    """Validator for dependency injection configurations.

    Example:
        ```python
        from injectq.diagnostics import DependencyValidator

        result = DependencyValidator(container).validate()
        if not result.is_valid:
            for error in result.errors:
                print(f"Validation error: {error}")
        ```
    """

    def __init__(self, container: InjectQ | None = None) -> None:
        """Initialize the validator.

        Args:
            container: The InjectQ container to validate
        """
        self.container = container
        self._graph: dict[ServiceKey, list[ServiceKey]] | None = None
        self._graph_version = -1

    def set_container(self, container: InjectQ) -> None:
        """Set the container to validate."""
        self.container = container
        self._graph = None

    def validate(self) -> "ValidationResult":
        """Validate every registered service; never raises for a bad graph.

        Returns:
            ValidationResult with one error per problem the container reports
        """
        if not self.container:
            return ValidationResult(
                errors=[ValidationError("No container set for validation")]
            )
        result = ValidationResult()
        try:
            self.container._registry.validate()  # noqa: SLF001
        except InjectQError as exc:
            result.errors.append(ValidationError(str(exc)))
        result.errors.extend(
            ValidationError(message)
            for message in self.container._resolver.validate()  # noqa: SLF001
        )
        return result

    def _dependency_graph(self) -> dict[ServiceKey, list[ServiceKey]]:
        """The engine's graph, rebuilt only when the bindings changed."""
        if not self.container:
            return {}
        version = self.container._version  # noqa: SLF001
        if self._graph is None or version != self._graph_version:
            self._graph = self.container.get_dependency_graph()
            self._graph_version = version
        return self._graph

    def get_dependency_graph(self) -> dict[ServiceKey, set[ServiceKey]]:
        """Direct dependencies of every registered service."""
        return {k: set(v) for k, v in self._dependency_graph().items()}

    def get_dependency_chain(self, service_key: ServiceKey) -> list[ServiceKey]:
        """``service_key`` and everything it transitively depends on."""
        return reachable(self._dependency_graph(), service_key)

    def find_potential_cycles(self) -> list[list[ServiceKey]]:
        """Find circular dependency cycles (``[A, B]`` means A -> B -> A)."""
        return find_cycles(self._dependency_graph())


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
    "ValidationError",
    "ValidationResult",
]
