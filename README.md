# Resource estimation for FT programs

Fast resource estimation for fault-tolerant quantum circuits, without full compilation.

## Motivation

What algorithms can we hope to run on the fault-tolerant machines we are building?
What practical advantage does the Gross code have over the surface code in absolute numbers?
Which synthesis is optimal for my algorithm?
How low do physical error rates have to be to achieve a target accuracy?

These questions can be answered precisely — either by analytic derivation or by full compilation to the target architecture — but that can take hours to days.
We oftentimes do not need precise answers.
To gauge feasibility or compare methods, fast order-of-magnitude estimates are sufficient.

This tool is built for exactly that: **reliable enough for resource comparisons, fast enough to run on a laptop**.

## Goals and non-goals

**Goals** — provide a generic, pluggable framework to efficiently estimate:
1. The three FTQC ingredients: magic (T gates), entanglement (Clifford operations), and routing.
2. The estimated circuit fidelity on a given architecture.
3. The estimated runtime. (Not available yet)

The core abstractions (`Node`, `Metric`, `ErrorModel`, `BaseTopology`) make no assumptions about gate sets or hardware. Users can define their own node types, metrics, and error models without touching any Qiskit or bicycle-code code.
Qiskit circuits and the Gross-code bicycle ISA are built-in options, not requirements.

**Non-goals**
- We don't define a circuit description language: algorithms are expressed using whatever interface the user prefers.
- We don't build a Gross-code compiler: fidelity estimates are derived from lightweight ISA-level formulas, not full compilation.
- We don't compile the full circuit: for exact resource counts, use a full compiler such as Qiskit + the bicycle architecture compiler.

---

## Installation

```bash
pip install -e .
```

---

## Quick start

```python
from qiskit.circuit.library import QFTGate
from ft_resource_estimation.graphs import CallGraph, InstructionNode
from ft_resource_estimation.graphs.metrics import Fidelity
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.topologies import Linear

# 1. Build a call graph from a Qiskit gate
graph = CallGraph(InstructionNode(QFTGate(20)))

# 2. Define the hardware
topo = Linear(num_modules=2)
error_model = GrossErrorModel(topology=topo, p=3)  # p=3 → physical error rate 1e-3

# 3. Estimate metrics
metrics = graph.estimate(error_models={InstructionNode: error_model})
print("Fidelity:", metrics[Fidelity()])
```

---

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

**Subclassing** `InstructionNode` is how you add library gates with hand-written decompositions. The built-in library (`ft_resource_estimation/library/`) provides `AQFT` and `Add` as examples.

**Building a call graph from a circuit** uses `CallGraph.from_circuit(qc)`, which wraps each gate in the circuit as an `InstructionNode` and unrolls their definitions.

### Metrics

`Metric` is an abstract class that defines how a resource quantity accumulates across nodes:

```python
class Metric(ABC):
    def combine(self, a, b): ...   # how to merge two values (e.g. multiply, add)
    def repeat(self, v, n): ...    # how to scale by repetition count (e.g. v^n, v*n)
    def identity(self): ...        # neutral element
```

The library ships with:
- `Fidelity` — multiplicative (`combine = a*b`, `repeat = v^n`)
- `TCount` — additive (`combine = a+b`, `repeat = v*n`)
- `InFidelity`, `TFidelity`, `InterFidelity`, `RoutingFidelity` — fidelity breakdown components

You can define entirely custom metrics by subclassing `Metric` and returning them from `node.metrics()`, with no dependency on Qiskit or any error model.

### Error models and topology

An `ErrorModel[N]` maps a node to metric values:

```python
class ErrorModel(ABC, Generic[N]):
    def supports(self, node: Node) -> bool: ...
    def evaluate(self, node: N) -> dict[Metric, Value]: ...
```

The built-in `GrossErrorModel` (and its parent `BicycleErrorModel`) implement the Gross-code bicycle ISA:

1. **Routing**: the node is placed at its optimal topology location, and SWAP overhead is estimated from the average displacement.
2. **Compilation**: the gate is transpiled to the bicycle ISA (Cliffords + `rz` + `rzz`) using a Qiskit pass manager.
3. **Fidelity**: each ISA gate is scored by `gate_fidelity()`, which combines in-block measurement, automorphism, inter-block measurement, and T-injection error rates.

A `BaseTopology` describes the hardware layout:

```python
topo = Linear(num_modules=10)         # linear chain of bicycle code modules
topo = AllToAll(num_modules=10)       # all-to-all module connectivity
topo = Linear(num_modules=10, num_ancillas=5)  # reserve ancilla qubits for compilation
```

Each module contains 11 data qubits and 1 pivot qubit (12 total). `Linear` places the T factory at block 0 (the left end); `AllToAll` places a factory next to every module.

**Physical error rates** are set via `p`:
- `p=3` → physical error rate ~ 10⁻³
- `p=4` → physical error rate ~ 10⁻⁴

---

## Examples

### [`examples/callgraph_example.py`](examples/callgraph_example.py)

Demonstrates both usage modes: building a call graph from a Qiskit circuit and directly from a library node (`Add`). Shows `count_basis()` at different levels of unrolling.

### [`examples/qpe.py`](examples/qpe.py)

Quantum phase estimation on a 100-qubit Heisenberg Hamiltonian. Illustrates how to set a `basis` to stop unrolling at `PauliEvolution` gates and how to inspect the per-metric breakdown.

---

## Roadmap

### Research questions

1. **Examples** — simple: arithmetic (adders, multipliers), QPE, Grover, QAOA/Trotter; high-level: full algorithm demonstrations.
2. **Quality benchmarks** — compare against analytic numbers on a subset of examples.
3. **Error contributions** — what dominates: T-injection, entanglement, or routing? Does routing overhead matter more than placement?
4. **Comparison survey** — benchmark against Qualtran and Bartiq.
5. **Litinski pass** — run examples through the Litinski gate synthesis and compare fidelity.
6. **Functional fidelity representation** — express total fidelity as a function of individual error contributions.
7. **T factory layout** — dynamic vs. fixed; line vs. ladder vs. square allocation; optimal topology for a given algorithm.
