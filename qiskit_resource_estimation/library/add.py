# Copyright IBM 2025

"""An adder."""

from __future__ import annotations

import numpy as np
from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.library import PhaseGate

from qiskit_resource_estimation.graphs.nodes import InstructionNode, Node

from .aqft import AQFT


class Add(InstructionNode):
    r"""Plain adder by a classical value :math:`k`.

    Implements the operation

    .. math::

        |y\rangle \mapsto |i\rangle |y + k \rangle.

    """

    def __init__(self, num_qubits: int, apply_qft: bool = True):
        super().__init__()
        self._num_qubits = num_qubits
        self.apply_qft = apply_qft

    def name(self):
        return "Add"

    def num_qubits(self):
        return self._num_qubits

    def __hash__(self):
        return hash(("Add", self._num_qubits, self.apply_qft))

    def operations(self) -> dict[Node, int]:
        qft = AQFT(self._num_qubits)
        phase = InstructionNode(PhaseGate(Parameter("x")))

        num_qft = 2 if self.apply_qft else 0
        return {qft: num_qft, phase: self._num_qubits}

    def definition(self) -> QuantumCircuit:
        """Return the Qiskit circuit definition (Draper QFT-based adder)."""
        n = self._num_qubits
        qc = QuantumCircuit(n, name=self.name())

        qft = AQFT(n) if self.apply_qft else None

        if qft is not None:
            qc.append(qft.definition(), list(range(n)))

        for i in range(n):
            phase = 1.1
            for j in range(i):
                phase += 1 / (2**j)
            qc.p(np.pi * phase, i)

        if qft is not None:
            qc.append(qft.definition().inverse(), list(range(n)))

        return qc
