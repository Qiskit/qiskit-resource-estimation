# Copyright IBM 2026

from collections.abc import Callable
import numpy as np
import matplotlib.pyplot as plt

from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import SparseObservable
from qiskit.transpiler import generate_preset_clifford_t_pass_manager

from qiskit_resource_estimation.graphs import CallGraph, InstructionNode, Node
from qiskit_resource_estimation.error_models import TwoGrossErrorModel, ErrorModel
from qiskit_resource_estimation.topologies import Linear
from qiskit_resource_estimation.error_models.bicycle.routing import TeleportationRouting
from qiskit_resource_estimation.graphs.metrics import Fidelity, AdditiveMetric
from qiskit_resource_estimation.topologies.topology import Allocation

COUPLING_CONST = 0.5
FIELD_CONST = 1.0


class RZCount(AdditiveMetric): ...


class CountRotations(ErrorModel):
    def supports(self, node):
        return isinstance(node, InstructionNode)

    def evaluate(self, node):
        match node.name():
            case "rx" | "ry" | "rz" | "u1" | "p" | "rxx" | "ryy" | "rzz" | "rzx":
                return {RZCount(): 1}
            case "u" | "u3":
                return {RZCount(): 3}
            case _:
                raise TypeError(f"Unsupported node in rotation count: {node.name}")


class Trotter(Node):
    def __init__(self, hamiltonian, time, num_steps):
        evo = PauliEvolutionGate(hamiltonian, time / num_steps)
        self.evo_node = InstructionNode(evo)
        self.num_steps = num_steps

    def num_qubits(self):
        return self.evo_node.num_qubits

    def name(self):
        return "Trotter"

    def __hash__(self):
        return hash(("Trotter", hash(self.evo_node), self.num_steps))

    def operations(self):
        return {self.evo_node: self.num_steps}


def build_ising_hamiltonian(num_qubits: int) -> SparseObservable:
    return SparseObservable.from_sparse_list(
        [("ZZ", [i, i + 1], COUPLING_CONST) for i in range(num_qubits - 1)]
        + [("X", [i], FIELD_CONST) for i in range(num_qubits)],
        num_qubits=num_qubits,
    )


def ising_hamiltonian_trotter_error(num_qubits: int, num_steps: int, time: float):
    heuristic_const = 2 / 3
    bound = time**2 / num_steps * 2 * (num_qubits - 1) * COUPLING_CONST * FIELD_CONST
    return heuristic_const * bound


def evaluate_metrics(graph: CallGraph, num_qubits: int, rz_error: float) -> float:
    pm = generate_preset_clifford_t_pass_manager(
        rz_synthesis_config={"rz_synthesis_error": rz_error / 2, "rz_cache_error": rz_error / 2}
    )

    topo = Linear(num_modules=num_qubits // 11 + 1)
    routing = TeleportationRouting(allocation=Allocation.AVG)
    error_model = TwoGrossErrorModel(topology=topo, p=4, routing=routing, pass_manager=pm)

    basis = ["rx", "rzz"]

    # build the call graph and estimate metrics
    metrics = graph.estimate(
        basis=basis,
        error_models=[error_model, CountRotations()],
    )

    return metrics[Fidelity()], metrics[RZCount()]


def get_cost_function(num_qubits: int) -> Callable:
    hamiltonian = build_ising_hamiltonian(num_qubits)

    def cost_function(x: tuple[int, float]) -> float:
        trotter_steps = int(x[0])
        rz_error = x[1]

        root = Trotter(hamiltonian, time=1.0, num_steps=trotter_steps)
        graph = CallGraph(root)

        fid, rz_count = evaluate_metrics(graph, hamiltonian.num_qubits, rz_error)
        rz_fid = norm_to_fid(rz_error) ** rz_count
        trotter_fid = norm_to_fid(
            ising_hamiltonian_trotter_error(num_qubits, trotter_steps, time=1.0)
        )

        return float(fid * rz_fid * trotter_fid)

    return cost_function


def norm_to_fid(value: float) -> float:
    """Turn the operator norm into a lower bound for the fidelity."""
    return max(0, 1 - 2 * value)


def plot():
    num_qubits = 100
    cost_fn = get_cost_function(num_qubits)

    steps = np.arange(10_000, 100_000, 1_000)
    rz_errors = 10 ** np.linspace(-22, -15, num=50)

    steps_dep = [cost_fn([n, 1e-10]) for n in steps]
    rz_dep = [cost_fn([1000, rz_error]) for rz_error in rz_errors]

    _, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.set_title("Fidelity vs. Trotter steps")
    ax1.plot(steps, steps_dep, c="royalblue", label="f(n, eps=1e-10)")
    ax1.set_xlabel("Trotter steps")
    ax1.set_ylabel("Fidelity")
    ax1.legend()

    ax2.set_title("Fidelity vs. RZ error")
    ax2.semilogx(rz_errors, rz_dep, c="seagreen", label="f(n=10, eps)")
    ax2.set_xlabel(r"RZ error $\varepsilon$")
    ax2.set_ylabel("Fidelity")
    ax2.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot()
