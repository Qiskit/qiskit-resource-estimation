# Copyright IBM 2025.

"""A call graph representation of a quantum circuit."""

from __future__ import annotations
from qiskit.circuit import QuantumCircuit, Instruction
from rustworkx import PyDiGraph  # pylint: disable=no-name-in-module

from .nodes import Sentinel, Node


class CallGraph:
    """A call graph representation of a quantum circuit."""

    # todo add decomposer, which should also allow setting the target basis?
    def __init__(self, operation: QuantumCircuit | Instruction):
        self._graph = PyDiGraph()

        if isinstance(operation, QuantumCircuit):
            self._init_circuit(operation)

        elif isinstance(operation, Instruction):
            node = Node(operation)
            self._root = self._graph.add_node(node)
            self._unroll_node(self._root, node)

        else:
            raise TypeError(f"operation of type {type(operation)} are not supported")

    def _init_circuit(self, circuit: QuantumCircuit):
        self._root = self._graph.add_node(Sentinel(circuit.name))

        operations = {}
        for circuit_inst in circuit.data:
            node = Node(circuit_inst.operation)
            operations[node] = operations.get(node, 0) + 1

        for node, count in operations.items():
            node_id = self._graph.add_child(self._root, node, count)
            self._unroll_node(node_id, node)

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

            # we count the node either if it's in the target basis or if we can no longer unroll
            if node.name().lower() in basis:
                count_node = True
                children = None
            else:
                children = set(self._graph.successor_indices(node_id))
                # if we can't decompose it, count it (unless the user told us to raise an error)
                if len(children) == 0:
                    if not allow_incomplete_basis:
                        raise RuntimeError(f"Couldn't unroll node: {node} to basis: {basis}")
                    count_node = True
                # if we can decompose it, do so
                else:
                    count_node = False

            if count_node:
                # found a target, count it -- this could probably be done more efficiently
                # by keeping track of the current cost, but I'm out of time and need to go to Italy
                counts[node] = counts.get(node, 0) + self._path_cost(node_id)
            else:
                # otherwise update the list to visit
                to_visit |= children

        return counts

    def _path_cost(self, index: int) -> int:
        prod = 1
        while len(parent := self._graph.predecessor_indices(index)) > 0:
            assert len(parent) == 1, "something really went wrong"
            prod *= self._graph.get_edge_data(parent[0], index)
            index = parent[0]

        return prod
