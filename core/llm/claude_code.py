"""
ATOMIC CLAUDE - Claude Code CLI Provider

LLM provider that invokes the Claude Code CLI (subscription-based).
Uses `claude -p` (print mode) for non-interactive invocation.
"""

import os
import shutil
import subprocess
import time
from typing import Dict, Generator, Optional, Any

from .base import (
    BaseLLMProvider,
    LLMResponse,
    TokenUsage,
    HealthStatus,
    APIError,
)
from .resolver import CLAUDE_CODE_FAST_MODE_FORBIDDEN


# Model tier → CLI model flag
MODEL_TIER_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}


class ClaudeCodeProvider(BaseLLMProvider):
    """
    Claude Code CLI provider (subscription).

    Invokes the `claude` CLI in print mode (`-p`) via subprocess.
    No API key required — uses the Claude Code subscription.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.provider_name = "claude-code"
        self._claude_path = shutil.which("claude")
        self.default_model = self.config.get("default_model", "sonnet")
        self.default_timeout = self.config.get("timeout", 600)

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 16_000,
        temperature: float = 1.0,
        timeout: int = 0,
        **kwargs
    ) -> LLMResponse:
        """Invoke Claude Code CLI with a prompt."""
        if not self._claude_path:
            raise APIError("claude CLI not found on PATH", provider="claude-code")

        resolved_model = self._resolve_model(model)
        effective_timeout = timeout or self.default_timeout

        cmd = [self._claude_path, "-p", "--output-format", "text"]

        if resolved_model:
            cmd.extend(["--model", resolved_model])

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # Effort level (low/medium/high)
        effort = kwargs.get("effort") or kwargs.get("effort_level")
        if effort and effort in ("low", "medium", "high"):
            cmd.extend(["--effort", effort])

        # Build clean environment — unset all Claude Code session vars
        # to avoid "cannot be launched inside another Claude Code session"
        env = os.environ.copy()
        for key in list(env.keys()):
            if key.startswith("CLAUDECODE") or key.startswith("CLAUDE_CODE"):
                del env[key]

        # Use caller-supplied cwd to prevent Claude Code from reading
        # atomic-claude's own CLAUDE.md and source files (context bleed)
        cwd = kwargs.get("cwd")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=env,
                cwd=cwd,
            )
        except subprocess.TimeoutExpired:
            raise APIError(
                f"Claude Code CLI timed out after {effective_timeout}s",
                provider="claude-code",
            )
        except OSError as e:
            raise APIError(f"Failed to run claude CLI: {e}", provider="claude-code")

        elapsed_ms = int((time.time() - start_time) * 1000)

        if result.returncode != 0:
            # Error may be in stderr or stdout
            err_msg = (result.stderr or "").strip() or (result.stdout or "").strip()
            if not err_msg:
                err_msg = f"exit code {result.returncode} (no output)"
            raise APIError(
                f"Claude Code CLI failed: {err_msg}",
                provider="claude-code",
            )

        content = result.stdout.strip() if result.stdout else ""

        # Rough token estimate (no exact count from CLI)
        est_input = len(prompt) // 4
        est_output = len(content) // 4

        return LLMResponse(
            content=content,
            model=resolved_model or self.default_model,
            provider="claude-code",
            usage=TokenUsage(input_tokens=est_input, output_tokens=est_output),
            finish_reason="end_turn",
            latency_ms=elapsed_ms,
        )

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 16_000,
        temperature: float = 1.0,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream is not natively supported — falls back to full invoke."""
        response = self.invoke(
            prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        yield response.content

    def validate_model(self, model_name: str) -> bool:
        """Check if model is a known Claude model."""
        if model_name in MODEL_TIER_MAP:
            return True
        if model_name in MODEL_TIER_MAP.values():
            return True
        return model_name.startswith("claude-")

    def get_token_count(self, text: str, model: Optional[str] = None) -> int:
        """Rough token estimate (chars / 4)."""
        return len(text) // 4

    def health_check(self) -> HealthStatus:
        """Check if claude CLI is available."""
        if shutil.which("claude"):
            return HealthStatus.HEALTHY
        return HealthStatus.UNAVAILABLE

    def _resolve_model(self, model: Optional[str]) -> Optional[str]:
        """Resolve tier name to full model ID."""
        if model is None:
            model = self.default_model
        return MODEL_TIER_MAP.get(model, model)
