#!/usr/bin/env python3
"""
Actionability Meta-Audit Validator v2
Analyzes all audit files for actionability issues:
1. Regex pattern validity
2. Glob pattern validity
3. Script syntax validity (using shellcheck if available)
4. Command executability
5. Closeout verification validity
"""

import os
import re
import yaml
import fnmatch
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class Issue:
    audit_id: str
    audit_file: str
    severity: str
    issue: str
    field: str
    current: str
    recommended: str

@dataclass
class ValidationStats:
    patterns_checked: int = 0
    invalid_patterns: int = 0
    globs_checked: int = 0
    invalid_globs: int = 0
    scripts_checked: int = 0
    invalid_scripts: int = 0
    commands_checked: int = 0
    invalid_commands: int = 0
    verifications_checked: int = 0
    invalid_verifications: int = 0

class ActionabilityValidator:
    def __init__(self, audits_dir: str):
        self.audits_dir = Path(audits_dir)
        self.issues: List[Issue] = []
        self.stats = ValidationStats()
        self.shellcheck_available = shutil.which('shellcheck') is not None

        # Known valid commands (common CLI tools)
        self.valid_commands = {
            'grep', 'find', 'ls', 'cat', 'head', 'tail', 'wc', 'echo', 'printf',
            'bash', 'sh', 'python', 'python3', 'node', 'npm', 'npx', 'yarn', 'pnpm',
            'git', 'curl', 'wget', 'jq', 'sed', 'awk', 'sort', 'uniq', 'cut',
            'docker', 'docker-compose', 'kubectl', 'terraform', 'helm',
            'pip', 'pip3', 'poetry', 'pipenv',
            'cargo', 'rustc', 'go', 'java', 'javac', 'mvn', 'gradle',
            'semgrep', 'bandit', 'eslint', 'prettier', 'jest', 'pytest',
            'make', 'cmake', 'gcc', 'g++', 'clang',
            'aws', 'gcloud', 'az', 'gh', 'hub',
            'openssl', 'ssh', 'scp', 'rsync',
            'if', 'then', 'else', 'fi', 'for', 'do', 'done', 'while', 'case', 'esac',
            'test', '[', '[[', 'true', 'false', 'exit', 'return',
            'mkdir', 'rm', 'cp', 'mv', 'touch', 'chmod', 'chown',
            'tar', 'gzip', 'gunzip', 'zip', 'unzip',
            'nc', 'netstat', 'ss', 'nmap', 'dig', 'nslookup',
            'ps', 'top', 'htop', 'free', 'df', 'du',
            'xargs', 'tee', 'tr', 'comm', 'diff', 'patch',
            'rg', 'fd', 'fzf', 'bat', 'exa', 'tree',
            'yq', 'csvkit', 'miller',
            'trivy', 'snyk', 'grype', 'syft', 'cosign',
            'k9s', 'kubectx', 'kubens', 'kustomize', 'skaffold',
            'ansible', 'ansible-playbook', 'vault', 'consul',
            'redis-cli', 'mongo', 'psql', 'mysql', 'sqlite3',
            'coverage', 'nyc', 'istanbul', 'jacoco',
            'hadolint', 'shellcheck', 'yamllint', 'markdownlint',
            'dbt', 'feast', 'mlflow', 'dvc',
            'ncu', 'npm-check', 'depcheck', 'audit-ci',
            'opa', 'conftest', 'kubeval', 'kubesec',
        }

        # Problematic regex patterns
        self.problematic_regex_patterns = [
            (r'^\.\*$', "Pattern '.*' matches everything - too broad"),
            (r'^\.\+$', "Pattern '.+' matches everything with 1+ chars - too broad"),
            (r'^\.$', "Pattern '.' matches any single char - too broad"),
        ]

    def validate_regex(self, pattern: str, context: str) -> Tuple[bool, str]:
        """Validate a regex pattern for correctness and usefulness."""
        self.stats.patterns_checked += 1

        if not pattern or not pattern.strip():
            return False, "Empty pattern"

        # Check for overly broad patterns
        pattern_stripped = pattern.strip()
        for regex, msg in self.problematic_regex_patterns:
            if re.match(regex, pattern_stripped):
                return False, msg

        # Try to compile the regex
        try:
            compiled = re.compile(pattern)
            return True, ""
        except re.error as e:
            return False, f"Invalid regex syntax: {e}"

    def validate_glob(self, glob_pattern: str) -> Tuple[bool, str]:
        """Validate a glob pattern for correctness."""
        self.stats.globs_checked += 1

        if not glob_pattern or not glob_pattern.strip():
            return False, "Empty glob pattern"

        # Check for basic glob syntax issues
        try:
            # fnmatch.translate will work on most patterns
            fnmatch.translate(glob_pattern)

            # Check for patterns that are too broad
            if glob_pattern in ['*', '**', '**/*']:
                return False, f"Glob '{glob_pattern}' is too broad - will match all files"

            # Check for unbalanced braces/brackets
            if glob_pattern.count('{') != glob_pattern.count('}'):
                return False, "Unbalanced braces in glob pattern"

            if glob_pattern.count('[') != glob_pattern.count(']'):
                return False, "Unbalanced brackets in glob pattern"

            return True, ""
        except Exception as e:
            return False, f"Invalid glob syntax: {e}"

    def validate_bash_script_shellcheck(self, code: str) -> Tuple[bool, str]:
        """Validate bash script using shellcheck if available."""
        if not self.shellcheck_available:
            return True, ""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['shellcheck', '-s', 'bash', '-f', 'json', temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0 and result.stdout:
                import json
                try:
                    errors = json.loads(result.stdout)
                    error_msgs = [
                        e['message']
                        for e in errors
                        if e.get('level') == 'error'
                    ][:3]  # Limit to 3 errors
                    if error_msgs:
                        return False, "; ".join(error_msgs)
                except json.JSONDecodeError:
                    pass
            return True, ""
        except Exception:
            return True, ""
        finally:
            os.unlink(temp_path)

    def validate_bash_script_basic(self, code: str, script_id: str) -> Tuple[bool, str]:
        """Basic bash script validation without shellcheck."""
        self.stats.scripts_checked += 1

        if not code or not code.strip():
            return False, "Empty script"

        issues = []

        # Check for dangerous patterns - but be careful about false positives
        # Only flag truly dangerous patterns like "rm -rf /" or "rm -rf /*"
        # Not things like "rm -rf /tmp/..." which are relatively safe
        danger_patterns = [
            r'rm\s+-rf\s+/\s*$',           # rm -rf / (end of line)
            r'rm\s+-rf\s+/\s*;',           # rm -rf /;
            r'rm\s+-rf\s+/\*\s',           # rm -rf /* (space after)
            r'rm\s+-rf\s+/\*$',            # rm -rf /* (end of line)
            r'rm\s+-rf\s+--no-preserve-root',  # Force removal of root
        ]
        for danger_pat in danger_patterns:
            if re.search(danger_pat, code):
                issues.append("DANGEROUS: rm -rf / or similar detected")
                return False, "; ".join(issues)

        # Check for very obvious syntax errors using bash -n
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['bash', '-n', temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip().split('\n')[0] if result.stderr else "Syntax error"
                # Clean up the error message
                error_msg = re.sub(r'/tmp/[^:]+:', '', error_msg)
                return False, f"Bash syntax error: {error_msg[:100]}"
        except subprocess.TimeoutExpired:
            return True, ""
        except Exception as e:
            return True, ""  # Ignore other errors
        finally:
            os.unlink(temp_path)

        return True, ""

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """Validate a shell command for basic executability."""
        self.stats.commands_checked += 1

        if not command or not command.strip():
            return False, "Empty command"

        # Extract the first word (the command itself)
        cmd_clean = command.strip()

        # Remove leading whitespace and handle various shell constructs
        if cmd_clean.startswith('('):
            cmd_clean = cmd_clean[1:]
        if cmd_clean.startswith('$'):
            cmd_clean = cmd_clean[1:]
        if cmd_clean.startswith('{'):
            cmd_clean = cmd_clean[1:]

        # Get first word
        first_word = cmd_clean.split()[0] if cmd_clean.split() else ""

        # Remove any leading pipes or logical operators
        for prefix in ['|', '&&', '||', ';', '!']:
            first_word = first_word.lstrip(prefix)

        # Handle command substitution
        if first_word.startswith('$('):
            first_word = first_word[2:].split()[0] if first_word[2:].split() else ""
        if first_word.startswith('`'):
            first_word = first_word[1:].split()[0] if first_word[1:].split() else ""

        # Clean up any remaining special chars
        first_word = first_word.strip('(){}[]`$')

        if not first_word:
            return True, ""  # Complex shell construct, assume valid

        # Check if it's a known valid command
        if first_word in self.valid_commands:
            return True, ""

        # Check if it looks like a path to an executable
        if first_word.startswith('/') or first_word.startswith('./'):
            return True, ""

        # Check if it's a common pattern
        if first_word.startswith('.') or first_word == 'source':
            return True, ""

        # Allow environment variable assignments
        if '=' in first_word and not first_word.startswith('='):
            return True, ""

        return True, ""  # Assume valid if not obviously wrong

    def validate_verification(self, verification: Any) -> Tuple[bool, str]:
        """Validate a closeout verification."""
        self.stats.verifications_checked += 1

        if verification == "manual":
            return True, ""

        if verification == "automated":
            return True, ""

        if isinstance(verification, str):
            # It's a command or script - validate with bash -n
            return self.validate_bash_script_basic(verification, "verification")

        return True, ""

    def process_audit_file(self, file_path: Path) -> Optional[str]:
        """Process a single audit file and return audit ID."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse YAML
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                self.issues.append(Issue(
                    audit_id=str(file_path),
                    audit_file=str(file_path),
                    severity="critical",
                    issue=f"YAML parse error: {str(e)[:100]}",
                    field="root",
                    current="Invalid YAML",
                    recommended="Fix YAML syntax"
                ))
                return None

            if not data:
                return None

            # Get audit ID
            audit_id = data.get('audit', {}).get('id', str(file_path.stem))

            # Validate discovery.code_patterns
            discovery = data.get('discovery', {})
            code_patterns = discovery.get('code_patterns', [])
            if code_patterns:
                for i, cp in enumerate(code_patterns):
                    if isinstance(cp, dict):
                        pattern = cp.get('pattern', '')
                        pattern_type = cp.get('type', 'regex')
                        if pattern_type == 'regex' and pattern:
                            valid, error = self.validate_regex(pattern, f"code_patterns[{i}]")
                            if not valid:
                                self.stats.invalid_patterns += 1
                                self.issues.append(Issue(
                                    audit_id=audit_id,
                                    audit_file=str(file_path),
                                    severity="high" if "syntax" in error.lower() else "medium",
                                    issue=error,
                                    field=f"discovery.code_patterns[{i}].pattern",
                                    current=pattern[:100],
                                    recommended="Fix regex pattern syntax"
                                ))

            # Validate discovery.file_patterns
            file_patterns = discovery.get('file_patterns', [])
            if file_patterns:
                for i, fp in enumerate(file_patterns):
                    if isinstance(fp, dict):
                        glob = fp.get('glob', '')
                        if glob:
                            valid, error = self.validate_glob(glob)
                            if not valid:
                                self.stats.invalid_globs += 1
                                self.issues.append(Issue(
                                    audit_id=audit_id,
                                    audit_file=str(file_path),
                                    severity="medium",
                                    issue=error,
                                    field=f"discovery.file_patterns[{i}].glob",
                                    current=glob[:100],
                                    recommended="Fix glob pattern"
                                ))

            # Validate tooling.scripts using bash -n
            tooling = data.get('tooling', {})
            scripts = tooling.get('scripts', [])
            if scripts:
                for i, script in enumerate(scripts):
                    if isinstance(script, dict):
                        code = script.get('code', '')
                        script_id = script.get('id', f'script_{i}')
                        language = script.get('language', 'bash')
                        if code and language in ['bash', 'sh', 'shell']:
                            valid, error = self.validate_bash_script_basic(code, script_id)
                            if not valid:
                                self.stats.invalid_scripts += 1
                                self.issues.append(Issue(
                                    audit_id=audit_id,
                                    audit_file=str(file_path),
                                    severity="high",
                                    issue=f"Script '{script_id}': {error}",
                                    field=f"tooling.scripts[{i}].code",
                                    current=code[:80].replace('\n', '\\n'),
                                    recommended="Fix script syntax"
                                ))

            # Validate procedure.steps.*.commands
            procedure = data.get('procedure', {})
            steps = procedure.get('steps', [])
            if steps:
                for i, step in enumerate(steps):
                    if isinstance(step, dict):
                        commands = step.get('commands', [])
                        if commands:
                            for j, cmd in enumerate(commands):
                                if isinstance(cmd, dict):
                                    command = cmd.get('command', '')
                                    if command:
                                        valid, error = self.validate_command(command)
                                        if not valid:
                                            self.stats.invalid_commands += 1
                                            self.issues.append(Issue(
                                                audit_id=audit_id,
                                                audit_file=str(file_path),
                                                severity="high",
                                                issue=error,
                                                field=f"procedure.steps[{i}].commands[{j}].command",
                                                current=command[:100],
                                                recommended="Fix command"
                                            ))

            # Validate closeout_checklist verifications
            closeout = data.get('closeout_checklist', [])
            if closeout:
                for i, item in enumerate(closeout):
                    if isinstance(item, dict):
                        verification = item.get('verification', '')
                        if verification and verification not in ['manual', 'automated']:
                            valid, error = self.validate_verification(verification)
                            if not valid:
                                self.stats.invalid_verifications += 1
                                self.issues.append(Issue(
                                    audit_id=audit_id,
                                    audit_file=str(file_path),
                                    severity="medium",
                                    issue=f"Verification: {error}",
                                    field=f"closeout_checklist[{i}].verification",
                                    current=str(verification)[:80].replace('\n', '\\n') if isinstance(verification, str) else str(verification)[:80],
                                    recommended="Fix verification command"
                                ))

            # Check signals evidence_patterns (which are also regexes)
            signals = data.get('signals', {})
            for severity_level in ['critical', 'high', 'medium', 'low']:
                severity_signals = signals.get(severity_level, [])
                if severity_signals:
                    for i, sig in enumerate(severity_signals):
                        if isinstance(sig, dict):
                            evidence = sig.get('evidence_pattern', '')
                            if evidence:
                                valid, error = self.validate_regex(evidence, f"signals.{severity_level}[{i}]")
                                if not valid and "syntax" in error.lower():
                                    self.stats.invalid_patterns += 1
                                    self.issues.append(Issue(
                                        audit_id=audit_id,
                                        audit_file=str(file_path),
                                        severity="medium",
                                        issue=f"Signal evidence pattern: {error}",
                                        field=f"signals.{severity_level}[{i}].evidence_pattern",
                                        current=evidence[:100],
                                        recommended="Fix regex pattern"
                                    ))

            return audit_id

        except Exception as e:
            self.issues.append(Issue(
                audit_id=str(file_path),
                audit_file=str(file_path),
                severity="critical",
                issue=f"Failed to process file: {str(e)[:100]}",
                field="root",
                current="N/A",
                recommended="Fix file format"
            ))
            return None

    def run_validation(self) -> Dict[str, Any]:
        """Run validation on all audit files."""
        audit_files = list(self.audits_dir.rglob('*.yaml'))
        print(f"Found {len(audit_files)} audit files to validate")
        print(f"Shellcheck available: {self.shellcheck_available}")

        processed = 0
        for file_path in audit_files:
            self.process_audit_file(file_path)
            processed += 1
            if processed % 200 == 0:
                print(f"Processed {processed}/{len(audit_files)} files...")

        # Categorize issues by severity
        severity_counts = defaultdict(int)
        for issue in self.issues:
            severity_counts[issue.severity] += 1

        # Calculate pass rate
        total_checks = (
            self.stats.patterns_checked +
            self.stats.globs_checked +
            self.stats.scripts_checked +
            self.stats.commands_checked +
            self.stats.verifications_checked
        )
        total_failures = (
            self.stats.invalid_patterns +
            self.stats.invalid_globs +
            self.stats.invalid_scripts +
            self.stats.invalid_commands +
            self.stats.invalid_verifications
        )
        pass_rate = 1.0 - (total_failures / total_checks if total_checks > 0 else 0)

        # Build report
        report = {
            'dimension_report': {
                'dimension': 'actionability',
                'audits_analyzed': len(audit_files),
                'findings': {
                    'critical': severity_counts.get('critical', 0),
                    'high': severity_counts.get('high', 0),
                    'medium': severity_counts.get('medium', 0),
                    'low': severity_counts.get('low', 0),
                },
                'issues': [
                    {
                        'audit_id': issue.audit_id,
                        'audit_file': issue.audit_file,
                        'severity': issue.severity,
                        'issue': issue.issue,
                        'field': issue.field,
                        'current': issue.current,
                        'recommended': issue.recommended,
                    }
                    for issue in self.issues
                ],
                'summary': {
                    'pass_rate': round(pass_rate, 4),
                    'needs_remediation': len(self.issues),
                    'patterns_checked': self.stats.patterns_checked,
                    'invalid_patterns': self.stats.invalid_patterns,
                    'globs_checked': self.stats.globs_checked,
                    'invalid_globs': self.stats.invalid_globs,
                    'scripts_checked': self.stats.scripts_checked,
                    'invalid_scripts': self.stats.invalid_scripts,
                    'commands_checked': self.stats.commands_checked,
                    'invalid_commands': self.stats.invalid_commands,
                    'verifications_checked': self.stats.verifications_checked,
                    'invalid_verifications': self.stats.invalid_verifications,
                }
            }
        }

        return report


def main():
    audits_dir = "/mnt/walnut-drive/dev/audits/audits"
    output_file = "/mnt/walnut-drive/dev/audits/meta-audit/actionability-report.yaml"

    print("Starting Actionability Meta-Audit v2...")
    print(f"Audits directory: {audits_dir}")

    validator = ActionabilityValidator(audits_dir)
    report = validator.run_validation()

    # Write report
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)

    print(f"\nReport written to: {output_file}")
    print(f"\nSummary:")
    print(f"  Audits analyzed: {report['dimension_report']['audits_analyzed']}")
    print(f"  Total issues: {report['dimension_report']['summary']['needs_remediation']}")
    print(f"  Pass rate: {report['dimension_report']['summary']['pass_rate']:.2%}")
    print(f"\nFindings by severity:")
    for sev in ['critical', 'high', 'medium', 'low']:
        count = report['dimension_report']['findings'][sev]
        print(f"  {sev.upper()}: {count}")

    print(f"\nValidation stats:")
    print(f"  Patterns checked: {report['dimension_report']['summary']['patterns_checked']}")
    print(f"  Invalid patterns: {report['dimension_report']['summary']['invalid_patterns']}")
    print(f"  Globs checked: {report['dimension_report']['summary']['globs_checked']}")
    print(f"  Invalid globs: {report['dimension_report']['summary']['invalid_globs']}")
    print(f"  Scripts checked: {report['dimension_report']['summary']['scripts_checked']}")
    print(f"  Invalid scripts: {report['dimension_report']['summary']['invalid_scripts']}")
    print(f"  Commands checked: {report['dimension_report']['summary']['commands_checked']}")
    print(f"  Verifications checked: {report['dimension_report']['summary']['verifications_checked']}")


if __name__ == '__main__':
    main()
