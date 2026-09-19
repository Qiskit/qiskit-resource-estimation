
# Qiskit resource estimation

> [!NOTE]
> This repository is under active development and the code here should not be considered stable.

Qiskit resource estimation provides an extensible framework for fast, approximative resource estimation for fault-tolerant programs, without full compilation. The main design principle is being extensible in both program building blocks
(or `Node`s) and target metrics that can be tracked.

We do, however, provide a [Qiskit](https://github.com/Qiskit/qiskit)-compatible error model for [Gross-codes](https://arxiv.org/abs/2506.03094) out of the box. This allows to take your existing Qiskit programs and easily obtain first estimations:
```python
from qiskit import QuantumCircuit
from qiskit.circuit.library import phase_estimation, RZGate

from qiskit_resource_estimation.graphs import CallGraph, InstructionNode
from qiskit_resource_estimation.graphs.metrics import Fidelity
from qiskit_resource_estimation.error_models import GrossErrorModel
from qiskit_resource_estimation.topologies import Linear

# Start from your Qiskit circuit
circuit = phase_estimation(50, RZGate(0.2))

# 1. Build a call graph from a Qiskit gate
graph = CallGraph.from_circuit(circuit)

# 2. Define the hardware
topo = Linear(num_modules=circuit.num_qubits // 11 + 1)
error_model = GrossErrorModel(topology=topo, p=3)  # p=3 → physical error rate 1e-3

# 3. Estimate metrics
metrics = graph.estimate(error_models={InstructionNode: error_model})
print("Fidelity:", metrics[Fidelity()])
```

## Purpose (and non-goals)

The purpose of this package is to provide an extensible framework for resource estimations.
The program is represented in a `CallGraph` datastructure with the abstractions
* `Node` - a node in callgraph, extensible to custom objects (block encodings, oracles, ...)
* `ErrorModel` - an error model taking a `Node` and returning a dictionary of `{Metric: Value}` 

The `CallGraph` can then accumulate metrics across the nodes. See for
example the `CallGraph.estimate` method to estimate the metrics and the 
`CallGraph.dump_flamegraph` method to generate a flamegraph for the program.

This package is _not_ providing a program description language (`Node`s can be backed by 
arbitrary objects, e.g. by Qiskit circuits) and is not building a compiler (but the `ErrorModel` 
allows to plug-in arbitrary compilers).

## Installation

Simply 
```bash
pip install -e .
```

## Code structure

The library has two layers: a **generic graph layer** that is independent of Qiskit and any specific error model, and a **built-in bicycle-code layer** on top.

### The call graph

The core data structure is a `CallGraph`: a directed acyclic graph (backed by `rustworkx`) where nodes represent types of quantum operations and edge weights are integer repetition counts.

```
QFT(20) ─── H x 20
      └── CPhase x 190
```

This hierarchical representation lets you count operations at any level of abstraction without simulating the circuit.

```python
# Count all basis gates (unroll everything)
counts = graph.count_basis()

# Stop unrolling at a specific gate set
counts = graph.count_basis(basis=["cp", "h", "cx"])

# Count a single gate type anywhere in the hierarchy
n_hadamards = graph.count("h")
```

`CallGraph.estimate()` unrolls to the basis and accumulates metrics across all leaf nodes:

```python
metrics = graph.estimate(
    basis=["ccx", "mcx"],
    error_models={InstructionNode: error_model},
)
```

### Nodes

`Node` is the abstract interface every operation must implement:

| Method | Purpose |
|--------|---------|
| `name() -> str` | Gate name used for basis matching |
| `num_qubits() -> int` | Number of logical qubits |
| `operations() -> dict[Node, int] \| None` | Decomposition into child operations; `None` for leaf nodes |
| `metrics() -> dict[Metric, Value] \| None` | Optional per-node resource contributions |

**`InstructionNode`** wraps any Qiskit `Instruction`. Its `operations()` reads the gate's `.definition` circuit automatically, so the entire Qiskit gate library is available out of the box.

```python
from qiskit.circuit.library import MCXGate
node = InstructionNode(MCXGate(5))
graph = CallGraph(node)
```

### Metrics

`Metric` is an abstract class that defines how a resource quantity accumulates across nodes:

```python
class Metric(ABC):
    def combine(self, a, b): ...   # how to merge two values (e.g. multiply, add)
    def repeat(self, v, n): ...    # how to scale by repetition count (e.g. v^n, v*n)
    def identity(self): ...        # neutral element
```

You can define entirely custom metrics by subclassing `Metric` and returning them from `node.metrics()`, with no dependency on Qiskit or any error model.

### Error models and topology

An `ErrorModel[N]` maps a node to metric values:

```python
class ErrorModel(ABC, Generic[N]):
    def supports(self, node: Node) -> bool: ...
    def evaluate(self, node: N) -> dict[Metric, Value]: ...
```

The built-in `GrossErrorModel` implement the Gross-code bicycle ISA.

## Examples

### [`examples/callgraph_example.py`](examples/callgraph_example.py)

Demonstrates both usage modes: building a call graph from a Qiskit circuit and directly from a library node (`Add`). Shows `count_basis()` at different levels of unrolling.

### [`examples/qpe.py`](examples/qpe.py)

Quantum phase estimation on a 100-qubit Heisenberg Hamiltonian. Illustrates how to set a `basis` to stop unrolling at `PauliEvolution` gates and how to inspect the per-metric breakdown.
