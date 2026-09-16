# Copyright IBM 2026

from abc import abstractmethod, ABC
from typing import Generic, TypeVar
from ..graphs.nodes import Node
from ..graphs.metrics import Metric, Value

N = TypeVar("N", bound=Node)


class ErrorModel(ABC, Generic[N]):
    """An error model for a node."""

    @abstractmethod
    def supports(self, node: Node) -> bool:
        """Whether the input node is supported."""
        ...

    @abstractmethod
    def evaluate(self, node: N) -> dict[Metric, Value]:
        """Evaluate the error metrics for the node."""
        ...
