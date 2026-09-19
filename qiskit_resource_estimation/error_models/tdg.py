# Copyright IBM 2026

from typing import Literal
from ..graphs.nodes import Node, InstructionNode
from ..graphs.metrics import Metric, Value
from .error_model import ErrorModel


class TdGErrorModel(ErrorModel[InstructionNode]):
    """Tour de Gross error model. Compilation logic is not yet implemented.

    Args:
        code: The bicycle code variant ("gross" or "two-gross").
        p: Physical error rate exponent — 3 for 1e-3, 4 for 1e-4.
        allocation: Location allocation strategy ("best", "average", or "worst" case).
    """

    def __init__(
        self,
        code: Literal["gross", "two-gross"],
        p: Literal[3, 4],
        allocation: Literal["best", "average", "worst"] = "average",
    ):
        self._code = code
        self._p = p
        self._allocation = allocation

    def supports(self, node: Node) -> bool:
        return isinstance(node, InstructionNode)

    def evaluate(self, node: InstructionNode) -> dict[Metric, Value]:
        raise NotImplementedError("TdGErrorModel compilation is not yet implemented.")
