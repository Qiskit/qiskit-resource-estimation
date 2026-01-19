# Resource estimation

## Table of Contents

- [Resource estimation](#resource-estimation)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
    - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-goals](#non-goals)
    - [State of the art (as we know it)](#state-of-the-art-as-we-know-it)
  - [Design](#design)
    - [1. The call graph](#1-the-call-graph)
    - [2. Target](#2-target)
      - [Fidelity estimation](#fidelity-estimation)
      - [2.1. Topology](#21-topology)
      - [2.2. Error model](#22-error-model)
  - [Roadmap](#roadmap)
    - [Research questions](#research-questions)
    - [Software features](#software-features)

## Overview

### Motivation
What algorithms can we hope to run on the fault-tolerance machines we are building? What practical advantage does the Gross code have over the surface code in absolute numbers? Which synthesis is optimal for my algorithm? How low do the physical error rates have to be to achieve my target accuracy?

These questions can be answered precisely: either by analytic derivations or full compilation to the target architecture -- but this can take hours to days. Yet, we oftentimes do not require precise answers to these questions. To gauge whether an algorithm could be feasible on the planned hardware or to compare methods, we expect fast estimates to be sufficient.

Our motivation is to build precisely such a tool, which enables us to answer questions about our algorithms and architecture at a fast pace. Reliable enough for resource comparisons and order of magnitude estimates, and fast enough to perform large-scale comparisons.

### Goals

Build a tool that can **efficiently** estimate

1. the 3 FTQC ingredients: magic, entanglement, and routing,
2. the estimated error on given architecture, and
3. the estimated runtime,

-- while being pluggable: we can exchange building blocks easily, to see the impact on the different measures above.

### Non-goals

- We don't provide a new circuit interface (like Qube): we _use existing_ interfaces to construct circuits
- We don't build a Gross-code compiler: we obtain error and runtime estimates from existing compilers
- We don't compile the full circuit: we provide _fast resource estimates_ -- for full compilation use Qiskit + Bicycle Architecture compiler

### State of the art (as we know it)

| Tool                     | Pluggable | Fast estimates | Qiskit Integration | Supports routing   | Notes                                      |
|--------------------------|-----------|----------------|--------------------|--------------------|--------------------------------------------|
| **Qualtran**             | ✅        | ✅             | ❌                 | very crude         | Cannot account for topology                |
| **Qiskit**               | ✅        | ❌             | ✅                 | ✅                 | Gate-level compilation                     |
| **Qrisp**                | ❌        | n/a            | ?                  | ?                  | Too high level; not pluggable              |
| **QUBE**                 | ❌        | n/a            | ✅                 | n/a                | Interface for circuit building             |
| **this project**         | ✅        | ✅             | ✅                 | approximately      |                                            |


## Design
We have the following main components:
1. the call graph: a hierarchical representation of the circuit of interest
2. a target system consisting of:
   1. a topology 
   2. an error model to estimate error + runtime metrics

High-level example:
```python
from qiskit import QuantumCircuit
from qiskit.circuit.library import grover_operator
from ft_resource_estimation.graphs.callgraph import CallGraph
from ft_resource_estimation.topologies import Linear
from ft_resource_estimation.error_models import GrossErrorModel
from ft_resource_estimation.target import Target


# build the circuit we are interested in
num_qubits = 200
oracle = QuantumCircuit(num_qubits)
oracle.cz(0, 1)
circuit = grover_operator(oracle)

# create the call graph
graph = CallGraph(circuit)

# query graph properties
print("Num. Hadamards:", graph.count("h"))  # number of Hadamard gates
base_count = graph.count_basis() # count final leaves 
print("Basis gates:")
for node, count in base_count.items():
        print(node.name(), count)
base_count = graph.count_basis(['h', 'cx', 't']) # unroll to specific gate set 
print("Unrolled gates:")
for node, count in base_count.items():
        print(node.name(), count)

# specify the error model
error_model = GrossErrorModel(p=3)

# specify the topology we compile to
topo = Linear(num_modules=circuit.num_qubits // 11 + 1)

# build the target system
target = Target(topo, error_model)
 
# estimate the total error
base_fid = target.estimate_fidelity(base_count)
print("\nEstimated fidelity:", base_fid)
```
### 1. The call graph

The circuit of interest is represented as **call graph**:
- nodes represent types of operation (e.g. ADD, QFT, CCX, T, ..)
- each node has directed edges to nodes (operations) that it's synthesis contains
- edge weights are integers that count how often an operation is contained in a node

For example, quantum amplitude estimation (QAE) would be represented as:
![image](https://github.ibm.com/user-attachments/assets/f705a7f7-5339-438b-a9f7-acbae25e59be)

This representation allows to unroll a circuit and count operations very efficiently, but loses information about relative placements.


### 2. Target

The target defines the compilation and error model used to evaluate the dictionary of operations returned by a call graph.

It specifies:

- the hardware topology, describing the available qubits, connectivity, and location of the T factories, and

- an error model, describing the operation error rates.

Together, these determine how the fidelity of a circuit is estimated.

#### Fidelity estimation

The fidelity is computed by evaluating each operation in the dictionary produced by the call graph under the target assumptions. For each operation, the target:

- computes the fidelity assuming an optimal placement on the topology, and

- incorporates an average routing overhead to account for the approximation induced by compiling nodes independently, rather than compiling the full circuit with its global structure

This yields an approximate fidelity estimate that captures hardware constraints while avoiding explicit compilation and routing of the full circuit at the highest level of the call graph.

#### 2.1. Topology

The topology specifies: 
- the number of qubits and connections
- location of the T factories
- the optimal location and average routing overhead as a function of the number of qubits of the node of interest

Note that we have only implemented topologies that assume logical qubits are grouped in 12-qubit blocks (the bicycle code tori), collected in `tour_de_gross.py`. This could be easily extended in the future if we also want to consider other setups, such as the surface code.

#### 2.2. Error model

At an abstract level, the error model stores information about the error rates of its primitive operations, and provides the machinery to compute the fidelity of the operations allowed within the model.

At present, the error model is implemented for the bicycle model instruction set, specialized to the Gross code.

In this setting, the Gross code takes as input a physical error rate and derives from it the effective error rates of the primitive operations (idle, automorphism, in-block measurement, inter-block measurement and T injection). These rates are then used to compute the gate fidelity of the bicycle instructions: measurement, Pauli gate, Pauli rotations, T gates, and Clifford operations.

## Roadmap

This section outlines both the **research questions** the framework is meant to address and the **software features** needed to support them. The two are naturally related: answering a given research question often requires specific features to be implemented.

### Research questions

This section refers to the research questions we want to study using the framework. 
Research questions are annotated with references to the relevant features. For example, **[F3]** indicates that a given research question depends on (or motivates) **Feature 3** listed below.

In addition, for some research questions we explicitly state the expected **deliverable**, e.g. a benchmark, a plot, or a folder.

1. Set of examples
   1. Simple examples: Arithmetics (e.g. multiplication with different adders), QPE, Grover, QAOA / Trotter. 
      **Deliverable:** New additions in the `Examples` folder.
   1. High level algorithm demonstration (something beyond the examples in 1.).
1. Quality benchmarks compared against 
   1. analytical numbers on a subset of the `Examples`.
   1. on smaller sets, compare against full Gross code ISA compilation
1. What are the main error contributions? **[[F1](#F1)]**
   1. Does routing overhead have a larger impact than compiling to the optimal location? If so can use dictionaries instead of compiling the blocks.
1. Survey: compare to qualtran, bartiq. **Deliverable:** `Benchmarks` folder / repo that uses the `Examples` from 1.
1. Litinski on the set of examples **[[F2](#F2)]**. **Deliverable:** data or plots.
   1. In which regime is Litinski worth it?
1. Functional representation of the error such that it takes different error contributions as input and outputs the total fidelity. **[[F1](#F1)]** **Deliverable:** Tutorial that uses this feature.
1. T factory layout: **[[F3](#F3), [F4](#F4)]**
   1. dynamic vs fixed
   1. How much do you gain by going from line -> ladder -> square -> dynamic allocation of T factory
   1. Given a quantum algorithm, what is the optimal and realistic topology in terms of T factories?

### Software features

This section lists the concrete software features to be implemented. Features are numbered so they can be referenced from the research-question list.
1. <a id="F1"></a> Split the different error contributions (T error, entanglement, Pauli addressing)
2. <a id="F2"></a> Pauli addressing (right now we say 19 always)
3. <a id="F3"></a> Different T factory topologies
4. <a id="F4"></a> Dynamic T factory allocation
5. <a id="F5"></a> Include algorithmic error
