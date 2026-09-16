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

    def _path_cost(self, index: int) -> int:
        prod = 1
        while len(parent := self._graph.predecessor_indices(index)) > 0:
            if len(parent) != 1:
                raise RuntimeError(f"Expected exactly one parent, got {len(parent)}")
            prod *= self._graph.get_edge_data(parent[0], index)
            index = parent[0]

        return prod
