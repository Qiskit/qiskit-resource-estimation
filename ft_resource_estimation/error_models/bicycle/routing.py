# Copyright IBM 2026

"""Routing for the bicycle architecture."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from .isa import GateType
from ...topologies.topology import BaseTopology, Allocation
from ...graphs.nodes import Node


@dataclass
class RoutingOverhead:
    gate_type: GateType  # type of Gate
    locality: int  # number of non-identity blocks
    total_span: int  # total number of blocks spanned
    num: int  # number of times it appears


class Routing(ABC):
    """Routing strategy for the bicycle code."""

    @abstractmethod
    def route(self, node: Node, topology: BaseTopology) -> tuple[list[int], list[RoutingOverhead]]:
        """Return the location and overhead for a node."""
        ...


class SwapRouting(Routing):
    """Swap-based routing.

    This separates the routing cost into: optimal location + swap overhead.
    """

    def route(self, node: Node, topology: BaseTopology) -> tuple[list[int], list[RoutingOverhead]]:
        location = topology.allocate(node, allocation=Allocation.BEST)

        num_blocks = topology.average_routing_overhead(node.num_qubits())

        # The cost of a SWAP gate is (XX + YY + ZZ) pi/4 rotations. The cost is then that of 3
        # two-local clifford gates. On average, we have 10 in-block swaps per block.
        overhead = [
            RoutingOverhead(GateType.Clifford, 1, 1, 30 * num_blocks),
        ]
        if num_blocks > 1:
            overhead.append(
                RoutingOverhead(GateType.Clifford, 2, 2, 3 * node.num_qubits() * (num_blocks - 1))
            )

        return location, overhead


class TeleportationRouting(Routing):
    """Teleportation-based routing."""

    def __init__(self, allocation: Allocation = Allocation.AVG):
        self.allocation = allocation

    def route(self, node: Node, topology: BaseTopology):
        location = topology.allocate(node, self.allocation)
        overhead = []

        return location, overhead
