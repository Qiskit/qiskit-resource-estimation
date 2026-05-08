# Copyright IBM 2026.

"""Test generic Node/Metric pipeline without Qiskit or an error model."""

import unittest

from ft_resource_estimation.graphs.nodes import Node
from ft_resource_estimation.graphs.callgraph import CallGraph
from ft_resource_estimation.graphs.metrics import Metric, Value


class Banana(Metric):
    """Additive metric."""

    def combine(self, a: Value, b: Value) -> Value:
        return a + b

    def repeat(self, value: Value, count: int) -> Value:
        return value * count

    def identity(self) -> Value:
        return 0


class Rabbit(Metric):
    """Multiplicative metric."""

    def combine(self, a: Value, b: Value) -> Value:
        return a * b

    def repeat(self, value: Value, count: int) -> Value:
        return value**count

    def identity(self) -> Value:
        return 1


class Leaf1(Node):
    def name(self):
        return "Leaf1"

    def num_qubits(self):
        return 1

    def __hash__(self):
        return hash("Leaf1")

    def operations(self):
        return None

    def metrics(self) -> dict[Metric, Value]:
        return {Banana(): 3, Rabbit(): 2}


class Leaf2(Node):
    def name(self):
        return "Leaf2"

    def num_qubits(self):
        return 1

    def __hash__(self):
        return hash("Leaf2")

    def operations(self):
        return None

    def metrics(self) -> dict[Metric, Value]:
        return {Banana(): 5, Rabbit(): 1}


class Leaf3(Node):
    def name(self):
        return "Leaf3"

    def num_qubits(self):
        return 1

    def __hash__(self):
        return hash("Leaf3")

    def operations(self):
        return None

    def metrics(self) -> dict[Metric, Value]:
        return {Banana(): 2, Rabbit(): 3}


class Left(Node):
    def name(self):
        return "Left"

    def num_qubits(self):
        return 2

    def __hash__(self):
        return hash("Left")

    def operations(self) -> dict[Node, int] | None:
        return {Leaf1(): 1, Leaf2(): 2}


class Right(Node):
    def name(self):
        return "Right"

    def num_qubits(self):
        return 1

    def __hash__(self):
        return hash("Right")

    def operations(self) -> dict[Node, int] | None:
        return {Leaf3(): 3}


class Root(Node):
    """
    Custom node hierarchy

    Root ─── Left x 1 ─── Leaf1 x 1
            │         └── Leaf2 x 2
            └── Right x 2 ─── Leaf3 x 3

    Effective leaf counts from Root:
    Leaf1: 1
    Leaf2: 2
    Leaf3: 6
    """

    def name(self):
        return "Root"

    def num_qubits(self):
        return 3

    def __hash__(self):
        return hash("Root")

    def operations(self) -> dict[Node, int] | None:
        return {Left(): 1, Right(): 2}


class TestGenericMetrics(unittest.TestCase):
    def test_accumulation(self):
        """Test additive and multiplicative accumulations."""
        graph = CallGraph(Root())
        result = graph.estimate()
        self.assertEqual(result[Banana()], 25)
        self.assertAlmostEqual(result[Rabbit()], 3**6 * 2)


if __name__ == "__main__":
    unittest.main()
