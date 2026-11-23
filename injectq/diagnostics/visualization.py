"""Dependency graph visualization and analysis.

The graph comes from the container's compiled resolution plans, so string
annotations, forward references and cycles are seen exactly as the resolver
sees them.
"""

import inspect
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from injectq.core.container import InjectQ
from injectq.utils.exceptions import InjectQError
from injectq.utils.graph import find_cycles, find_path
from injectq.utils.helpers import format_type_name
from injectq.utils.types import ServiceKey


class VisualizationError(InjectQError):
    """Errors related to dependency visualization."""


_NO_CONTAINER = "No container set for visualization"


def _node_id(key: ServiceKey) -> str:
    """A unique, readable id: ``module.QualName`` for classes, the string itself."""
    if isinstance(key, str):
        return key
    module = getattr(key, "__module__", None)
    qualname = getattr(key, "__qualname__", None)
    if module and qualname:
        return f"{module}.{qualname}"
    return str(key)


def _dot_quote(text: str) -> str:
    """A DOT double-quoted string: backslashes, quotes and newlines escaped."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped.replace("\n", "\\n") + '"'


class DependencyVisualizer:
    """Visualizes dependency graphs and provides analysis tools.

    Supports DOT (Graphviz), JSON and ASCII output.

    Example:
        ```python
        from injectq.diagnostics import DependencyVisualizer

        visualizer = DependencyVisualizer(container)
        dot_content = visualizer.to_dot()
        visualizer.save_graph("dependencies.dot", format="dot")
        ```
    """

    def __init__(self, container: InjectQ | None = None) -> None:
        """Initialize the visualizer.

        Args:
            container: The InjectQ container to visualize
        """
        self.container = container
        self._dependency_graph: dict[ServiceKey, list[ServiceKey]] = {}
        self._service_info: dict[ServiceKey, dict[str, Any]] = {}
        self._analysed: tuple[int, int] | None = None  # (id(container), version)

    def set_container(self, container: InjectQ | None) -> None:
        """Set the container to visualize."""
        self.container = container
        self._analysed = None

    # ---------------------------------------------------------------- analysis

    def _analyze_dependencies(self) -> None:
        """(Re)build the graph, only when the container's bindings changed."""
        if not self.container:
            self._dependency_graph = {}
            self._service_info = {}
            self._analysed = None
            return
        stamp = (id(self.container), self.container._version)  # noqa: SLF001
        if stamp == self._analysed:
            return
        graph = self.container.get_dependency_graph()
        resolver = self.container._resolver  # noqa: SLF001
        info: dict[ServiceKey, dict[str, Any]] = {}
        for key, deps in graph.items():
            binding = resolver.provider(key)
            if binding is None:
                info[key] = {"type": "unknown", "scope": "unknown"}
            else:
                impl = binding.implementation
                is_class = inspect.isclass(impl) and not binding.is_factory
                info[key] = {
                    "type": "factory" if binding.is_factory else "binding",
                    "scope": binding.scope,
                    "implementation": str(impl),
                    "is_class": is_class,
                    "is_instance": not binding.is_factory
                    and not inspect.isclass(impl)
                    and not callable(impl),
                }
            info[key]["dependencies"] = list(deps)
        self._dependency_graph = graph
        self._service_info = info
        self._analysed = stamp

    def _require_container(self) -> None:
        if not self.container:
            raise VisualizationError(_NO_CONTAINER)
        self._analyze_dependencies()

    def _all_nodes(self) -> list[ServiceKey]:
        """Registered keys, then dependency targets that are not registered."""
        nodes = list(self._service_info)
        seen = set(nodes)
        for deps in self._dependency_graph.values():
            for dep in deps:
                if dep not in seen:
                    seen.add(dep)
                    nodes.append(dep)
        return nodes

    # --------------------------------------------------------------------- DOT

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
        self._require_container()

        lines = ["digraph Dependencies {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=rounded];")
        lines.append("")

        def node_line(key: ServiceKey, indent: str) -> str:
            label = self._format_node_label(key, include_scopes, include_types)
            attrs = self._get_node_attributes(key)
            return f"{indent}{_dot_quote(_node_id(key))} [label={label}{attrs}];"

        if cluster_by_scope:
            groups: dict[str, list[ServiceKey]] = defaultdict(list)
            for key, info in self._service_info.items():
                groups[info.get("scope", "unknown")].append(key)
            for scope, services in groups.items():
                cluster = re.sub(r"\W", "_", scope)
                lines.append(f"  subgraph cluster_{cluster} {{")
                lines.append(f"    label={_dot_quote(scope.title() + ' Scope')};")
                lines.append("    style=dashed;")
                lines.extend(node_line(key, "    ") for key in services)
                lines.append("  }")
                lines.append("")
            lines.extend(
                node_line(key, "  ")
                for key in self._all_nodes()
                if key not in self._service_info
            )
        else:
            lines.extend(node_line(key, "  ") for key in self._all_nodes())

        lines.append("")
        for key, deps in self._dependency_graph.items():
            src = _dot_quote(_node_id(key))
            lines.extend(f"  {src} -> {_dot_quote(_node_id(dep))};" for dep in deps)

        lines.append("}")
        return "\n".join(lines)

    def _format_node_label(
        self, service_key: ServiceKey, include_scopes: bool, include_types: bool
    ) -> str:
        """A quoted DOT label: the class name, kind and scope."""
        info = self._service_info.get(service_key, {})
        parts = [format_type_name(service_key)]

        if include_types:
            if info.get("type") == "factory":
                parts.append("(factory)")
            elif info.get("is_class"):
                parts.append("(class)")
            elif info.get("is_instance"):
                parts.append("(instance)")
            elif not info:
                parts.append("(auto)")

        if include_scopes:
            scope = info.get("scope", "unknown")
            if scope != "unknown":
                parts.append(f"[{scope}]")

        # Parts are escaped one by one; "\n" is the DOT line break.
        quoted = (_dot_quote(part)[1:-1] for part in parts)
        return '"' + "\\n".join(quoted) + '"'

    def _get_node_attributes(self, service_key: ServiceKey) -> str:
        """Get DOT attributes for a node."""
        info = self._service_info.get(service_key)
        if info is None:
            return ", color=gray, style=dashed"
        attrs = []

        if info.get("type") == "factory":
            attrs.append("color=orange")
        elif info.get("is_class"):
            attrs.append("color=blue")
        elif info.get("is_instance"):
            attrs.append("color=green")
        else:
            attrs.append("color=gray")

        scope = info.get("scope")
        if scope == "singleton":
            attrs.append("penwidth=3")
        elif scope == "transient":
            attrs.append('style="rounded,dashed"')

        return ", " + ", ".join(attrs)

    # -------------------------------------------------------------- JSON/ASCII

    def to_json(self) -> dict[str, Any]:
        """Generate JSON representation of the dependency graph.

        Returns:
            Dictionary with nodes and edges information
        """
        self._require_container()

        nodes = []
        for key, info in self._service_info.items():
            nodes.append(
                {
                    "id": _node_id(key),
                    "label": format_type_name(key),
                    "type": info.get("type", "unknown"),
                    "scope": info.get("scope", "unknown"),
                    "implementation": info.get("implementation", ""),
                    "is_class": info.get("is_class", False),
                    "is_instance": info.get("is_instance", False),
                    "dependencies": [_node_id(d) for d in info["dependencies"]],
                }
            )

        edges = [
            {"from": _node_id(key), "to": _node_id(dep), "type": "dependency"}
            for key, deps in self._dependency_graph.items()
            for dep in deps
        ]

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

    def to_ascii(self, max_width: int = 80) -> str:  # noqa: ARG002
        """Generate a plain-text representation of the dependency graph."""
        self._require_container()

        lines = ["=== Dependency Graph ===", ""]
        for key in sorted(self._service_info, key=_node_id):
            info = self._service_info[key]
            header = (
                f"{format_type_name(key)} "
                f"({info.get('type', 'unknown')}, {info.get('scope', 'unknown')})"
            )
            lines.append(header)
            lines.append("-" * len(header))

            deps = self._dependency_graph.get(key, [])
            if deps:
                lines.append("Dependencies:")
                lines.extend(
                    f"  └─ {format_type_name(dep)}"
                    for dep in sorted(set(deps), key=_node_id)
                )
            else:
                lines.append("No dependencies")
            lines.append("")

        return "\n".join(lines)

    def save_graph(self, filename: str, format: str = "dot", **kwargs: Any) -> None:  # noqa: A002
        """Save the dependency graph to a file.

        Args:
            filename: Output filename
            format: Output format ("dot", "json", "ascii")
            **kwargs: Additional arguments for the format method
        """
        if format == "dot":
            content = self.to_dot(**kwargs)
        elif format == "json":
            content = json.dumps(self.to_json(), indent=2)
        elif format == "ascii":
            content = self.to_ascii(**kwargs)
        else:
            msg = f"Unknown format: {format}"
            raise VisualizationError(msg)

        with Path(filename).open("w", encoding="utf-8") as f:
            f.write(content)

    # ---------------------------------------------------------------- analysis

    def get_statistics(self) -> dict[str, Any]:
        """Get dependency graph statistics."""
        if not self.container:
            return {}
        self._analyze_dependencies()

        type_counts: dict[str, int] = defaultdict(int)
        scope_counts: dict[str, int] = defaultdict(int)
        for info in self._service_info.values():
            type_counts[info.get("type", "unknown")] += 1
            scope_counts[info.get("scope", "unknown")] += 1

        dependency_counts = [len(deps) for deps in self._dependency_graph.values()]
        total_dependencies = sum(dependency_counts)

        most_dependencies = sorted(
            ((key, len(deps)) for key, deps in self._dependency_graph.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:5]

        dependents: dict[ServiceKey, int] = defaultdict(int)
        for deps in self._dependency_graph.values():
            for dep in deps:
                dependents[dep] += 1
        most_depended = sorted(
            dependents.items(), key=lambda item: item[1], reverse=True
        )[:5]

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
            Cycles as closed paths: ``[A, B, A]`` means A -> B -> A
        """
        self._analyze_dependencies()
        return [[*cycle, cycle[0]] for cycle in find_cycles(self._dependency_graph)]

    def get_dependency_path(
        self, from_service: ServiceKey, to_service: ServiceKey
    ) -> list[ServiceKey] | None:
        """Find the shortest dependency path between two services.

        Returns:
            Path from ``from_service`` to ``to_service``, or None
        """
        self._analyze_dependencies()
        return find_path(self._dependency_graph, from_service, to_service)


__all__ = ["DependencyVisualizer", "VisualizationError"]
