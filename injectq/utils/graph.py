"""Small graph algorithms over ``{node: [dependency, ...]}`` mappings.

Shared by the dependency validator and visualizer. Iterative, so deep
dependency chains cannot hit the recursion limit.
"""

from collections import deque
from collections.abc import Iterable, Mapping
from typing import TypeVar


N = TypeVar("N")


def find_cycles(graph: Mapping[N, Iterable[N]]) -> list[list[N]]:
    """Return the cycles of ``graph``, each as its nodes in dependency order.

    A cycle ``[A, B]`` means ``A -> B -> A``. Self-loops are ``[A]``. Every
    back edge found by a depth-first walk yields one cycle.
    """
    cycles: list[list[N]] = []
    done: set[N] = set()
    for root in graph:
        if root in done:
            continue
        path: list[N] = [root]
        on_path = {root}
        stack = [iter(graph.get(root, ()))]
        while stack:
            for dep in stack[-1]:
                if dep in on_path:
                    cycles.append(path[path.index(dep) :])
                elif dep not in done:
                    path.append(dep)
                    on_path.add(dep)
                    stack.append(iter(graph.get(dep, ())))
                    break
            else:
                stack.pop()
                node = path.pop()
                on_path.discard(node)
                done.add(node)
    return cycles


def find_path(graph: Mapping[N, Iterable[N]], start: N, goal: N) -> list[N] | None:
    """Shortest dependency path from ``start`` to ``goal`` (BFS), or None."""
    if start == goal:
        return [start]
    parent: dict[N, N] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for dep in graph.get(node, ()):
            if dep in seen:
                continue
            parent[dep] = node
            if dep == goal:
                path = [dep]
                while path[-1] != start:
                    path.append(parent[path[-1]])
                path.reverse()
                return path
            seen.add(dep)
            queue.append(dep)
    return None


def reachable(graph: Mapping[N, Iterable[N]], start: N) -> list[N]:
    """``start`` and everything it depends on, depth-first, each once."""
    order: list[N] = []
    seen: set[N] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        order.append(node)
        stack.extend(reversed(list(graph.get(node, ()))))
    return order
