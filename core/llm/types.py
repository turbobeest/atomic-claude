#!/usr/bin/env python3
"""
ATOMIC CLAUDE - LLM Shared Types

Pydantic models for LLM requests, responses, and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback to dataclasses
    BaseModel = object


class ModelRole(str, Enum):
    """Model role for routing."""
    PRIMARY = "primary"
    FAST = "fast"
    GARDENER = "gardener"
    HEAVYWEIGHT = "heavyweight"


class ProviderType(str, Enum):
    """Supported provider types."""
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    OPENAI = "openai"
    GOOGLE = "google"


class HealthStatus(str, Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


if PYDANTIC_AVAILABLE:
    class LLMRequest(BaseModel):
        """
        Standardized LLM request.

        Used by router to represent a provider-agnostic request.
        """
        prompt: str = Field(..., description="User prompt/message")
        system_prompt: Optional[str] = Field(None, description="System prompt")
        model: Optional[str] = Field(None, description="Model name or tier")
        max_tokens: int = Field(4096, ge=1, le=100000, description="Max output tokens")
        temperature: float = Field(1.0, ge=0.0, le=2.0, description="Sampling temperature")
        timeout: int = Field(300, ge=1, le=3600, description="Timeout in seconds")
        stream: bool = Field(False, description="Enable streaming")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

        @validator('prompt')
        def prompt_not_empty(cls, v):
            """Validate prompt is not empty."""
            if not v or not v.strip():
                raise ValueError("Prompt cannot be empty")
            return v

        class Config:
            """Pydantic config."""
            validate_assignment = True


    class LLMResponse(BaseModel):
        """
        Standardized LLM response.

        Returned by all providers.
        """
        content: str = Field(..., description="Response content")
        model: str = Field(..., description="Model used")
        provider: str = Field(..., description="Provider name")
        usage: Dict[str, int] = Field(default_factory=dict, description="Token usage")
        finish_reason: Optional[str] = Field(None, description="Finish reason")
        stop_reason: Optional[str] = Field(None, description="Stop reason")
        latency_ms: Optional[int] = Field(None, description="Latency in milliseconds")
        timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

        class Config:
            """Pydantic config."""
            json_encoders = {
                datetime: lambda v: v.isoformat()
            }


    class UsageStats(BaseModel):
        """
        Token usage statistics.

        Tracks token consumption across requests.
        """
        input_tokens: int = Field(0, ge=0, description="Input tokens")
        output_tokens: int = Field(0, ge=0, description="Output tokens")
        cache_read_tokens: int = Field(0, ge=0, description="Cache read tokens")
        cache_write_tokens: int = Field(0, ge=0, description="Cache write tokens")
        total_requests: int = Field(0, ge=0, description="Total requests")
        failed_requests: int = Field(0, ge=0, description="Failed requests")
        avg_latency_ms: float = Field(0.0, ge=0, description="Average latency")

        @property
        def total_tokens(self) -> int:
            """Total tokens used."""
            return self.input_tokens + self.output_tokens

        @property
        def success_rate(self) -> float:
            """Success rate (0.0-1.0)."""
            if self.total_requests == 0:
                return 0.0
            return (self.total_requests - self.failed_requests) / self.total_requests


    class ModelInfo(BaseModel):
        """
        Model metadata and capabilities.

        Describes model characteristics.
        """
        name: str = Field(..., description="Model identifier")
        provider: str = Field(..., description="Provider name")
        context_window: int = Field(..., ge=1, description="Context window size")
        max_output_tokens: int = Field(..., ge=1, description="Max output tokens")
        supports_streaming: bool = Field(True, description="Supports streaming")
        supports_vision: bool = Field(False, description="Supports vision inputs")
        supports_tools: bool = Field(False, description="Supports function calling")
        cost_per_1k_input: Optional[float] = Field(None, ge=0, description="Cost per 1k input tokens")
        cost_per_1k_output: Optional[float] = Field(None, ge=0, description="Cost per 1k output tokens")
        tier: Optional[str] = Field(None, description="Model tier (opus/sonnet/haiku)")


    class ProviderHealth(BaseModel):
        """
        Provider health information.

        Tracks provider availability and status.
        """
        provider: str = Field(..., description="Provider name")
        status: HealthStatus = Field(..., description="Health status")
        available: bool = Field(..., description="Provider available")
        last_check: datetime = Field(default_factory=datetime.now, description="Last health check")
        error_message: Optional[str] = Field(None, description="Error message if unavailable")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional health data")

        class Config:
            """Pydantic config."""
            json_encoders = {
                datetime: lambda v: v.isoformat()
            }


else:
    # Fallback to dataclasses if pydantic not available
    @dataclass
    class LLMRequest:
        """LLM request (dataclass fallback)."""
        prompt: str
        system_prompt: Optional[str] = None
        model: Optional[str] = None
        max_tokens: int = 4096
        temperature: float = 1.0
        timeout: int = 300
        stream: bool = False
        metadata: Dict[str, Any] = field(default_factory=dict)


    @dataclass
    class LLMResponse:
        """LLM response (dataclass fallback)."""
        content: str
        model: str
        provider: str
        usage: Dict[str, int] = field(default_factory=dict)
        finish_reason: Optional[str] = None
        stop_reason: Optional[str] = None
        latency_ms: Optional[int] = None
        timestamp: datetime = field(default_factory=datetime.now)
        metadata: Dict[str, Any] = field(default_factory=dict)


    @dataclass
    class UsageStats:
        """Usage statistics (dataclass fallback)."""
        input_tokens: int = 0
        output_tokens: int = 0
        cache_read_tokens: int = 0
        cache_write_tokens: int = 0
        total_requests: int = 0
        failed_requests: int = 0
        avg_latency_ms: float = 0.0

        @property
        def total_tokens(self) -> int:
            return self.input_tokens + self.output_tokens

        @property
        def success_rate(self) -> float:
            if self.total_requests == 0:
                return 0.0
            return (self.total_requests - self.failed_requests) / self.total_requests


    @dataclass
    class ModelInfo:
        """Model information (dataclass fallback)."""
        name: str
        provider: str
        context_window: int
        max_output_tokens: int
        supports_streaming: bool = True
        supports_vision: bool = False
        supports_tools: bool = False
        cost_per_1k_input: Optional[float] = None
        cost_per_1k_output: Optional[float] = None
        tier: Optional[str] = None


    @dataclass
    class ProviderHealth:
        """Provider health (dataclass fallback)."""
        provider: str
        status: HealthStatus
        available: bool
        last_check: datetime = field(default_factory=datetime.now)
        error_message: Optional[str] = None
        metadata: Dict[str, Any] = field(default_factory=dict)
