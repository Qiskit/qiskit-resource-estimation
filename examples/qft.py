# Copyright IBM 2025.

"""A QFT example."""

import numpy as np
from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import get_clifford_gate_names
from qiskit.transpiler.passes import CommutativeOptimization
from ft_resource_estimation.library.aqft import AQFT
from ft_resource_estimation.transformations import PBCTransformation


def count_t(circuit, t_thres=200):
    rot_count = sum(circuit.count_ops().get(name, 0) for name in ["rz", "rzz"])
    return rot_count * t_thres


def count_pauli(circuit, t_thres=200):
    count = 0
    for data in circuit.data:
        evo = data.operation
        angle = evo.time
        if np.isclose(angle % (np.pi / 2), 0):
            # is Pauli
            continue
        if np.isclose(angle % (np.pi / 4), 0):
            # is clifford
            continue

        count += 200

    return count


n = 100
node = AQFT(n)
cliffords = get_clifford_gate_names()

circuit = QuantumCircuit(node.num_qubits)
circuit.append(node, circuit.qubits)

tqc = transpile(circuit, basis_gates=cliffords + ["rz", "rzz"], approximation_degree=1)
tqc = CommutativeOptimization()(tqc)
print("RZ + RZZ optimization")
print(count_t(tqc))

tqc = transpile(circuit, basis_gates=cliffords + ["rz", "rzz", "p", "cp"], approximation_degree=1)
tqc = CommutativeOptimization()(tqc)
print("P + CP + RZ + RZZ decomp")
print(tqc.count_ops())

tqc = transpile(tqc, basis_gates=cliffords + ["rz", "rzz"])
# print(tqc.draw())
pbc = PBCTransformation()(tqc)
pbc = CommutativeOptimization()(pbc)
# print(pbc.draw())
print(pbc.count_ops())
print(count_pauli(pbc))

# for data in pbc.data:
#     evo = data.operation
#     print(evo.operator.paulis, evo.time)
