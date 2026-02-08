"""
Task Type Definitions

Pydantic models for task metadata, state, results, and dependencies.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class TaskState(str, Enum):
    """Task state enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DependencyType(str, Enum):
    """Dependency type enum."""
    REQUIRED = "required"
    OPTIONAL = "optional"


class TaskDependency(BaseModel):
    """Task dependency definition."""
    task_id: str = Field(..., description="ID of the task this depends on")
    type: DependencyType = Field(
        default=DependencyType.REQUIRED,
        description="Whether this dependency is required or optional"
    )

    class Config:
        use_enum_values = True


class TaskDefinition(BaseModel):
    """Task metadata and configuration."""
    task_id: str = Field(..., description="Unique task identifier (e.g., '001', '105')")
    phase_id: str = Field(..., description="Phase identifier (e.g., '0-setup', '1-discovery')")
    name: str = Field(..., description="Human-readable task name")
    description: Optional[str] = Field(None, description="Detailed task description")
    timeout: int = Field(default=600, description="Task timeout in seconds")
    dependencies: List[TaskDependency] = Field(
        default_factory=list,
        description="Tasks that must complete before this one"
    )
    script_path: Optional[str] = Field(None, description="Path to bash task script")
    function: Optional[Any] = Field(None, description="Python function to execute")
    retryable: bool = Field(default=True, description="Whether task can be retried on failure")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata"
    )

    @validator('task_id')
    def validate_task_id(cls, v):
        """Validate task ID format."""
        if not v:
            raise ValueError("task_id cannot be empty")
        if not v.isdigit():
            raise ValueError(f"task_id must be numeric: {v}")
        return v

    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout is reasonable."""
        if v < 1:
            raise ValueError("timeout must be at least 1 second")
        if v > 7200:  # 2 hours
            raise ValueError("timeout cannot exceed 2 hours (7200 seconds)")
        return v

    @validator('max_retries')
    def validate_max_retries(cls, v):
        """Validate max retries is reasonable."""
        if v < 0:
            raise ValueError("max_retries cannot be negative")
        if v > 10:
            raise ValueError("max_retries cannot exceed 10")
        return v

    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True


class StateTransition(BaseModel):
    """Record of a state transition."""
    from_state: TaskState
    to_state: TaskState
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: Optional[str] = Field(None, description="Reason for transition")

    class Config:
        use_enum_values = True


class TaskResult(BaseModel):
    """Result of task execution."""
    task_id: str
    phase_id: str
    state: TaskState
    exit_code: Optional[int] = Field(None, description="Exit code (0 = success)")
    output: Optional[str] = Field(None, description="Task output/stdout")
    error: Optional[str] = Field(None, description="Error message/stderr")
    duration: Optional[float] = Field(None, description="Execution duration in seconds")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    artifacts: List[str] = Field(
        default_factory=list,
        description="Paths to generated artifacts"
    )
    retry_count: int = Field(default=0, description="Number of retries attempted")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata"
    )

    @property
    def success(self) -> bool:
        """Check if task was successful."""
        return self.state == TaskState.COMPLETED and self.exit_code == 0

    @property
    def failed(self) -> bool:
        """Check if task failed."""
        return self.state == TaskState.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "state": self.state.value if isinstance(self.state, TaskState) else self.state,
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "artifacts": self.artifacts,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }

    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of task validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def add_error(self, error: str):
        """Add validation error."""
        self.valid = False
        self.errors.append(error)

    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)

    @property
    def has_errors(self) -> bool:
        """Check if there are errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0
