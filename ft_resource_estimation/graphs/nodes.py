# Copyright IBM 2025.

"""Nodes for the call graph."""

from __future__ import annotations
from abc import abstractmethod, ABC
from qiskit.circuit import Instruction
from .dictionary_instruction import DictionaryMixin


class BaseNode(ABC):
    """The node interface.

    Requires hash to be implemented, such that the nodes can be used as dictionary keys
    for resource counts.
    """

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError("Node needs __hash__ to be implemented.")

    @abstractmethod
    def name(self):
        """Return the name of the node."""
        raise NotImplementedError("Node needs a name!")

    @abstractmethod
    def num_qubits(self):
        """Return the number of logical qubits."""
        raise NotImplementedError("Node must be able to tell its number of qubits.")

    def __eq__(self, other):
        return hash(self) == hash(other)

    @abstractmethod
    def operations(self) -> dict[BaseNode, int]:
        """Get the operation counts."""
        raise NotImplementedError("Nodes must be provide their operations().")

    def __repr__(self) -> str:
        return f"{self.name()}({self.num_qubits()})"


class Sentinel(BaseNode):
    """A sentinel node without internal information.

    Used e.g. as root node when constructing from a circuit.
    """

    def __init__(self, name: str):
        super().__init__()
        self._name = name

    def name(self):
        return self._name

    def __hash__(self):
        return hash(self._name)

    def operations(self):
        raise RuntimeError("A Sentinel cannot be decomposed. This indicates a faulty graph.")

    def num_qubits(self):
        raise RuntimeError("A Sentinel cannot be decomposed. This indicates a faulty graph.")


class Node(BaseNode):
    """A node backed by a Qiskit ``Instruction``."""

    def __init__(self, instruction: Instruction):
        super().__init__()
        self._inst = instruction

    def name(self):
        return self._inst.name

    def num_qubits(self):
        return self._inst.num_qubits

    def __hash__(self):
        return hash((self._inst.name, self._inst.num_qubits, self._inst.num_clbits))

    def operations(self) -> dict[Node, int] | None:
        if isinstance(self._inst, DictionaryMixin):
            return self._inst.operations()

        if (circuit := self._inst.definition) is None:
            return None

        out = {}
        for circuit_inst in circuit.data:
            as_node = Node(circuit_inst.operation)
            out[as_node] = out.get(as_node, 0) + 1

        return out
