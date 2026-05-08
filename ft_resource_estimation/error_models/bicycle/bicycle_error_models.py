# Copyright IBM 2025.

"""The bicycle code error models."""

from __future__ import annotations

from qiskit.transpiler import PassManager
from mpmath import mp

from .routing import Routing, SwapRouting
from .error_rates import ErrorRates, gross_code
from . import compiler
from ..error_model import ErrorModel
from ...graphs.nodes import Node, InstructionNode
from ...graphs.metrics import (
    Metric,
    Value,
    Fidelity,
    InFidelity,
    InterFidelity,
    TFidelity,
    RoutingFidelity,
)
from ...topologies.topology import BaseTopology


class BicycleErrorModel(ErrorModel[InstructionNode]):
    """Error model for the bicycle code architecture.

    Compiles InstructionNodes to the bicycle ISA and returns fidelity estimates.

    Args:
        topology: The hardware topology.
        error_rates: The physical error rates for the bicycle ISA.
        routing: Routing strategy (defaults to SwapRouting).
        t_threshold: Number of T gates used to synthesise an arbitrary rotation.
    """

    def __init__(
        self,
        topology: BaseTopology,
        error_rates: ErrorRates,
        routing: Routing | None = None,
        t_threshold: int = 200,
        pass_manager: PassManager | None = None,
    ):
        self._topology = topology
        self._error_rates = error_rates
        self._routing = routing or SwapRouting()
        self._t_threshold = t_threshold
        self._pm = pass_manager

    def supports(self, node: Node) -> bool:
        return isinstance(node, InstructionNode)

    def evaluate(self, node: InstructionNode) -> dict[Metric, Value]:
        location, overhead = self._routing.route(node, self._topology)
        fidelity, in_fidelity, t_fidelity, inter_fidelity = compiler.compile(
            node, location, self._topology, self._error_rates, self._t_threshold, self._pm
        )

        routing_fidelity = mp.mpf(1)
        for ro in overhead:
            routing_fidelity *= (
                compiler.gate_fidelity(
                    ro.total_span, ro.locality, ro.gate_type, self._error_rates, self._t_threshold
                )[0]
                ** ro.num
            )

        fidelity *= routing_fidelity

        return {
            Fidelity(): fidelity,
            InFidelity(): in_fidelity,
            TFidelity(): t_fidelity,
            InterFidelity(): inter_fidelity,
            RoutingFidelity(): routing_fidelity,
        }


class GrossErrorModel(BicycleErrorModel):
    """Convenience error model for the Gross / Two-Gross bicycle code.

    Args:
        topology: The hardware topology.
        p: Physical error rate exponent — 3 for 1e-3, 4 for 1e-4.
        routing: Routing strategy (defaults to SwapRouting).
        t_threshold: Number of T gates used to synthesise an arbitrary rotation.
    """

    def __init__(
        self,
        topology: BaseTopology,
        p: int,
        routing: Routing | None = None,
        t_threshold: int = 200,
        pass_manager: PassManager | None = None,
    ):
        super().__init__(topology, gross_code(p), routing, t_threshold, pass_manager)
