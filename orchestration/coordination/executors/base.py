"""Base classes for pattern executors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ExecutionContext:
    """Context passed to pattern executors."""

    task_id: str
    task_name: str
    task_func: Callable
    mem: Any                                 # TaskMemory instance
    roster: Optional[List[Tuple]] = None     # (AgentEntry, ResolvedModel) tuples
    gravity: str = "standard"
    graph: Any = None                        # GraphManager instance
    phase_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result from a pattern executor."""

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    pattern_used: str = "sequential"
    iterations: int = 1


class BasePatternExecutor(ABC):
    """Abstract base for coordination pattern executors."""

    @abstractmethod
    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        """Execute the pattern.

        Args:
            ctx: Execution context.

        Returns:
            ExecutionResult.
        """
        ...
