# Copyright IBM 2025.

"""An adder."""

from __future__ import annotations

import numpy as np
from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.library import PhaseGate

from ft_resource_estimation.graphs.dictionary_instruction import DictionaryGate
from ft_resource_estimation.graphs.nodes import Node

from .aqft import AQFT


class Add(DictionaryGate):
    r"""Plain adder by a classical value :math:`k`.

    Implements the operation

    .. math::

        |y\rangle \mapsto |i\rangle |y + k \rangle.

    """

    def __init__(self, num_qubits: int, apply_qft: bool = True):
        self.apply_qft = apply_qft
        super().__init__(name="Add", num_qubits=num_qubits, params=[])

    def operations(self) -> dict[Node, int]:
        # These are the gates in the Add operation
        qft = AQFT(self.num_qubits)
        phase = PhaseGate(Parameter("x"))

        # In the dictionary, we wrap them in Node objects
        num_qft = 2 if self.apply_qft else 0
        operations = {Node(qft): num_qft, Node(phase): self.num_qubits}

        return operations

    def _define(self):
        """Draper QFT based implementation from https://arxiv.org/abs/quant-ph/0008033"""
        n = self.num_qubits
        # default decomposition circuit
        qc = QuantumCircuit(n, name=self.name)
        if self.apply_qft:
            qft = AQFT(n)
            qc.append(qft, list(range(n)))

        # in reality, the argument will depend also on k
        for i in range(n):
            phase = 1.1
            for j in range(i):
                phase += 1 / (2**j)
            qc.p(np.pi * phase, i)

        if self.apply_qft:
            qc.append(qft.inverse(), list(range(n)))

        self.definition = qc
