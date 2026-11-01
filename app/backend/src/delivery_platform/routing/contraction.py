"""Contraction hierarchies: preprocessing and upward bidirectional queries.

CH preprocessing contracts nodes one by one in a heuristic order. Contracting a
node removes it from the working graph and inserts a *shortcut* between two of
its neighbours when the path through the node is shorter than any witness that
avoids it. Every edge keeps its level, and every shortest path in the original
graph corresponds to an up-down path in the hierarchy — so a query is two
one-directional Dijkstras on a graph that only ever goes up.

Why this and not just ALT: ALT answers from precomputed landmark distances and
still expands a noticeable share of the graph; CH pays a much larger one-time
preprocessing cost and then answers in a handful of node visits. Which one wins
depends on the query volume, and the benchmark publishes the break-even point.

Implementation notes:

* Nodes are integer indices internally; string ids only at the boundary.
* The witness search is bounded (``settle_limit``). A missed witness can only
  add a redundant shortcut, never break correctness, so the bound is safe.
* Shortcut creation records its two child edges, so a query can expand a path
  made of shortcuts back into original graph nodes.
* Preprocessing is deterministic: indices come from sorted ids, ties in the
  priority queue break on the index, and neighbor iteration is insertion-ordered.
"""

from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass

from delivery_platform.routing.graph import StreetGraph
from delivery_platform.routing.path import Objective, edge_weight

DEFAULT_SETTLE_LIMIT = 200
#: Witness searches are bounded by hop count, the standard CH tuning knob: a
#: witness that needs more than a few edges is rare on road networks, and a
#: missed one only adds a redundant shortcut.
DEFAULT_WITNESS_HOPS = 3


@dataclass(frozen=True)
class CHStats:
    nodes: int
    original_edges: int
    shortcuts: int
    settle_limit: int
    witness_hops: int
    preprocessing_time_ns: int


@dataclass(frozen=True)
class CHPath:
    """One query result: cost, the original node path, and work performed."""

    cost: float
    nodes: list[str]
    settled: int
    settle_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class CHGraph:
    """The processed hierarchy, queryable for one objective."""

    ids: tuple[str, ...]
    index: dict[str, int]
    levels: tuple[int, ...]
    up_forward: tuple[tuple[tuple[int, float], ...], ...]
    up_backward: tuple[tuple[tuple[int, float], ...], ...]
    children: dict[tuple[int, int], tuple[tuple[int, int], tuple[int, int]]]
    stats: CHStats

    @property
    def shortcut_count(self) -> int:
        return self.stats.shortcuts

    def expand(self, edge: tuple[int, int]) -> list[tuple[int, int]]:
        """Expand a (possibly shortcut) edge into original graph edges."""
        chain: list[tuple[int, int]] = []
        stack = [edge]
        while stack:
            current = stack.pop()
            children = self.children.get(current)
            if children is None:
                chain.append(current)
            else:
                left, right = children
                stack.append(right)
                stack.append(left)
        return chain

    def shortest_path(
        self, source: str, target: str, *, trace: bool = False
    ) -> CHPath | None:
        """Return the shortest path or ``None`` when the target is unreachable.

        Two upward Dijkstras advance in lockstep and stop as soon as neither
        frontier can improve the best meeting. They keep only the nodes they
        touch: a CH query settles a few dozen nodes, so allocating arrays the
        size of the graph per query would dominate its cost at city scale.
        """
        start, goal = self.index[source], self.index[target]
        if start == goal:
            return CHPath(cost=0.0, nodes=[source], settled=0)
        infinity = float("inf")
        dist_f: dict[int, float] = {start: 0.0}
        dist_b: dict[int, float] = {goal: 0.0}
        parent_f: dict[int, int] = {}
        parent_b: dict[int, int] = {}
        settled_f: set[int] = set()
        settled_b: set[int] = set()
        heap_f: list[tuple[float, int]] = [(0.0, start)]
        heap_b: list[tuple[float, int]] = [(0.0, goal)]
        settled = 0
        settle_order: list[str] = []
        best = infinity
        meeting = -1

        def relax_forward(node: int, cost: float) -> None:
            nonlocal best, meeting
            for neighbour, weight in self.up_forward[node]:
                candidate = cost + weight
                if candidate < dist_f.get(neighbour, infinity):
                    dist_f[neighbour] = candidate
                    parent_f[neighbour] = node
                    heapq.heappush(heap_f, (candidate, neighbour))
                    other = dist_b.get(neighbour)
                    if other is not None and candidate + other < best:
                        best = candidate + other
                        meeting = neighbour

        def relax_backward(node: int, cost: float) -> None:
            nonlocal best, meeting
            for neighbour, weight in self.up_backward[node]:
                candidate = cost + weight
                if candidate < dist_b.get(neighbour, infinity):
                    dist_b[neighbour] = candidate
                    parent_b[neighbour] = node
                    heapq.heappush(heap_b, (candidate, neighbour))
                    other = dist_f.get(neighbour)
                    if other is not None and other + candidate < best:
                        best = other + candidate
                        meeting = neighbour

        while heap_f or heap_b:
            top_f = heap_f[0][0] if heap_f else infinity
            top_b = heap_b[0][0] if heap_b else infinity
            if min(top_f, top_b) >= best:
                break
            if top_f <= top_b:
                cost, node = heapq.heappop(heap_f)
                if node in settled_f or cost > dist_f[node]:
                    continue
                settled_f.add(node)
                settled += 1
                if trace:
                    settle_order.append(self.ids[node])
                other = dist_b.get(node)
                if other is not None and cost + other < best:
                    best = cost + other
                    meeting = node
                relax_forward(node, cost)
            else:
                cost, node = heapq.heappop(heap_b)
                if node in settled_b or cost > dist_b[node]:
                    continue
                settled_b.add(node)
                settled += 1
                if trace:
                    settle_order.append(self.ids[node])
                other = dist_f.get(node)
                if other is not None and other + cost < best:
                    best = other + cost
                    meeting = node
                relax_backward(node, cost)

        if meeting < 0 or best == infinity:
            return None

        upward = [meeting]
        while upward[-1] != start:
            upward.append(parent_f[upward[-1]])
        upward.reverse()
        downward = [meeting]
        while downward[-1] != goal:
            downward.append(parent_b[downward[-1]])

        edges: list[tuple[int, int]] = list(itertools.pairwise(upward))
        edges.extend(itertools.pairwise(downward))
        sequence = [start]
        for edge in edges:
            for original in self.expand(edge):
                sequence.append(original[1])
        return CHPath(
            cost=best,
            nodes=[self.ids[node] for node in sequence],
            settled=settled,
            settle_order=tuple(settle_order),
        )


def preprocess(
    graph: StreetGraph,
    *,
    objective: Objective = "time",
    settle_limit: int = DEFAULT_SETTLE_LIMIT,
    witness_hops: int = DEFAULT_WITNESS_HOPS,
    verbose: bool = False,
) -> CHGraph:
    """Build the hierarchy. Deterministic for a given graph, objective and limit."""
    started = time.perf_counter_ns()
    started_seconds = time.perf_counter()
    ids = tuple(sorted(graph.nodes))
    index = {node: position for position, node in enumerate(ids)}
    size = len(ids)
    out: list[dict[int, float]] = [{} for _ in range(size)]
    incoming: list[dict[int, float]] = [{} for _ in range(size)]
    original_edges = 0
    for node_id, edges in graph.adjacency.items():
        source = index[node_id]
        for edge in edges:
            target = index[edge.to_node]
            weight = edge_weight(edge, objective)
            if target not in out[source] or weight < out[source][target]:
                out[source][target] = weight
                incoming[target][source] = weight
                original_edges += 1

    children: dict[tuple[int, int], tuple[tuple[int, int], tuple[int, int]]] = {}
    active = bytearray(b"\x01") * size

    def witness(source: int, target: int, cutoff: float, banned: int) -> bool:
        """Hop-bounded, cost-pruned search: is there a short witness avoiding ``banned``?"""
        if source == target:
            return True
        best: dict[int, tuple[float, int]] = {source: (0.0, 0)}
        heap: list[tuple[float, int, int]] = [(0.0, 0, source)]
        settles = 0
        while heap:
            cost, hops, node = heapq.heappop(heap)
            if node == target:
                return True
            settles += 1
            if settles > settle_limit or hops >= witness_hops:
                continue
            for neighbour, weight in out[node].items():
                if neighbour == banned:
                    continue
                candidate = cost + weight
                if candidate > cutoff:
                    continue
                previous = best.get(neighbour)
                if previous is not None and previous[0] <= candidate and previous[1] <= hops + 1:
                    continue
                best[neighbour] = (candidate, hops + 1)
                heapq.heappush(heap, (candidate, hops + 1, neighbour))
        return False

    def shortcuts_for(node: int) -> list[tuple[int, int, float]]:
        """Shortcuts a contraction would add, after witness checks."""
        added: list[tuple[int, int, float]] = []
        for source, weight_in in incoming[node].items():
            for target, weight_out in out[node].items():
                if source == target:
                    continue
                cost = weight_in + weight_out
                direct = out[source].get(target)
                if direct is not None and direct <= cost:
                    continue
                if witness(source, target, cost, node):
                    continue
                added.append((source, target, cost))
        return added

    def priority(node: int) -> int:
        """Edge-difference estimate *without* witness searches.

        Ordering does not affect correctness, only the shortcut count, and a
        full witness pass per queue probe dominates preprocessing cost in pure
        Python. The estimate keeps the order useful at a fraction of the price;
        the real witness checks happen once, when the node is contracted.
        """
        estimate = 0
        for source, weight_in in incoming[node].items():
            for target, weight_out in out[node].items():
                if source == target:
                    continue
                direct = out[source].get(target)
                if direct is None or direct > weight_in + weight_out:
                    estimate += 1
        return estimate - (len(incoming[node]) + len(out[node]))

    queue: list[tuple[int, int]] = []
    for node in range(size):
        heapq.heappush(queue, (priority(node), node))

    levels = [-1] * size
    up_forward: list[list[tuple[int, float]]] = [[] for _ in range(size)]
    up_backward: list[list[tuple[int, float]]] = [[] for _ in range(size)]
    level = 0
    while queue:
        recorded, node = heapq.heappop(queue)
        if not active[node]:
            continue
        current = priority(node)
        if current > recorded:
            heapq.heappush(queue, (current, node))
            continue
        for source, target, cost in shortcuts_for(node):
            if cost < out[source].get(target, float("inf")):
                out[source][target] = cost
                incoming[target][source] = cost
                children[(source, target)] = ((source, node), (node, target))
        # Capture the upward edges before the node leaves the working graph.
        for source, weight in incoming[node].items():
            up_backward[node].append((source, weight))
        for target, weight in out[node].items():
            up_forward[node].append((target, weight))
        for source in incoming[node]:
            del out[source][node]
        for target in out[node]:
            del incoming[target][node]
        incoming[node].clear()
        out[node].clear()
        levels[node] = level
        level += 1
        active[node] = 0
        if verbose and level % 5000 == 0:
            print(
                f"  contracted {level:,}/{size:,} nodes · {len(children):,} shortcuts "
                f"· {time.perf_counter() - started_seconds:.0f}s",
                flush=True,
            )

    assert all(value >= 0 for value in levels), "every node must be contracted"
    stats = CHStats(
        nodes=size,
        original_edges=original_edges,
        shortcuts=len(children),
        settle_limit=settle_limit,
        witness_hops=witness_hops,
        preprocessing_time_ns=time.perf_counter_ns() - started,
    )
    return CHGraph(
        ids=ids,
        index=index,
        levels=tuple(levels),
        up_forward=tuple(tuple(edges) for edges in up_forward),
        up_backward=tuple(tuple(edges) for edges in up_backward),
        children=children,
        stats=stats,
    )
