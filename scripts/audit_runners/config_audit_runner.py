#!/usr/bin/env python3
"""
Configuration Audit Runner
Validates all configuration files and environment variable handling

This audit ensures that:
1. Configuration files exist and are valid
2. Configuration schema is correct
3. Environment variables are properly set
4. Configuration consistency across files
"""

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================================
# ANSI COLOR CODES
# ============================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
NC = "\033[0m"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ConfigTestResult:
    """Result of a single configuration test."""
    category: str  # config_files, schema, env_vars, consistency
    test: str
    passed: bool
    message: str
    severity: str  # critical, warning, info


@dataclass
class ConfigAuditReport:
    """Overall configuration audit report."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    duration: float
    results: List[Dict]

    def critical_failures(self) -> int:
        """Count critical failures."""
        return sum(1 for r in self.results if not r["passed"] and r["severity"] == "critical")

    def warnings(self) -> int:
        """Count warnings."""
        return sum(1 for r in self.results if not r["passed"] and r["severity"] == "warning")


# ============================================================================
# CONFIGURATION AUDIT RUNNER
# ============================================================================

class ConfigAuditRunner:
    """
    Validates all configuration files and environment variables for ATOMIC CLAUDE.
    """

    def __init__(self, atomic_root: Optional[Path] = None):
        if atomic_root:
            self.atomic_root = atomic_root
        else:
            self.atomic_root = Path(__file__).parent.parent.resolve()

        self.test_dir = self.atomic_root / "test"
        self.reports_dir = self.test_dir / "reports"
        self.outputs_dir = self.atomic_root / ".outputs" / "0-setup"
        self.init_dir = self.atomic_root / "initialization"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.results: List[ConfigTestResult] = []

    # ========================================================================
    # CONFIGURATION FILE TESTS
    # ========================================================================

    def test_config_files_exist(self) -> List[ConfigTestResult]:
        """Test that required configuration files exist."""
        results = []

        print(f"\n{BOLD}{BLUE}Testing Configuration File Existence...{NC}")

        # Test project-config.json
        print(f"  Checking project-config.json...", end=" ")
        project_config = self.outputs_dir / "project-config.json"

        if project_config.exists():
            print(f"{GREEN}✓{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test="project-config.json exists",
                passed=True,
                message=f"Found at {project_config}",
                severity="critical"
            ))
        else:
            print(f"{RED}✗{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test="project-config.json exists",
                passed=False,
                message=f"Not found at {project_config}",
                severity="critical"
            ))

        # Test secrets.json
        print(f"  Checking secrets.json...", end=" ")
        secrets_file = self.outputs_dir / "secrets.json"

        if secrets_file.exists():
            print(f"{GREEN}✓{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test="secrets.json exists",
                passed=True,
                message=f"Found at {secrets_file}",
                severity="critical"
            ))
        else:
            print(f"{RED}✗{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test="secrets.json exists",
                passed=False,
                message=f"Not found at {secrets_file}",
                severity="critical"
            ))

        # Test setup.md (optional)
        print(f"  Checking initialization/setup.md (optional)...", end=" ")
        setup_file = self.init_dir / "setup.md"

        if setup_file.exists():
            print(f"{GREEN}✓{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test="setup.md exists",
                passed=True,
                message=f"Found at {setup_file}",
                severity="info"
            ))
        else:
            print(f"{YELLOW}~{NC} Not present")
            results.append(ConfigTestResult(
                category="config_files",
                test="setup.md exists",
                passed=True,  # Optional file
                message="Optional file not present (OK for guided mode)",
                severity="info"
            ))

        # Test .outputs/0-setup directory exists
        print(f"  Checking .outputs/0-setup directory...", end=" ")

        if self.outputs_dir.exists() and self.outputs_dir.is_dir():
            print(f"{GREEN}✓{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test=".outputs/0-setup directory exists",
                passed=True,
                message=f"Found at {self.outputs_dir}",
                severity="critical"
            ))
        else:
            print(f"{RED}✗{NC}")
            results.append(ConfigTestResult(
                category="config_files",
                test=".outputs/0-setup directory exists",
                passed=False,
                message=f"Not found at {self.outputs_dir}",
                severity="critical"
            ))

        return results

    # ========================================================================
    # SCHEMA VALIDATION TESTS
    # ========================================================================

    def test_config_schema(self) -> List[ConfigTestResult]:
        """Test that configuration files have valid schema."""
        results = []

        print(f"\n{BOLD}{BLUE}Testing Configuration Schema...{NC}")

        # Test project-config.json schema
        project_config = self.outputs_dir / "project-config.json"

        if project_config.exists():
            print(f"  Validating project-config.json schema...", end=" ")

            try:
                with open(project_config, 'r') as f:
                    config = json.load(f)

                # Handle both flat and nested config formats
                # If config has "extracted.project" structure, flatten it for testing
                if "extracted" in config and "project" in config["extracted"]:
                    # Merge top-level and extracted.project fields
                    project_data = config["extracted"]["project"]
                    config = {**config, **project_data}

                # Check required fields
                required_fields = ["name", "type"]
                missing_fields = [f for f in required_fields if f not in config]

                if not missing_fields:
                    print(f"{GREEN}✓{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project-config.json has required fields",
                        passed=True,
                        message=f"All required fields present: {', '.join(required_fields)}",
                        severity="critical"
                    ))
                else:
                    print(f"{RED}✗{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project-config.json has required fields",
                        passed=False,
                        message=f"Missing required fields: {', '.join(missing_fields)}",
                        severity="critical"
                    ))

                # Check optional but recommended fields
                print(f"  Checking optional fields...", end=" ")
                recommended_fields = ["description", "tech_stack", "setup_mode"]
                present_recommended = [f for f in recommended_fields if f in config]

                if len(present_recommended) == len(recommended_fields):
                    print(f"{GREEN}✓{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project-config.json has recommended fields",
                        passed=True,
                        message=f"All recommended fields present: {', '.join(recommended_fields)}",
                        severity="info"
                    ))
                elif present_recommended:
                    print(f"{YELLOW}⚠{NC}")
                    missing = [f for f in recommended_fields if f not in config]
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project-config.json has recommended fields",
                        passed=False,
                        message=f"Missing recommended fields: {', '.join(missing)}",
                        severity="warning"
                    ))
                else:
                    print(f"{YELLOW}⚠{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project-config.json has recommended fields",
                        passed=False,
                        message="No recommended fields present",
                        severity="warning"
                    ))

                # Validate project type
                print(f"  Validating project type...", end=" ")
                valid_types = ["webapp", "cli", "library", "service", "component", "new-component", "system"]
                project_type = config.get("type")

                if project_type in valid_types:
                    print(f"{GREEN}✓{NC} ({project_type})")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project type is valid",
                        passed=True,
                        message=f"Type '{project_type}' is valid",
                        severity="critical"
                    ))
                else:
                    print(f"{YELLOW}⚠{NC} ({project_type})")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="project type is valid",
                        passed=False,
                        message=f"Type '{project_type}' not in standard types: {', '.join(valid_types)}",
                        severity="warning"
                    ))

            except json.JSONDecodeError as e:
                print(f"{RED}✗{NC}")
                results.append(ConfigTestResult(
                    category="schema",
                    test="project-config.json is valid JSON",
                    passed=False,
                    message=f"JSON parse error: {str(e)}",
                    severity="critical"
                ))
            except Exception as e:
                print(f"{RED}✗{NC}")
                results.append(ConfigTestResult(
                    category="schema",
                    test="project-config.json is readable",
                    passed=False,
                    message=f"Error reading file: {str(e)}",
                    severity="critical"
                ))

        # Test secrets.json schema
        secrets_file = self.outputs_dir / "secrets.json"

        if secrets_file.exists():
            print(f"  Validating secrets.json schema...", end=" ")

            try:
                with open(secrets_file, 'r') as f:
                    secrets = json.load(f)

                # Check for expected fields (flexible schema)
                expected_keys = ["memory_enabled", "network_mode"]
                present_keys = [k for k in expected_keys if k in secrets]

                print(f"{GREEN}✓{NC}")
                results.append(ConfigTestResult(
                    category="schema",
                    test="secrets.json is valid JSON",
                    passed=True,
                    message=f"Valid JSON with {len(secrets)} keys",
                    severity="critical"
                ))

                # Check for provider configuration
                print(f"  Checking provider configuration...", end=" ")
                provider_keys = ["bedrock_enabled", "ollama_enabled", "aws_region", "ollama_host", "claude_code_enabled", "ATOMIC_LLM_PROVIDER"]
                present_providers = [k for k in provider_keys if k in secrets]

                if present_providers:
                    print(f"{GREEN}✓{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="secrets.json has provider configuration",
                        passed=True,
                        message=f"Found provider keys: {', '.join(present_providers)}",
                        severity="info"
                    ))
                else:
                    print(f"{YELLOW}⚠{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="secrets.json has provider configuration",
                        passed=False,
                        message="No provider configuration found",
                        severity="warning"
                    ))

            except json.JSONDecodeError as e:
                print(f"{RED}✗{NC}")
                results.append(ConfigTestResult(
                    category="schema",
                    test="secrets.json is valid JSON",
                    passed=False,
                    message=f"JSON parse error: {str(e)}",
                    severity="critical"
                ))
            except Exception as e:
                print(f"{RED}✗{NC}")
                results.append(ConfigTestResult(
                    category="schema",
                    test="secrets.json is readable",
                    passed=False,
                    message=f"Error reading file: {str(e)}",
                    severity="critical"
                ))

        # Test setup.md format (if present)
        setup_file = self.init_dir / "setup.md"

        if setup_file.exists():
            print(f"  Validating setup.md format...", end=" ")

            try:
                with open(setup_file, 'r') as f:
                    content = f.read()

                # Check for key-value pairs
                kv_pattern = re.compile(r'^\*\*[\w.]+\*\*:\s*.+$', re.MULTILINE)
                matches = kv_pattern.findall(content)

                if matches:
                    print(f"{GREEN}✓{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="setup.md has valid format",
                        passed=True,
                        message=f"Found {len(matches)} configuration entries",
                        severity="info"
                    ))
                else:
                    print(f"{YELLOW}⚠{NC}")
                    results.append(ConfigTestResult(
                        category="schema",
                        test="setup.md has valid format",
                        passed=False,
                        message="No valid key-value pairs found",
                        severity="warning"
                    ))

            except Exception as e:
                print(f"{RED}✗{NC}")
                results.append(ConfigTestResult(
                    category="schema",
                    test="setup.md is readable",
                    passed=False,
                    message=f"Error reading file: {str(e)}",
                    severity="warning"
                ))

        return results

    # ========================================================================
    # ENVIRONMENT VARIABLE TESTS
    # ========================================================================

    def test_env_vars(self) -> List[ConfigTestResult]:
        """Test environment variable configuration."""
        results = []

        print(f"\n{BOLD}{BLUE}Testing Environment Variables...{NC}")

        # Check ATOMIC_UAT_MODE
        print(f"  Checking ATOMIC_UAT_MODE...", end=" ")
        uat_mode = os.getenv("ATOMIC_UAT_MODE", "false")

        if uat_mode.lower() in ["true", "false"]:
            print(f"{GREEN}✓{NC} ({uat_mode})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_UAT_MODE is valid",
                passed=True,
                message=f"Value: {uat_mode}",
                severity="info"
            ))
        else:
            print(f"{YELLOW}⚠{NC} ({uat_mode})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_UAT_MODE is valid",
                passed=False,
                message=f"Invalid value '{uat_mode}' (should be 'true' or 'false')",
                severity="warning"
            ))

        # Check ATOMIC_AUTO_APPROVE
        print(f"  Checking ATOMIC_AUTO_APPROVE...", end=" ")
        auto_approve = os.getenv("ATOMIC_AUTO_APPROVE", "false")

        if auto_approve.lower() in ["true", "false"]:
            print(f"{GREEN}✓{NC} ({auto_approve})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_AUTO_APPROVE is valid",
                passed=True,
                message=f"Value: {auto_approve}",
                severity="info"
            ))
        else:
            print(f"{YELLOW}⚠{NC} ({auto_approve})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_AUTO_APPROVE is valid",
                passed=False,
                message=f"Invalid value '{auto_approve}' (should be 'true' or 'false')",
                severity="warning"
            ))

        # Check ATOMIC_MEMORY_ENABLED
        print(f"  Checking ATOMIC_MEMORY_ENABLED...", end=" ")
        memory_enabled = os.getenv("ATOMIC_MEMORY_ENABLED", "")

        if memory_enabled == "":
            print(f"{YELLOW}~{NC} Not set")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_MEMORY_ENABLED status",
                passed=True,
                message="Not set (will use secrets.json value)",
                severity="info"
            ))
        elif memory_enabled.lower() in ["true", "false"]:
            print(f"{GREEN}✓{NC} ({memory_enabled})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_MEMORY_ENABLED is valid",
                passed=True,
                message=f"Value: {memory_enabled}",
                severity="info"
            ))
        else:
            print(f"{YELLOW}⚠{NC} ({memory_enabled})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_MEMORY_ENABLED is valid",
                passed=False,
                message=f"Invalid value '{memory_enabled}' (should be 'true' or 'false')",
                severity="warning"
            ))

        # Check ATOMIC_NETWORK_MODE
        print(f"  Checking ATOMIC_NETWORK_MODE...", end=" ")
        network_mode = os.getenv("ATOMIC_NETWORK_MODE", "")

        if network_mode == "":
            print(f"{YELLOW}~{NC} Not set")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_NETWORK_MODE status",
                passed=True,
                message="Not set (will use secrets.json value)",
                severity="info"
            ))
        elif network_mode.lower() in ["cui", "internet", "airgapped"]:
            print(f"{GREEN}✓{NC} ({network_mode})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_NETWORK_MODE is valid",
                passed=True,
                message=f"Value: {network_mode}",
                severity="info"
            ))
        else:
            print(f"{YELLOW}⚠{NC} ({network_mode})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_NETWORK_MODE is valid",
                passed=False,
                message=f"Invalid value '{network_mode}' (should be 'cui', 'internet', or 'airgapped')",
                severity="warning"
            ))

        # Check ATOMIC_OFFLINE_MODE
        print(f"  Checking ATOMIC_OFFLINE_MODE...", end=" ")
        offline_mode = os.getenv("ATOMIC_OFFLINE_MODE", "false")

        if offline_mode.lower() in ["true", "false"]:
            print(f"{GREEN}✓{NC} ({offline_mode})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_OFFLINE_MODE is valid",
                passed=True,
                message=f"Value: {offline_mode}",
                severity="info"
            ))
        else:
            print(f"{YELLOW}⚠{NC} ({offline_mode})")
            results.append(ConfigTestResult(
                category="env_vars",
                test="ATOMIC_OFFLINE_MODE is valid",
                passed=False,
                message=f"Invalid value '{offline_mode}' (should be 'true' or 'false')",
                severity="warning"
            ))

        # Check for conflicting settings
        print(f"  Checking for conflicting env vars...", end=" ")
        conflicts = []

        # Conflict: UAT_MODE=true + AUTO_APPROVE=true (both shouldn't be active)
        if uat_mode.lower() == "true" and auto_approve.lower() == "true":
            conflicts.append("ATOMIC_UAT_MODE and ATOMIC_AUTO_APPROVE both enabled")

        # Conflict: OFFLINE_MODE=true + NETWORK_MODE=internet
        if offline_mode.lower() == "true" and network_mode.lower() == "internet":
            conflicts.append("ATOMIC_OFFLINE_MODE=true conflicts with ATOMIC_NETWORK_MODE=internet")

        if not conflicts:
            print(f"{GREEN}✓{NC}")
            results.append(ConfigTestResult(
                category="env_vars",
                test="no conflicting env vars",
                passed=True,
                message="No conflicts detected",
                severity="warning"
            ))
        else:
            print(f"{YELLOW}⚠{NC}")
            results.append(ConfigTestResult(
                category="env_vars",
                test="no conflicting env vars",
                passed=False,
                message=f"Conflicts: {'; '.join(conflicts)}",
                severity="warning"
            ))

        return results

    # ========================================================================
    # CONSISTENCY TESTS
    # ========================================================================

    def test_config_consistency(self) -> List[ConfigTestResult]:
        """Test consistency across configuration files."""
        results = []

        print(f"\n{BOLD}{BLUE}Testing Configuration Consistency...{NC}")

        project_config_file = self.outputs_dir / "project-config.json"
        secrets_file = self.outputs_dir / "secrets.json"

        if not project_config_file.exists() or not secrets_file.exists():
            print(f"  {YELLOW}Skipping consistency tests (missing config files){NC}")
            return results

        try:
            with open(project_config_file, 'r') as f:
                project_config = json.load(f)

            with open(secrets_file, 'r') as f:
                secrets = json.load(f)

            # Test: network_mode consistency
            print(f"  Checking network_mode consistency...", end=" ")

            # Get network_mode from various places
            config_network_mode = project_config.get("sandbox", {}).get("network_mode")
            secrets_network_mode = secrets.get("network_mode")
            env_network_mode = os.getenv("ATOMIC_NETWORK_MODE")

            modes = [m for m in [config_network_mode, secrets_network_mode, env_network_mode] if m]

            if len(set(modes)) <= 1:
                print(f"{GREEN}✓{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="network_mode is consistent",
                    passed=True,
                    message=f"Consistent value: {modes[0] if modes else 'not set'}",
                    severity="warning"
                ))
            else:
                print(f"{YELLOW}⚠{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="network_mode is consistent",
                    passed=False,
                    message=f"Inconsistent values: project-config={config_network_mode}, secrets={secrets_network_mode}, env={env_network_mode}",
                    severity="warning"
                ))

            # Test: project name is set
            print(f"  Checking project name...", end=" ")
            project_name = project_config.get("name") or project_config.get("project", {}).get("name")

            if project_name and project_name.strip():
                print(f"{GREEN}✓{NC} ({project_name})")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="project name is set",
                    passed=True,
                    message=f"Project name: {project_name}",
                    severity="critical"
                ))
            else:
                print(f"{RED}✗{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="project name is set",
                    passed=False,
                    message="Project name is empty or missing",
                    severity="critical"
                ))

            # Test: memory_enabled consistency
            print(f"  Checking memory_enabled consistency...", end=" ")

            secrets_memory = secrets.get("memory_enabled")
            env_memory = os.getenv("ATOMIC_MEMORY_ENABLED")

            if env_memory and secrets_memory is not None:
                if (env_memory.lower() == "true") == secrets_memory:
                    print(f"{GREEN}✓{NC}")
                    results.append(ConfigTestResult(
                        category="consistency",
                        test="memory_enabled is consistent",
                        passed=True,
                        message=f"Both set to {secrets_memory}",
                        severity="info"
                    ))
                else:
                    print(f"{YELLOW}⚠{NC}")
                    results.append(ConfigTestResult(
                        category="consistency",
                        test="memory_enabled is consistent",
                        passed=False,
                        message=f"Mismatch: secrets.json={secrets_memory}, env={env_memory}",
                        severity="warning"
                    ))
            else:
                print(f"{GREEN}✓{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="memory_enabled is consistent",
                    passed=True,
                    message="Only one source configured (OK)",
                    severity="info"
                ))

            # Test: tech_stack is specified
            print(f"  Checking tech_stack...", end=" ")
            tech_stack = project_config.get("tech_stack")

            if tech_stack:
                if isinstance(tech_stack, list):
                    stack_str = ", ".join(tech_stack)
                else:
                    stack_str = str(tech_stack)

                print(f"{GREEN}✓{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="tech_stack is specified",
                    passed=True,
                    message=f"Tech stack: {stack_str[:50]}...",
                    severity="info"
                ))
            else:
                print(f"{YELLOW}⚠{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="tech_stack is specified",
                    passed=False,
                    message="Tech stack not specified",
                    severity="warning"
                ))

            # Test: provider configuration consistency
            print(f"  Checking provider configuration...", end=" ")

            llm_provider = project_config.get("llm", {}).get("primary_provider")
            bedrock_enabled = secrets.get("bedrock_enabled")
            ollama_enabled = secrets.get("ollama_enabled")

            provider_issues = []

            if llm_provider == "aws-bedrock" and not bedrock_enabled:
                provider_issues.append("Bedrock configured but not enabled in secrets")

            if not bedrock_enabled and not ollama_enabled:
                provider_issues.append("No LLM provider enabled")

            if not provider_issues:
                print(f"{GREEN}✓{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="provider configuration is valid",
                    passed=True,
                    message=f"Provider: {llm_provider}, Bedrock: {bedrock_enabled}, Ollama: {ollama_enabled}",
                    severity="critical"
                ))
            else:
                print(f"{YELLOW}⚠{NC}")
                results.append(ConfigTestResult(
                    category="consistency",
                    test="provider configuration is valid",
                    passed=False,
                    message=f"Issues: {'; '.join(provider_issues)}",
                    severity="warning"
                ))

        except json.JSONDecodeError as e:
            print(f"{RED}✗{NC}")
            results.append(ConfigTestResult(
                category="consistency",
                test="configuration files are valid JSON",
                passed=False,
                message=f"JSON parse error: {str(e)}",
                severity="critical"
            ))
        except Exception as e:
            print(f"{RED}✗{NC}")
            results.append(ConfigTestResult(
                category="consistency",
                test="configuration consistency check",
                passed=False,
                message=f"Error: {str(e)}",
                severity="warning"
            ))

        return results

    # ========================================================================
    # MAIN RUN METHOD
    # ========================================================================

    def run_all_tests(self) -> ConfigAuditReport:
        """
        Run all configuration tests and generate report.
        """
        start_time = time.time()

        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}{CYAN}ATOMIC CLAUDE - Configuration Audit{NC}")
        print(f"{BOLD}{CYAN}{'='*70}{NC}")

        print(f"\n{DIM}Atomic Root: {self.atomic_root}{NC}")
        print(f"{DIM}Config Dir:  {self.outputs_dir}{NC}")

        # Run all test categories
        file_results = self.test_config_files_exist()
        schema_results = self.test_config_schema()
        env_results = self.test_env_vars()
        consistency_results = self.test_config_consistency()

        # Combine all results
        all_results = file_results + schema_results + env_results + consistency_results

        # Convert to dict for JSON serialization
        results_dict = [
            {
                "category": r.category,
                "test": r.test,
                "passed": r.passed,
                "message": r.message,
                "severity": r.severity
            }
            for r in all_results
        ]

        # Count results
        total_tests = len(all_results)
        passed = sum(1 for r in all_results if r.passed)
        failed = total_tests - passed

        duration = time.time() - start_time

        # Create report
        report = ConfigAuditReport(
            timestamp=datetime.now().isoformat(),
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            duration=duration,
            results=results_dict
        )

        # Display summary
        self._display_summary(report)

        # Save report
        self._save_report(report)

        return report

    def _display_summary(self, report: ConfigAuditReport):
        """Display audit summary."""
        print(f"\n{BOLD}{CYAN}{'='*70}{NC}")
        print(f"{BOLD}{CYAN}Summary{NC}")
        print(f"{BOLD}{CYAN}{'='*70}{NC}\n")

        print(f"  Total Tests:         {report.total_tests}")
        print(f"  {GREEN}✓{NC} Passed:             {report.passed}")
        print(f"  {RED}✗{NC} Failed:             {report.failed}")
        print(f"  {RED}⚠{NC}  Critical Failures:  {report.critical_failures()}")
        print(f"  {YELLOW}⚠{NC}  Warnings:           {report.warnings()}")
        print(f"\n  Duration:            {report.duration:.2f}s")

        # Overall status
        if report.critical_failures() > 0:
            print(f"\n  {RED}✗ FAILED{NC} - Critical configuration issues detected")
        elif report.warnings() > 0:
            print(f"\n  {YELLOW}⚠ PASSED WITH WARNINGS{NC} - Configuration has warnings")
        else:
            print(f"\n  {GREEN}✓ PASSED{NC} - All configuration tests passed")

        # Show failures by category
        if report.failed > 0:
            print(f"\n{BOLD}Failed Tests by Category:{NC}\n")

            categories = {}
            for result in report.results:
                if not result["passed"]:
                    cat = result["category"]
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(result)

            for category, failures in categories.items():
                print(f"  {BOLD}{category}:{NC}")
                for failure in failures:
                    severity_color = RED if failure["severity"] == "critical" else YELLOW
                    print(f"    {severity_color}✗{NC} {failure['test']}")
                    print(f"      {DIM}{failure['message']}{NC}")
                print()

    def _save_report(self, report: ConfigAuditReport):
        """Save report to JSON file."""
        timestamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_file = self.reports_dir / f"config-audit-{timestamp_str}.json"

        # Convert report to dict
        report_dict = {
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "critical_failures": report.critical_failures(),
            "warnings": report.warnings(),
            "duration": report.duration,
            "results": report.results
        }

        with open(report_file, 'w') as f:
            json.dump(report_dict, f, indent=2)

        print(f"\n{DIM}Report saved: {report_file}{NC}\n")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    # Support optional path argument for testing
    atomic_root = None
    if len(sys.argv) > 1:
        atomic_root = Path(sys.argv[1])

    runner = ConfigAuditRunner(atomic_root=atomic_root)
    report = runner.run_all_tests()

    # Exit with error if critical failures found
    if report.critical_failures() > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
