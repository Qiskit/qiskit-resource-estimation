# Copyright IBM 2025.

"""Example algorithm circuits for the Litinski experiments."""

import numpy as np

from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import (
    PauliEvolutionGate,
    phase_estimation,
    qaoa_ansatz,
    grover_operator,
    LinearPauliRotationsGate,
)
from qiskit.quantum_info import SparseObservable, SparsePauliOp


def aqft(n):
    threshold = int(np.ceil(np.log2(n))) - 1
    qc = QuantumCircuit(n)
    # random placeholder circuit
    for i in range(n):
        qc.h(n - 1 - i)
        for j in range(i + 1, min(n, i + 1 + threshold)):
            qc.cp(3 + i / n, n - 1 - j, n - 1 - i)

    return qc


def grover(num_qubits: int) -> QuantumCircuit:
    state_qubits = list(range(num_qubits - 1))
    target_qubit = num_qubits - 1

    # state preparation: prob dist + function applied on the values
    state_prep = QuantumCircuit(num_qubits)
    state_prep.h(state_qubits)  # could replace this by a probability distribution
    func = LinearPauliRotationsGate(num_qubits - 1, slope=0.2, offset=1)
    state_prep.append(func, state_qubits + [target_qubit])

    # oracle: flip if target qubit is 1
    oracle = QuantumCircuit(num_qubits)
    oracle.z(target_qubit)

    # we could maybe set reflection_qubits=[target_qubit] too
    return grover_operator(oracle, state_preparation=state_prep)


def qaoa(num_qubits: int) -> QuantumCircuit:
    gen = np.random.default_rng(seed=24_122_025)
    obs = SparsePauliOp.from_sparse_list(
        [("ZZ", [i, j], gen.random()) for i in range(num_qubits - 1) for j in range(i)],
        num_qubits=num_qubits,
    )

    return qaoa_ansatz(obs, reps=10)


# define the Hamiltonian for QPE
def qpe(n):
    hamiltonian = SparseObservable.from_sparse_list(
        [(term, [i, i + 1], -1) for i in range(n - 1) for term in ["XX", "YY", "ZZ"]]
        + [("Z", [i], 0.5) for i in range(n)],
        num_qubits=n,
    )

    # build the unitary
    unitary = PauliEvolutionGate(hamiltonian, time=0.1)

    # define the initial state -- here we use a placeholder
    qc = QuantumCircuit(n)
    qc.x(range(0, n, 2))
    initial = qc.to_gate()

    # build the QPE circuit
    num_eval_qubits = 20
    circuit = QuantumCircuit(num_eval_qubits + n)

    qpe = phase_estimation(num_eval_qubits, unitary)
    circuit.append(initial, circuit.qubits[-n:])
    circuit.compose(qpe, inplace=True)

    return circuit
