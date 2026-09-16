# Copyright IBM 2026

"""Tests that InstructionNode hashing distinguishes gates by fidelity-relevant angle class.

Two same-shape gates (same name/num_qubits/num_clbits) with angles that fall into
different classes (Pauli/Clifford/T/Rotation, see graphs/nodes.py:angle_class) must not
be treated as the same node -- otherwise CallGraph.estimate()'s count_basis() grouping
silently evaluates one gate's fidelity and applies it to both (see test_bicycle_error_model.py
for the end-to-end regression test this bug would otherwise cause).
"""

import unittest
import numpy as np
from qiskit.circuit.library import RZGate, CXGate

from qiskit_resource_estimation.graphs.nodes import InstructionNode


class TestInstructionNodeAngleHashing(unittest.TestCase):
    def test_same_angle_class_hashes_equal(self):
        """Two Clifford-class rz angles must hash/compare equal."""
        a = InstructionNode(RZGate(np.pi / 2))
        b = InstructionNode(RZGate(3 * np.pi / 2))
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)

    def test_different_angle_class_hashes_unequal(self):
        """A Clifford-class angle and a Rotation-class angle must not collide."""
        clifford = InstructionNode(RZGate(np.pi / 2))
        rotation = InstructionNode(RZGate(np.pi / 8))
        self.assertNotEqual(hash(clifford), hash(rotation))
        self.assertNotEqual(clifford, rotation)

    def test_pauli_vs_t_class(self):
        pauli = InstructionNode(RZGate(np.pi))
        t = InstructionNode(RZGate(np.pi / 4))
        self.assertNotEqual(hash(pauli), hash(t))
        self.assertNotEqual(pauli, t)

    def test_unparameterized_gate_unaffected(self):
        """Gates outside the classified set (e.g. cx) keep shape-only identity."""
        a = InstructionNode(CXGate())
        b = InstructionNode(CXGate())
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
