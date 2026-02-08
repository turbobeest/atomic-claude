"""
Unit Tests for Core Audit System

Tests run_audit(), run_phase_audit(), UAT mode bypass, and audit selection.

Author: Phase 6 - Testing & Validation
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from core.audit import (
    run_audit,
    select_audit,
    run_phase_audit,
    AuditManager
)


# ============================================================================
# RUN AUDIT TESTS
# ============================================================================

@pytest.mark.unit
class TestRunAudit:
    """Test run_audit function."""

    @patch('core.audit.subprocess.run')
    def test_run_audit_success(self, mock_run, temp_dir):
        """Test successful audit execution."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        assert result is True
        mock_run.assert_called_once()

    @patch('core.audit.subprocess.run')
    def test_run_audit_failure(self, mock_run, temp_dir):
        """Test audit failure (non-blocking)."""
        mock_run.return_value = Mock(returncode=1, stderr="Audit failed")

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Failures are non-blocking
        assert result is True

    @patch('core.audit.subprocess.run')
    def test_run_audit_timeout(self, mock_run, temp_dir):
        """Test audit timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Timeout is non-blocking
        assert result is True

    @patch('core.audit.subprocess.run')
    def test_run_audit_exception(self, mock_run, temp_dir):
        """Test audit exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Exceptions are non-blocking
        assert result is True

    def test_run_audit_uat_mode(self, temp_dir, capsys):
        """Test audit bypass in UAT mode."""
        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs",
            uat_mode=True
        )

        assert result is True

        # Should print UAT message
        captured = capsys.readouterr()
        assert "UAT Mode" in captured.out
        assert "Skipping" in captured.out

    @patch('core.audit.subprocess.run')
    def test_run_audit_library_missing(self, mock_run, temp_dir, capsys):
        """Test handling missing audit library."""
        # Audit library won't exist in temp_dir

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Should skip gracefully
        assert result is True

        captured = capsys.readouterr()
        assert "not found" in captured.out or "skipping" in captured.out.lower()

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_run_audit_sets_environment(self, mock_exists, mock_run, temp_dir):
        """Test audit receives correct environment variables."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Check environment was passed
        call_args = mock_run.call_args
        env = call_args[1].get('env', {})

        assert 'ATOMIC_PHASE' in env
        assert env['ATOMIC_PHASE'] == "0-setup"
        assert 'ATOMIC_OUTPUT_DIR' in env


# ============================================================================
# SELECT AUDIT TESTS
# ============================================================================

@pytest.mark.unit
class TestSelectAudit:
    """Test select_audit function."""

    def test_select_audit_default(self, temp_dir):
        """Test default audit selection."""
        audit = select_audit(
            phase_num=0,
            output_dir=temp_dir / ".outputs"
        )

        assert audit is not None
        assert isinstance(audit, str)
        assert "phase-0" in audit

    def test_select_audit_uat_mode(self, temp_dir):
        """Test audit selection in UAT mode."""
        audit = select_audit(
            phase_num=1,
            output_dir=temp_dir / ".outputs",
            uat_mode=True
        )

        assert audit is not None
        assert "phase-1" in audit
        assert "default" in audit

    def test_select_audit_different_phases(self, temp_dir):
        """Test audit selection for different phases."""
        audit0 = select_audit(0, temp_dir / ".outputs")
        audit1 = select_audit(1, temp_dir / ".outputs")
        audit2 = select_audit(2, temp_dir / ".outputs")

        # Should return different audits for different phases
        assert "phase-0" in audit0
        assert "phase-1" in audit1
        assert "phase-2" in audit2


# ============================================================================
# RUN PHASE AUDIT TESTS
# ============================================================================

@pytest.mark.unit
class TestRunPhaseAudit:
    """Test run_phase_audit function."""

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_run_phase_audit_success(self, mock_exists, mock_run, temp_dir):
        """Test running phase audit successfully."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        result = run_phase_audit(
            phase_num=0,
            phase_id="0-setup",
            output_dir=temp_dir / ".outputs"
        )

        assert result is True

    def test_run_phase_audit_uat_mode(self, temp_dir, capsys):
        """Test phase audit bypass in UAT mode."""
        result = run_phase_audit(
            phase_num=0,
            phase_id="0-setup",
            output_dir=temp_dir / ".outputs",
            uat_mode=True
        )

        assert result is True

        captured = capsys.readouterr()
        assert "UAT Mode" in captured.out

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_run_phase_audit_selects_audit(self, mock_exists, mock_run, temp_dir):
        """Test phase audit selects appropriate audit."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        run_phase_audit(
            phase_num=1,
            phase_id="1-discovery",
            output_dir=temp_dir / ".outputs"
        )

        # Should have selected and run audit
        assert mock_run.called

    @patch('core.audit.select_audit', return_value=None)
    def test_run_phase_audit_no_audit_selected(self, mock_select, temp_dir, capsys):
        """Test handling when no audit is selected."""
        result = run_phase_audit(
            phase_num=0,
            phase_id="0-setup",
            output_dir=temp_dir / ".outputs"
        )

        # Should pass even without audit
        assert result is True

        captured = capsys.readouterr()
        assert "No audit selected" in captured.out


# ============================================================================
# AUDIT MANAGER TESTS
# ============================================================================

@pytest.mark.unit
class TestAuditManager:
    """Test AuditManager class."""

    def test_init(self, temp_dir):
        """Test AuditManager initialization."""
        manager = AuditManager(
            atomic_root=temp_dir,
            output_dir=temp_dir / ".outputs"
        )

        assert manager.atomic_root == temp_dir
        assert manager.output_dir == temp_dir / ".outputs"

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_run_phase_audit_via_manager(self, mock_exists, mock_run, temp_dir):
        """Test running phase audit via manager."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        manager = AuditManager(
            atomic_root=temp_dir,
            output_dir=temp_dir / ".outputs"
        )

        result = manager.run_phase_audit(
            phase_num=0,
            phase_id="0-setup"
        )

        assert result is True

    def test_manager_uat_mode(self, temp_dir):
        """Test manager respects UAT mode."""
        manager = AuditManager(
            atomic_root=temp_dir,
            output_dir=temp_dir / ".outputs"
        )

        result = manager.run_phase_audit(
            phase_num=0,
            phase_id="0-setup",
            uat_mode=True
        )

        assert result is True


# ============================================================================
# AUDIT EXECUTION TESTS
# ============================================================================

@pytest.mark.unit
class TestAuditExecution:
    """Test audit execution details."""

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_command_format(self, mock_exists, mock_run, temp_dir):
        """Test audit command is formatted correctly."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Check command format
        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert cmd[0] == "bash"
        assert "test-audit" in cmd

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_timeout_value(self, mock_exists, mock_run, temp_dir):
        """Test audit uses correct timeout."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Check timeout was set
        call_args = mock_run.call_args
        timeout = call_args[1].get('timeout')

        assert timeout == 300  # 5 minutes

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_captures_output(self, mock_exists, mock_run, temp_dir):
        """Test audit captures stdout and stderr."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Check output capture
        call_args = mock_run.call_args
        kwargs = call_args[1]

        assert kwargs.get('capture_output') is True
        assert kwargs.get('text') is True


# ============================================================================
# UAT MODE TESTS
# ============================================================================

@pytest.mark.unit
class TestUATMode:
    """Test UAT mode functionality."""

    def test_uat_mode_bypasses_audit(self, temp_dir, capsys):
        """Test UAT mode completely bypasses audit execution."""
        # No mock needed - should not even try to execute

        result = run_audit(
            "any-audit",
            "0-setup",
            temp_dir / ".outputs",
            uat_mode=True
        )

        assert result is True

        captured = capsys.readouterr()
        assert "Skipping" in captured.out

    def test_uat_mode_in_phase_audit(self, temp_dir, capsys):
        """Test UAT mode in phase audit."""
        result = run_phase_audit(
            phase_num=0,
            phase_id="0-setup",
            output_dir=temp_dir / ".outputs",
            uat_mode=True
        )

        assert result is True

        captured = capsys.readouterr()
        assert "UAT Mode" in captured.out

    def test_uat_mode_via_manager(self, temp_dir):
        """Test UAT mode through AuditManager."""
        manager = AuditManager(
            atomic_root=temp_dir,
            output_dir=temp_dir / ".outputs"
        )

        result = manager.run_phase_audit(
            phase_num=1,
            phase_id="1-discovery",
            uat_mode=True
        )

        assert result is True


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.unit
class TestAuditErrorHandling:
    """Test error handling in audit system."""

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_stderr_output(self, mock_exists, mock_run, temp_dir, capsys):
        """Test handling audit stderr output."""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Error: Audit check failed"
        )

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Non-blocking
        assert result is True

        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_empty_stderr(self, mock_exists, mock_run, temp_dir):
        """Test handling empty stderr."""
        mock_run.return_value = Mock(returncode=1, stderr="")

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        assert result is True

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_long_stderr(self, mock_exists, mock_run, temp_dir, capsys):
        """Test handling long stderr output."""
        long_error = "Error: " + ("x" * 500)
        mock_run.return_value = Mock(returncode=1, stderr=long_error)

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        assert result is True

        # Should truncate stderr
        captured = capsys.readouterr()
        # Output should contain truncated error (up to 200 chars)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestAuditIntegration:
    """Test audit integration scenarios."""

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_multiple_audits_sequential(self, mock_exists, mock_run, temp_dir):
        """Test running multiple audits sequentially."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Run multiple audits
        result1 = run_audit("audit1", "0-setup", temp_dir / ".outputs")
        result2 = run_audit("audit2", "1-discovery", temp_dir / ".outputs")
        result3 = run_audit("audit3", "2-prd", temp_dir / ".outputs")

        assert all([result1, result2, result3])
        assert mock_run.call_count == 3

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_audit_per_phase(self, mock_exists, mock_run, temp_dir):
        """Test running audit for each phase."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        for phase_num in range(3):
            result = run_phase_audit(
                phase_num=phase_num,
                phase_id=f"{phase_num}-phase",
                output_dir=temp_dir / ".outputs"
            )
            assert result is True

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_manager_multiple_phases(self, mock_exists, mock_run, temp_dir):
        """Test manager running audits for multiple phases."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        manager = AuditManager(
            atomic_root=temp_dir,
            output_dir=temp_dir / ".outputs"
        )

        results = []
        for phase_num in range(3):
            result = manager.run_phase_audit(
                phase_num=phase_num,
                phase_id=f"{phase_num}-phase"
            )
            results.append(result)

        assert all(results)


# ============================================================================
# NON-BLOCKING BEHAVIOR TESTS
# ============================================================================

@pytest.mark.unit
class TestNonBlockingBehavior:
    """Test audit non-blocking behavior."""

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_failure_non_blocking(self, mock_exists, mock_run, temp_dir):
        """Test audit failure is non-blocking."""
        mock_run.return_value = Mock(returncode=1, stderr="Failed")

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Should pass despite failure
        assert result is True

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_timeout_non_blocking(self, mock_exists, mock_run, temp_dir):
        """Test audit timeout is non-blocking."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Should pass despite timeout
        assert result is True

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_exception_non_blocking(self, mock_exists, mock_run, temp_dir):
        """Test audit exception is non-blocking."""
        mock_run.side_effect = RuntimeError("Unexpected error")

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        # Should pass despite exception
        assert result is True


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.unit
class TestAuditEdgeCases:
    """Test edge cases in audit system."""

    def test_empty_audit_name(self, temp_dir):
        """Test handling empty audit name."""
        result = run_audit(
            "",
            "0-setup",
            temp_dir / ".outputs",
            uat_mode=True  # Bypass execution
        )

        assert result is True

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_special_characters_in_audit_name(self, mock_exists, mock_run, temp_dir):
        """Test audit name with special characters."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        result = run_audit(
            "test-audit_v1.2",
            "0-setup",
            temp_dir / ".outputs"
        )

        assert result is True

    def test_nonexistent_output_dir(self, temp_dir):
        """Test handling non-existent output directory."""
        nonexistent = temp_dir / "nonexistent" / ".outputs"

        result = run_audit(
            "test-audit",
            "0-setup",
            nonexistent,
            uat_mode=True  # Bypass execution
        )

        assert result is True

    @patch('core.audit.subprocess.run')
    @patch('core.audit.Path.exists', return_value=True)
    def test_unicode_in_audit_output(self, mock_exists, mock_run, temp_dir):
        """Test handling Unicode in audit output."""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Error: 世界 failed"
        )

        result = run_audit(
            "test-audit",
            "0-setup",
            temp_dir / ".outputs"
        )

        assert result is True
