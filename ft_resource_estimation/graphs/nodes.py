# Copyright IBM 2025

"""Nodes for the call graph."""

from __future__ import annotations
from abc import abstractmethod, ABC
from enum import Enum

import numpy as np
from qiskit.circuit import Instruction, ParameterExpression

from .metrics import Metric, Value

ROTATIONS = {"rx", "ry", "rz", "rzz", "ryy", "rxx", "rzx", "p", "pauli_product_rotation"}


class AngleClass(Enum):
    """Represents different angle classes that are important to resource estimations."""

    PAULI = 0
    CLIFFORD = 1
    T = 2
    ROTATION = 3


def _is_multiple_of_pi_k(angle: float, k: int) -> bool:
    modulo = angle * k / np.pi
    remainder = modulo % 1.0
    return np.isclose(remainder, 0) or np.isclose(remainder, 1)


def get_angle_class(angle: float) -> AngleClass:
    """Classify a rotation angle into the fidelity-relevant bucket it belongs to."""
    if _is_multiple_of_pi_k(angle, 1):
        return AngleClass.PAULI
    if _is_multiple_of_pi_k(angle, 2):
        return AngleClass.CLIFFORD
    if _is_multiple_of_pi_k(angle, 4):
        return AngleClass.T
    return AngleClass.ROTATION


def _param_key(instruction: Instruction) -> tuple | None:
    """Return a hashable key for an instruction's angle class, or None if not applicable.

    Only single-angle gates (see `_SINGLE_ANGLE_GATES`/`_PAULI_ANGLE_GATES`) are classified;
    other gates keep today's shape-only identity. Unbound parameters (`ParameterExpression`)
    can't be classified either, so they also fall back to `None`.
    """
    name = instruction.name
    if name in ROTATIONS:
        angle = instruction.params[0]
    elif name == "PauliEvolution":
        angle = instruction.params[0] / 2
    else:
        return None

    if isinstance(angle, ParameterExpression):
        return None
    return (get_angle_class(angle),)


class Node(ABC):
    """The node interface.

    Requires hash to be implemented, such that the nodes can be used as dictionary keys
    for resource counts.
    """

    @abstractmethod
    def __hash__(self): ...

    @abstractmethod
    def name(self) -> str:
        """Return the name of the node."""
        ...

    @abstractmethod
    def num_qubits(self) -> int:
        """Return the number of logical qubits."""
        ...

    def __eq__(self, other):
        return hash(self) == hash(other)

    @abstractmethod
    def operations(self) -> dict[Node, int] | None:
        """Get the operation counts."""
        ...

    def metrics(self) -> dict[Metric, Value] | None:
        """Get the node's custom metrics, if available."""
        return None

    def __repr__(self) -> str:
        return f"{self.name()}({self.num_qubits()})"


class Sentinel(Node):
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

    def __repr__(self) -> str:
        return f"{self.name()} (sentinel)"


class InstructionNode(Node):
    """A node backed by a Qiskit ``Instruction``.

    Supports two usage modes:

    1. **Wrapper mode**: ``InstructionNode(gate)`` — wraps an existing Qiskit instruction.
       ``name()``, ``num_qubits()``, and ``operations()`` delegate to the wrapped instruction.

    2. **Subclass mode**: subclass ``InstructionNode`` directly (e.g. library gates like
       ``Add`` or ``AQFT``). Call ``super().__init__()`` with no argument and override
       ``name()``, ``num_qubits()``, ``operations()``, and ``__hash__()`` directly.
    """

    def __init__(self, instruction: Instruction | None = None):
        super().__init__()
        self._inst = instruction

    @property
    def instruction(self):
        return self._inst

    def name(self) -> str:
        if self._inst is None:
            raise TypeError(
                f"{type(self).__name__} has no instruction. " "Override this method in a subclass."
            )
        return self._inst.name

    def num_qubits(self) -> int:
        if self._inst is None:
            raise TypeError(
                f"{type(self).__name__} has no instruction. " "Override this method in a subclass."
            )
        return self._inst.num_qubits

    def __hash__(self) -> int:
        if self._inst is None:
            raise TypeError(
                f"{type(self).__name__} has no instruction. " "Override this method in a subclass."
            )
        return hash(
            (self._inst.name, self._inst.num_qubits, self._inst.num_clbits, _param_key(self._inst))
        )

    def operations(self) -> dict[Node, int] | None:
        if self._inst is None:
            raise TypeError(
                f"{type(self).__name__} has no instruction. " "Override this method in a subclass."
            )
        if (circuit := self._inst.definition) is None:
            return None

        out: dict[Node, int] = {}
        for circuit_inst in circuit.data:
            as_node = InstructionNode(circuit_inst.operation)
            out[as_node] = out.get(as_node, 0) + 1

        return out
