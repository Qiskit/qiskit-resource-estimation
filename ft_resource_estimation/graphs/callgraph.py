# Copyright IBM 2025

"""A call graph representation of a quantum circuit."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

from rustworkx import PyDiGraph
from qiskit.circuit import QuantumCircuit

from .nodes import Sentinel, Node, InstructionNode
from .metrics import Metric, Value

if TYPE_CHECKING:
    from ..error_models.error_model import ErrorModel

# constant number of flamegraph samples to distribute
NUM_SAMPLES = 10_000


class CallGraph:
    """A call graph representation of a quantum circuit."""

    def __init__(self, operation: Node):
        self._graph = PyDiGraph()
        self._root = self._graph.add_node(operation)
        self._unroll_node(self._root, operation)

    @classmethod
    def from_circuit(cls, circuit: QuantumCircuit) -> CallGraph:
        """Construct a CallGraph from a Qiskit QuantumCircuit."""
        instance = cls.__new__(cls)
        instance._graph = PyDiGraph()
        instance._root = instance._graph.add_node(Sentinel(circuit.name))

        operations: dict[InstructionNode, int] = {}
        for circuit_inst in circuit.data:
            node = InstructionNode(circuit_inst.operation)
            operations[node] = operations.get(node, 0) + 1

        for node, count in operations.items():
            node_id = instance._graph.add_child(instance._root, node, count)
            instance._unroll_node(node_id, node)

        return instance

    def _unroll_node(self, node_id, node):
        if (operations := node.operations()) is None:
            return

        for child, count in operations.items():
            child_id = self._graph.add_child(node_id, child, count)
            self._unroll_node(child_id, child)

    def count(self, name: str) -> int:
        """Count the number of operations.

        Args:
            name: The name of the operation.

        Returns:
            How many times the operation occurs.
        """
        indices = self._graph.filter_nodes(lambda node: node.name() == name)
        return sum(self._path_cost(index) for index in indices)

    def count_basis(
        self, basis: list[str] | None = None, allow_incomplete_basis: bool = True
    ) -> dict[Node, int]:
        """Unroll the operations, keeping count of how often operations appear.

        Args:
            basis: These operations are not unrolled further.
            allow_incomplete_basis: If ``False``, this method will fail if it cannot unroll the
                graph to the target basis. If ``True`` it will simply return the most basic
                nodes.

        Returns:
            A dictionary with ``{node: #ops}`` pairs.
        """
        if self._root is None:
            raise RuntimeError("Graph seems to be empty!")

        if basis is None:
            basis = []
        else:
            # make name checking case insensitive
            basis = list(name.lower() for name in basis)

        nodes = self._graph.nodes()
        to_visit = {self._root}
        counts = {}
        while len(to_visit) > 0:
            node_id = to_visit.pop()
            node = nodes[node_id]

            if node.name().lower() in basis:
                counts[node] = counts.get(node, 0) + self._path_cost(node_id)
            else:
                children = set(self._graph.successor_indices(node_id))
                if len(children) == 0:
                    if not allow_incomplete_basis:
                        raise RuntimeError(f"Couldn't unroll node: {node} to basis: {basis}")
                    counts[node] = counts.get(node, 0) + self._path_cost(node_id)
                else:
                    to_visit |= children

        return counts

    def estimate(
        self,
        basis: list[str] | None = None,
        error_models: dict[type[Node], "ErrorModel[Any]"] | None = None,
    ) -> dict[Metric, Value]:
        """Estimate metrics by accumulating over all basis nodes.

        For each node, metrics are sourced from two places and merged:
        - ``node.metrics()`` — metrics the node declares itself
        - the first error model whose ``supports(node)`` returns True

        When both sources define the same metric key, the error model's value takes precedence.
        Metrics are then scaled by the node's repetition count and accumulated across all nodes.

        Args:
            basis: Nodes to stop unrolling at (passed to ``count_basis``). If ``None``, the
                graph is fully unrolled to the terminal leafs.
            error_models: A mapping from node type to error model. The first model whose
                ``supports(node)`` returns True is used; keys communicate intent but are not
                used for lookup.

        Returns:
            A dictionary mapping each metric to its accumulated value.
        """
        counts = self.count_basis(basis)
        totals: dict[Metric, Value] = {}
        error_models = error_models or {}

        for node, count in counts.items():
            node_metrics = node.metrics() or {}
            em = next((m for m in error_models.values() if m.supports(node)), None)
            em_metrics = em.evaluate(node) if em is not None else {}

            # merge: error model overwrites node value for same key; disjoint keys kept
            merged = {**node_metrics, **em_metrics}

            # scale by count and fold into running totals
            for metric, value in merged.items():
                scaled = metric.repeat(value, count)
                totals[metric] = (
                    metric.combine(totals[metric], scaled) if metric in totals else scaled
                )

        return totals

    def dump_flamegraph(
        self,
        filename: str,
        metric: Metric,
        basis: list[str] | None = None,
        allow_incomplete_basis: bool = True,
        error_models: dict[type[Node], "ErrorModel[Any]"] | None = None,
        overwrite: bool = False,
    ):
        if self._root is None:
            raise RuntimeError("Graph seems to be empty!")

        if basis is None:
            basis = []
        else:
            # make name checking case insensitive
            basis = list(name.lower() for name in basis)

        nodes = self._graph.nodes()
        to_visit = {self._root}
        leafs = []  # list of all the final nodes -- this shouldn't use Hash-based containers

        while len(to_visit) > 0:
            node_idx = to_visit.pop()
            self._graph.successor_indices(node_idx)
            node = nodes[node_idx]

            if node.name().lower() in basis:
                print(f"node.name() ({node.name().lower()}) is in basis {basis}")
                leafs.append(node_idx)
            else:
                print(f"node.name() ({node.name().lower()}) is not in")
                children = set(self._graph.successor_indices(node_idx))

                if len(children) == 0:
                    if not allow_incomplete_basis:
                        raise RuntimeError(f"Couldn't unroll node: {node} to basis: {basis}")
                    leafs.append(node_idx)
                else:
                    to_visit |= children

        nodes = self._graph.nodes()
        all_values = [
            metric.repeat(
                _eval_metric_on_node(nodes[node_idx], metric, error_models),
                self._path_cost(node_idx),
            )
            for node_idx in leafs
        ]
        samples = metric.values_to_samples(all_values, num_samples=NUM_SAMPLES)

        fmode = "w" if overwrite else "x"
        with open(filename, fmode) as fhandle:
            for num_samples, node in zip(samples, leafs):
                ancestry, multiplicity = self._get_ancestry(node, with_counts=True)

                # format the flamegraph string, which has the form
                # root; leaf1; leaf2; final_leaf cost
                # we're labeling the leafs with "<name>(<count> x)" to include the count in the flamegraph
                fmt = "; ".join(
                    f"{ancestor.name()}({mult}x)"
                    for ancestor, mult in zip(ancestry[::-1], multiplicity[::-1])
                )
                fmt += f" {num_samples}\n"
                fhandle.write(fmt)

        print(f"Wrote to {filename}.")

    def _path_cost(self, index: int) -> int:
        prod = 1
        while len(parent := self._graph.predecessor_indices(index)) > 0:
            if len(parent) != 1:
                raise RuntimeError(f"Expected exactly one parent, got {len(parent)}")
            prod *= self._graph.get_edge_data(parent[0], index)
            index = parent[0]

        return prod

    def _get_ancestry(
        self, node_idx: int, with_counts: bool = False
    ) -> list[Node] | tuple[list[Node], list[int]]:
        """Get the ancestors of the node.

        This is formatted as ``[node, ancestor1, ancestor2, ..., root]``. In particular, the
        node itself is included as first element.
        """
        index_to_node = dict(enumerate(self._graph.nodes()))
        print(index_to_node)

        history = [index_to_node[node_idx]]
        counts = []
        current_idx = node_idx

        while current_idx != self._root:
            ancestor_idx = self._graph.predecessor_indices(current_idx)
            if len(ancestor_idx) != 1:
                raise RuntimeError("Each node should have exactly 1 ancestor!")
            ancestor_idx = ancestor_idx[0]

            history.append(index_to_node[ancestor_idx])
            counts.append(self._graph.get_edge_data(ancestor_idx, current_idx))

            current_idx = ancestor_idx

        counts.append(1)  # root appears once

        if with_counts:
            return history, counts
        return history


def _eval_metric_on_node(
    node: Node, metric: Metric, error_models: dict[type[Node], "ErrorModel[Any]"] | None = None
) -> Value:
    value = None
    if error_models is not None:
        if (em := error_models.get(type(node))) is not None:
            if metric in (metrics := em.evaluate(node)):
                value = metrics[metric]
    if value is None:
        if metric in (metrics := node.metrics()):
            value = metrics[metric]
        else:
            raise RuntimeError(f"Unable to query {metric} for node {node}.")

    return value
