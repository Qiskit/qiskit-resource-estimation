# Copyright IBM 2025.

"""An example comparing costs with and without the Litinski transformation."""

from qiskit import transpile
from qiskit.transpiler.passes import LitinskiTransformation, CommutativeOptimization
import matplotlib.pyplot as plt

from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.error_models.error_model import GateType
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.target import Target, get_gate_type
from ft_resource_estimation.transformations.pbc_transformation import PBCTransformation

from circuits import grover


def count_locality(circuit):
    locality = {}

    for inst in circuit.data:
        op = inst.operation
        if inst.name == "PauliEvolution":
            term = op.operator[0]  # has only 1 term
            loc = len(term.bit_terms)
        elif inst.name == "pauli_product_measurement":
            label = op.pauli().to_label()
            loc = len(label) - label.count("I")
        else:
            loc = op.num_qubits

        locality[loc] = locality.get(loc, 0) + 1

    return locality


def estimate_fidelity(circuit, topology, errors):
    fid = 1
    indices = {qubit: index for index, qubit in enumerate(circuit.qubits)}

    for inst in circuit.data:
        qubits = [indices[q] for q in inst.qubits]
        locality = topology.locality(qubits)
        if len(qubits) == 1:
            num_blocks = 0
        else:
            num_blocks = topology.block_distance(min(qubits), max(qubits))  # HACK: min/max
        total_span = num_blocks
        # get the gate type (T, Pauli, Clifford, Rotation, Measure)
        gate_type = get_gate_type(inst)

        # for non-clifford gates the total span should take into account the distance to the nearest
        # factory
        if gate_type in {GateType.T, GateType.Rotation}:
            total_span += topology.magic_distance(max(qubits))  # HACK: max

        # finally add the errors arising from the inter block measurments
        fid *= errors.gate_fidelity(total_span, locality, gate_type)

    return fid


n = 100
# circuit = qpe(n)
circuit = grover(n)
# circuit = QuantumCircuit(n)
# circuit.x(0)
# circuit.compose(aqft(n), circuit.qubits, inplace=True)

# define the Target we compile to
error_model = GrossErrorModel(p=4)
topo = Linear(num_modules=n // 11 + 1)
target = Target(topo, error_model)

basis = ["rz"] + ["h", "s", "sx", "z", "y", "cx", "cz"]
copt = CommutativeOptimization()

# basis = ["rz"] + get_clifford_gate_names()
tqc = transpile(circuit, basis_gates=basis)
lit = LitinskiTransformation(fix_clifford=False)(tqc)

print("Litinski:")
print(lit.count_ops())
print(count_locality(lit))

pbc = PBCTransformation()(tqc)
print("Direct:")
print(pbc.count_ops())
print(count_locality(pbc))

print("Litinski + Gucci:")
lit_copt = copt(lit)
print(lit_copt.count_ops())
print(count_locality(lit_copt))
print(estimate_fidelity(lit_copt, topo, error_model))

print("Direct + Gucci:")
pbc_copt = copt(pbc)
print(pbc_copt.count_ops())
print(count_locality(pbc_copt))
print(estimate_fidelity(pbc_copt, topo, error_model))


def barplot(ax, locality, color, label, offset):
    ax.bar(
        [loc - 0.1 * offset for loc in locality.keys()],
        locality.values(),
        color=color,
        label=label,
        width=0.2,
    )


ax = plt.axes()
plt.grid()
plt.semilogy()
barplot(ax, count_locality(pbc_copt), color="crimson", label="Direct", offset=-1)
barplot(ax, count_locality(lit_copt), color="royalblue", label="Litinski", offset=1)
plt.xlabel("locality")
plt.ylabel("count")
plt.legend(loc="best")
plt.show()
