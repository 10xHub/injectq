"""Dependency graph visualization and analysis."""

import inspect
from collections import defaultdict

from injectq.utils.exceptions import InjectQError
from injectq.utils.types import ServiceKey


class VisualizationError(InjectQError):
    """Errors related to dependency visualization."""


class DependencyVisualizer:
    """Visualizes dependency graphs and provides analysis tools.

    Supports multiple output formats including DOT (Graphviz), JSON,
    and ASCII art representations.

    Example:
        ```python
        from injectq.diagnostics import DependencyVisualizer

        visualizer = DependencyVisualizer(container)

        # Generate DOT format for Graphviz
        dot_content = visualizer.to_dot()

        # Generate ASCII art
        ascii_graph = visualizer.to_ascii()

        # Save to file
        visualizer.save_graph("dependencies.dot", format="dot")
        ```
    """

    def __init__(self, container=None) -> None:
        """Initialize the visualizer.

        Args:
            container: The InjectQ container to visualize
        """
        self.container = container
        self._dependency_graph: dict[ServiceKey, set[ServiceKey]] = defaultdict(set)
        self._service_info: dict[ServiceKey, dict] = {}

    def set_container(self, container) -> None:
        """Set the container to visualize."""
        self.container = container
        self._analyze_dependencies()

    def _analyze_dependencies(self) -> None:
        """Analyze the container to build dependency graph."""
        if not self.container:
            return

        self._dependency_graph.clear()
        self._service_info.clear()

        registry = self.container._registry

        # Analyze bindings
        for service_key, binding in registry._bindings.items():
            self._analyze_binding(service_key, binding)

        # Analyze factories
        for service_key, factory in registry._factories.items():
            self._analyze_factory(service_key, factory)

    def _analyze_binding(self, service_key: ServiceKey, binding) -> None:
        """Analyze a service binding for dependencies."""
        implementation = binding.implementation

        service_info = {
            "type": "binding",
            "scope": getattr(binding, "scope", "unknown"),
            "implementation": str(implementation),
            "is_class": inspect.isclass(implementation),
            "is_instance": not inspect.isclass(implementation)
            and not callable(implementation),
        }

        if inspect.isclass(implementation):
            # Analyze constructor dependencies
            try:
                init_signature = inspect.signature(implementation.__init__)
                dependencies = []

                for param_name, param in init_signature.parameters.items():
                    if param_name == "self":
                        continue

                    param_type = param.annotation
                    if param_type != inspect.Parameter.empty:
                        dependencies.append(param_type)
                        self._dependency_graph[service_key].add(param_type)

                service_info["dependencies"] = dependencies
                service_info["constructor_params"] = len(dependencies)

            except (ValueError, TypeError):
                service_info["dependencies"] = []
                service_info["constructor_params"] = 0
        else:
            service_info["dependencies"] = []
            service_info["constructor_params"] = 0

        self._service_info[service_key] = service_info

    def _analyze_factory(self, service_key: ServiceKey, factory) -> None:
        """Analyze a factory function for dependencies."""
        service_info = {
            "type": "factory",
            "scope": "factory",
            "implementation": str(factory),
            "is_class": False,
            "is_instance": False,
        }

        try:
            factory_signature = inspect.signature(factory)
            dependencies = []

            for param_name, param in factory_signature.parameters.items():
                # Skip container parameter
                if param_name in ("container", "c"):
                    continue

                param_type = param.annotation
                if param_type != inspect.Parameter.empty:
                    dependencies.append(param_type)
                    self._dependency_graph[service_key].add(param_type)

            service_info["dependencies"] = dependencies
            service_info["factory_params"] = len(dependencies)

        except (ValueError, TypeError):
            service_info["dependencies"] = []
            service_info["factory_params"] = 0

        self._service_info[service_key] = service_info

    def to_dot(
        self,
        include_scopes: bool = True,
        include_types: bool = True,
        cluster_by_scope: bool = False,
    ) -> str:
        """Generate DOT format for Graphviz visualization.

        Args:
            include_scopes: Whether to include scope information in nodes
            include_types: Whether to include type information in node labels
            cluster_by_scope: Whether to group nodes by scope

        Returns:
            DOT format string
        """
        if not self.container:
            msg = "No container set for visualization"
            raise VisualizationError(msg)

        self._analyze_dependencies()

        lines = ["digraph Dependencies {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")
        lines.append("")

        # Group services by scope if requested
        if cluster_by_scope:
            scope_groups = defaultdict(list)
            for service_key, info in self._service_info.items():
                scope = info.get("scope", "unknown")
                scope_groups[scope].append(service_key)

            for scope, services in scope_groups.items():
                lines.append(f"  subgraph cluster_{scope} {{")
                lines.append(f'    label="{scope.title()} Scope";')
                lines.append("    style=dashed;")

                for service_key in services:
                    label = self._format_node_label(
                        service_key, include_scopes, include_types
                    )
                    node_attrs = self._get_node_attributes(service_key)
                    lines.append(f'    "{service_key}" [label="{label}"{node_attrs}];')

                lines.append("  }")
                lines.append("")
        else:
            # Add nodes
            for service_key in self._service_info:
                label = self._format_node_label(
                    service_key, include_scopes, include_types
                )
                node_attrs = self._get_node_attributes(service_key)
                lines.append(f'  "{service_key}" [label="{label}"{node_attrs}];')

        lines.append("")

        # Add edges
        for service_key, dependencies in self._dependency_graph.items():
            for dependency in dependencies:
                edge_attrs = self._get_edge_attributes(service_key, dependency)
                lines.append(f'  "{service_key}" -> "{dependency}"{edge_attrs};')

        lines.append("}")
        return "\n".join(lines)

    def _format_node_label(
        self, service_key: ServiceKey, include_scopes: bool, include_types: bool
    ) -> str:
        """Format a node label for DOT output."""
        info = self._service_info.get(service_key, {})

        # Start with service name
        label_parts = [str(service_key).split(".")[-1]]  # Use just class name

        if include_types:
            service_type = info.get("type", "unknown")
            if service_type == "binding":
                if info.get("is_class"):
                    label_parts.append("(class)")
                elif info.get("is_instance"):
                    label_parts.append("(instance)")
            elif service_type == "factory":
                label_parts.append("(factory)")

        if include_scopes:
            scope = info.get("scope", "unknown")
            if scope != "unknown":
                label_parts.append(f"[{scope}]")

        return "\\n".join(label_parts)

    def _get_node_attributes(self, service_key: ServiceKey) -> str:
        """Get DOT attributes for a node."""
        info = self._service_info.get(service_key, {})
        attrs = []

        # Color by type
        service_type = info.get("type", "unknown")
        if service_type == "binding":
            if info.get("is_class"):
                attrs.append("color=blue")
            elif info.get("is_instance"):
                attrs.append("color=green")
            else:
                attrs.append("color=gray")
        elif service_type == "factory":
            attrs.append("color=orange")

        # Shape by scope
        scope = info.get("scope", "unknown")
        if scope == "singleton":
            attrs.append("penwidth=3")
        elif scope == "transient":
            attrs.append('style="rounded,dashed"')

        return ", " + ", ".join(attrs) if attrs else ""

    def _get_edge_attributes(
        self, from_service: ServiceKey, to_service: ServiceKey
    ) -> str:
        """Get DOT attributes for an edge."""
        # Could add different edge styles based on dependency type
        return ""

    def to_json(self) -> dict:
        """Generate JSON representation of the dependency graph.

        Returns:
            Dictionary with nodes and edges information
        """
        if not self.container:
            msg = "No container set for visualization"
            raise VisualizationError(msg)

        self._analyze_dependencies()

        nodes = []
        edges = []

        # Create nodes
        for service_key, info in self._service_info.items():
            node = {
                "id": str(service_key),
                "label": str(service_key).split(".")[-1],
                "type": info.get("type", "unknown"),
                "scope": info.get("scope", "unknown"),
                "implementation": info.get("implementation", ""),
                "is_class": info.get("is_class", False),
                "is_instance": info.get("is_instance", False),
                "dependencies": [str(dep) for dep in info.get("dependencies", [])],
            }
            nodes.append(node)

        # Create edges
        for service_key, dependencies in self._dependency_graph.items():
            for dependency in dependencies:
                edge = {
                    "from": str(service_key),
                    "to": str(dependency),
                    "type": "dependency",
                }
                edges.append(edge)

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_services": len(nodes),
                "total_dependencies": len(edges),
                "service_types": list({node["type"] for node in nodes}),
                "scopes": list({node["scope"] for node in nodes}),
            },
        }

    def to_ascii(self, max_width: int = 80) -> str:
        """Generate ASCII art representation of the dependency graph.

        Args:
            max_width: Maximum width for the ASCII output

        Returns:
            ASCII art string
        """
        if not self.container:
            msg = "No container set for visualization"
            raise VisualizationError(msg)

        self._analyze_dependencies()

        lines = ["=== Dependency Graph ===", ""]

        # List all services with their dependencies
        for service_key in sorted(self._service_info.keys(), key=str):
            info = self._service_info[service_key]
            dependencies = self._dependency_graph.get(service_key, set())

            # Service header
            service_name = str(service_key).split(".")[-1]
            service_type = info.get("type", "unknown")
            scope = info.get("scope", "unknown")

            header = f"{service_name} ({service_type}, {scope})"
            lines.append(header)
            lines.append("-" * len(header))

            if dependencies:
                lines.append("Dependencies:")
                for dep in sorted(dependencies, key=str):
                    dep_name = str(dep).split(".")[-1]
                    lines.append(f"  └─ {dep_name}")
            else:
                lines.append("No dependencies")

            lines.append("")

        return "\n".join(lines)

    def save_graph(self, filename: str, format: str = "dot", **kwargs) -> None:
        """Save the dependency graph to a file.

        Args:
            filename: Output filename
            format: Output format ("dot", "json", "ascii")
            **kwargs: Additional arguments for the format method
        """
        if format == "dot":
            content = self.to_dot(**kwargs)
        elif format == "json":
            import json

            content = json.dumps(self.to_json(), indent=2)
        elif format == "ascii":
            content = self.to_ascii(**kwargs)
        else:
            msg = f"Unknown format: {format}"
            raise VisualizationError(msg)

        with open(filename, "w") as f:
            f.write(content)

    def get_statistics(self) -> dict:
        """Get dependency graph statistics.

        Returns:
            Dictionary with various statistics about the graph
        """
        if not self.container:
            return {}

        self._analyze_dependencies()

        # Count services by type
        type_counts = defaultdict(int)
        scope_counts = defaultdict(int)

        for info in self._service_info.values():
            type_counts[info.get("type", "unknown")] += 1
            scope_counts[info.get("scope", "unknown")] += 1

        # Calculate dependency statistics
        dependency_counts = [len(deps) for deps in self._dependency_graph.values()]
        total_dependencies = sum(dependency_counts)

        # Find services with most dependencies
        most_dependencies = sorted(
            [(service, len(deps)) for service, deps in self._dependency_graph.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Find most depended-upon services
        dependents = defaultdict(int)
        for dependencies in self._dependency_graph.values():
            for dep in dependencies:
                dependents[dep] += 1

        most_depended = sorted(dependents.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_services": len(self._service_info),
            "total_dependencies": total_dependencies,
            "average_dependencies": total_dependencies / len(self._service_info)
            if self._service_info
            else 0,
            "max_dependencies": max(dependency_counts) if dependency_counts else 0,
            "services_by_type": dict(type_counts),
            "services_by_scope": dict(scope_counts),
            "most_dependencies": most_dependencies,
            "most_depended_upon": most_depended,
        }

    def find_cycles(self) -> list[list[ServiceKey]]:
        """Find circular dependencies in the graph.

        Returns:
            List of cycles, where each cycle is a list of service keys
        """
        cycles = []
        visited = set()
        recursion_stack = set()

        def dfs(service_key: ServiceKey, path: list[ServiceKey]) -> None:
            if service_key in recursion_stack:
                # Found cycle
                cycle_start = path.index(service_key)
                cycle = [*path[cycle_start:], service_key]
                cycles.append(cycle)
                return

            if service_key in visited:
                return

            visited.add(service_key)
            recursion_stack.add(service_key)

            for dependency in self._dependency_graph.get(service_key, set()):
                dfs(dependency, [*path, service_key])

            recursion_stack.remove(service_key)

        for service_key in self._dependency_graph:
            if service_key not in visited:
                dfs(service_key, [])

        return cycles

    def get_dependency_path(
        self, from_service: ServiceKey, to_service: ServiceKey
    ) -> list[ServiceKey] | None:
        """Find dependency path between two services.

        Args:
            from_service: Starting service
            to_service: Target service

        Returns:
            Path from from_service to to_service, or None if no path exists
        """
        if from_service == to_service:
            return [from_service]

        visited = set()
        queue = [(from_service, [from_service])]

        while queue:
            current, path = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            for dependency in self._dependency_graph.get(current, set()):
                if dependency == to_service:
                    return [*path, dependency]

                if dependency not in visited:
                    queue.append((dependency, [*path, dependency]))

        return None


__all__ = ["DependencyVisualizer", "VisualizationError"]
