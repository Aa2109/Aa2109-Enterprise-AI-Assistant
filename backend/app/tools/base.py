from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ToolRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    def risk_level(self) -> ToolRisk:
        return ToolRisk.LOW

    @property
    def requires_approval(self) -> bool:
        return self.risk_level in {
            ToolRisk.HIGH,
            ToolRisk.CRITICAL,
        }

    @abstractmethod
    def execute(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        raise NotImplementedError