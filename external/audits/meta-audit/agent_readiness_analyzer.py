#!/usr/bin/env python3
"""
Agent Readiness Meta-Audit Analyzer
Analyzes all audit files for automation compatibility and agent-readiness.
"""

import os
import sys
import yaml
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional

# Known agent-compatible tools
KNOWN_TOOLS = {
    # Static analysis
    'grep', 'rg', 'ripgrep', 'semgrep', 'eslint', 'tslint', 'prettier',
    'pylint', 'flake8', 'mypy', 'black', 'isort', 'bandit', 'safety',
    'shellcheck', 'hadolint', 'trivy', 'snyk', 'npm audit', 'yarn audit',
    'sonarqube', 'sonar-scanner', 'codeql', 'gosec', 'staticcheck',
    'golangci-lint', 'cargo clippy', 'rustfmt', 'rubocop', 'brakeman',
    # Build/Test tools
    'npm', 'yarn', 'pnpm', 'pip', 'poetry', 'cargo', 'go', 'mvn', 'gradle',
    'jest', 'pytest', 'mocha', 'vitest', 'playwright', 'cypress', 'selenium',
    'coverage.py', 'nyc', 'istanbul', 'jacoco', 'lcov',
    # Git/Version control
    'git', 'gh', 'git-secrets', 'gitleaks', 'trufflehog',
    # Security tools
    'OWASP ZAP', 'nikto', 'nmap', 'nuclei', 'sqlmap', 'burp',
    # Infrastructure
    'docker', 'kubectl', 'helm', 'terraform', 'ansible', 'packer',
    'aws', 'gcloud', 'az', 'pulumi', 'cloudformation',
    # Documentation
    'jsdoc', 'typedoc', 'sphinx', 'mkdocs', 'doxygen',
    # Other utilities
    'jq', 'yq', 'curl', 'wget', 'find', 'awk', 'sed', 'xargs',
    'tree', 'wc', 'sort', 'uniq', 'diff', 'cat', 'head', 'tail',
}

# Manual-only indicators
MANUAL_BLOCKERS = [
    'human judgment required',
    'manual review',
    'manual verification',
    'manual inspection',
    'requires expert',
    'visual inspection',
    'subjective assessment',
    'interview',
    'meeting',
    'discussion',
    'stakeholder',
    'approval required',
    'sign-off',
    'physical access',
    'in-person',
    'human-in-the-loop',
    'cannot be automated',
    'not automatable',
]


class AgentReadinessAnalyzer:
    def __init__(self, audits_dir: str):
        self.audits_dir = Path(audits_dir)
        self.results = {
            'total_files': 0,
            'parsed_files': 0,
            'parse_errors': [],
            'automation_distribution': defaultdict(int),
            'cognitive_modes': defaultdict(int),
            'tool_usage': defaultdict(int),
            'manual_blockers': defaultdict(list),
            'issues': [],
            'readiness_scores': defaultdict(int),
            'files_by_category': defaultdict(int),
            'category_readiness': defaultdict(lambda: defaultdict(int)),
            'steps_with_commands': 0,
            'steps_without_commands': 0,
            'total_steps': 0,
            'closeout_items': {'automated': 0, 'manual': 0, 'total': 0},
            'tool_availability': {'known': 0, 'unknown': 0},
            'fully_automatable_audits': [],
            'automation_hooks': defaultdict(int),
        }

    def analyze_all(self) -> Dict[str, Any]:
        """Analyze all audit YAML files."""
        yaml_files = list(self.audits_dir.rglob('*.yaml'))
        self.results['total_files'] = len(yaml_files)

        for yaml_file in yaml_files:
            self._analyze_file(yaml_file)

        return self._generate_report()

    def _analyze_file(self, filepath: Path):
        """Analyze a single audit file for agent-readiness."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)

            if not data or 'audit' not in data:
                return

            self.results['parsed_files'] += 1
            audit_id = data.get('audit', {}).get('id', filepath.stem)
            category = data.get('audit', {}).get('category', 'unknown')
            self.results['files_by_category'][category] += 1

            # Analyze automation level
            automation = self._check_automation_level(data)
            self.results['automation_distribution'][automation] += 1

            # Analyze cognitive mode
            cognitive_mode = self._check_cognitive_mode(data)
            self.results['cognitive_modes'][cognitive_mode] += 1

            # Analyze tooling
            tools = self._check_tooling(data)
            for tool in tools:
                self.results['tool_usage'][tool] += 1
                # Check if tool is known
                tool_lower = tool.lower()
                if any(known in tool_lower for known in KNOWN_TOOLS):
                    self.results['tool_availability']['known'] += 1
                else:
                    self.results['tool_availability']['unknown'] += 1

            # Analyze procedure steps for commands
            self._analyze_procedure_steps(data)

            # Analyze closeout checklist
            self._analyze_closeout_checklist(data)

            # Analyze automation hooks
            self._analyze_automation_hooks(data, content)

            # Check for manual blockers
            blockers = self._check_manual_blockers(data, content)
            for blocker_type, details in blockers.items():
                if details:
                    self.results['manual_blockers'][blocker_type].append({
                        'audit_id': audit_id,
                        'details': details
                    })

            # Calculate readiness score
            score = self._calculate_readiness_score(data, content, automation, blockers)
            self.results['readiness_scores'][score] += 1
            self.results['category_readiness'][category][score] += 1

            if score == 'fully_automatable':
                self.results['fully_automatable_audits'].append(audit_id)

            # Generate issues for non-ready audits
            issues = self._generate_issues(audit_id, data, automation, blockers, filepath)
            self.results['issues'].extend(issues)

        except yaml.YAMLError as e:
            self.results['parse_errors'].append({
                'file': str(filepath),
                'error': f"YAML parse error: {str(e)[:100]}"
            })
        except Exception as e:
            self.results['parse_errors'].append({
                'file': str(filepath),
                'error': f"Error: {str(e)[:100]}"
            })

    def _analyze_procedure_steps(self, data: Dict):
        """Analyze procedure steps for command presence."""
        procedure = data.get('procedure', {})
        steps = procedure.get('steps', [])

        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict):
                    self.results['total_steps'] += 1
                    if step.get('commands'):
                        self.results['steps_with_commands'] += 1
                    else:
                        self.results['steps_without_commands'] += 1

    def _analyze_closeout_checklist(self, data: Dict):
        """Analyze closeout checklist for automation."""
        closeout = data.get('closeout_checklist', [])
        if isinstance(closeout, list):
            for item in closeout:
                if isinstance(item, dict):
                    self.results['closeout_items']['total'] += 1
                    verification = item.get('verification', '')
                    if verification == 'manual':
                        self.results['closeout_items']['manual'] += 1
                    else:
                        self.results['closeout_items']['automated'] += 1

    def _analyze_automation_hooks(self, data: Dict, content: str):
        """Analyze presence of automation hooks."""
        # Check for command templates in procedure
        procedure = data.get('procedure', {})
        steps = procedure.get('steps', [])
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get('commands'):
                    self.results['automation_hooks']['procedure_commands'] += 1
                    break

        # Check for scripts in tooling
        tooling = data.get('tooling', {})
        if tooling.get('scripts'):
            self.results['automation_hooks']['inline_scripts'] += 1

        # Check for discovery patterns
        discovery = data.get('discovery', {})
        if discovery.get('file_patterns'):
            self.results['automation_hooks']['file_patterns'] += 1
        if discovery.get('code_patterns'):
            self.results['automation_hooks']['code_patterns'] += 1

        # Check for signals with evidence patterns
        signals = data.get('signals', {})
        has_evidence = False
        for severity in ['critical', 'high', 'medium', 'low']:
            sigs = signals.get(severity, [])
            if isinstance(sigs, list):
                for sig in sigs:
                    if isinstance(sig, dict) and sig.get('evidence_pattern'):
                        has_evidence = True
                        break
        if has_evidence:
            self.results['automation_hooks']['evidence_patterns'] += 1

    def _check_automation_level(self, data: Dict) -> str:
        """Check the automation level specified in the audit."""
        execution = data.get('execution', {})
        automatable = execution.get('automatable', 'unspecified')

        # Normalize values
        if automatable in ['yes', 'full', True, 'true']:
            return 'full'
        elif automatable in ['partial', 'hybrid']:
            return 'partial'
        elif automatable in ['no', 'manual', False, 'false']:
            return 'manual'
        else:
            return 'unspecified'

    def _check_cognitive_mode(self, data: Dict) -> str:
        """Check if cognitive mode is specified in procedure context."""
        procedure = data.get('procedure', {})
        context = procedure.get('context', {})
        return context.get('cognitive_mode', 'unspecified')

    def _check_tooling(self, data: Dict) -> List[str]:
        """Extract tools referenced in the audit."""
        tools = []
        tooling = data.get('tooling', {})

        # Check static_analysis tools
        static_tools = tooling.get('static_analysis', [])
        if isinstance(static_tools, list):
            for tool_entry in static_tools:
                if isinstance(tool_entry, dict):
                    tool_name = tool_entry.get('tool', '')
                    if tool_name:
                        tools.append(tool_name.lower())
                elif isinstance(tool_entry, str):
                    tools.append(tool_entry.lower())

        # Check scripts
        scripts = tooling.get('scripts', [])
        if isinstance(scripts, list):
            for script in scripts:
                if isinstance(script, dict):
                    lang = script.get('language', '')
                    if lang:
                        tools.append(f"script:{lang}")

        return tools

    def _check_manual_blockers(self, data: Dict, content: str) -> Dict[str, List[str]]:
        """Check for elements that block full automation."""
        blockers = defaultdict(list)
        content_lower = content.lower()

        # Check closeout_checklist for manual verification
        closeout = data.get('closeout_checklist', [])
        if isinstance(closeout, list):
            for item in closeout:
                if isinstance(item, dict):
                    verification = item.get('verification', '')
                    if verification == 'manual':
                        blockers['manual_verification'].append(
                            item.get('item', 'Unknown checklist item')
                        )

        # Check for human judgment language
        for blocker_phrase in MANUAL_BLOCKERS:
            if blocker_phrase in content_lower:
                blockers['human_language'].append(blocker_phrase)

        # Check requires_runtime
        audit_section = data.get('audit', {})
        if audit_section.get('requires_runtime', False):
            blockers['requires_runtime'].append('Audit requires runtime environment')

        # Check for destructive operations
        if audit_section.get('destructive', False):
            blockers['destructive'].append('Audit may be destructive')

        return dict(blockers)

    def _calculate_readiness_score(self, data: Dict, content: str,
                                   automation: str, blockers: Dict) -> str:
        """Calculate overall agent-readiness score."""
        # Start with base score from automation level
        if automation == 'full':
            score = 4
        elif automation == 'partial':
            score = 3
        elif automation == 'manual':
            score = 1
        else:
            score = 2

        # Deduct for blockers
        if blockers.get('manual_verification'):
            score -= 1
        if blockers.get('human_language'):
            score -= 0.5
        if blockers.get('requires_runtime'):
            score -= 0.5
        if blockers.get('destructive'):
            score -= 0.5

        # Bonus for having commands in procedure
        procedure = data.get('procedure', {})
        steps = procedure.get('steps', [])
        has_commands = False
        for step in steps if isinstance(steps, list) else []:
            if isinstance(step, dict) and step.get('commands'):
                has_commands = True
                break

        if has_commands:
            score += 0.5

        # Map score to category
        if score >= 4:
            return 'fully_automatable'
        elif score >= 3:
            return 'mostly_automatable'
        elif score >= 2:
            return 'partially_automatable'
        else:
            return 'requires_human'

    def _generate_issues(self, audit_id: str, data: Dict, automation: str,
                        blockers: Dict, filepath: Path) -> List[Dict]:
        """Generate issues for problematic audits."""
        issues = []

        # Issue for unspecified automation
        if automation == 'unspecified':
            issues.append({
                'audit_id': audit_id,
                'severity': 'medium',
                'issue': 'Automation level not specified',
                'field': 'execution.automatable',
                'blocker': 'Cannot determine if audit is agent-executable',
                'recommended': 'Add execution.automatable field with value: full, partial, or manual'
            })

        # Issue for manual audits without explanation
        if automation == 'manual':
            issues.append({
                'audit_id': audit_id,
                'severity': 'low',
                'issue': 'Audit marked as manual',
                'field': 'execution.automatable',
                'blocker': 'Audit requires human execution',
                'recommended': 'Review if any steps can be automated'
            })

        # Issue for manual verification in closeout
        if blockers.get('manual_verification'):
            for item in blockers['manual_verification'][:3]:
                issues.append({
                    'audit_id': audit_id,
                    'severity': 'high',
                    'issue': 'Closeout checklist requires manual verification',
                    'field': 'closeout_checklist',
                    'blocker': f'Manual verification: {item}',
                    'recommended': 'Add automated verification command or script'
                })

        # Issue for missing cognitive mode
        procedure = data.get('procedure', {})
        context = procedure.get('context', {})
        if not context.get('cognitive_mode'):
            issues.append({
                'audit_id': audit_id,
                'severity': 'low',
                'issue': 'Cognitive mode not specified',
                'field': 'procedure.context.cognitive_mode',
                'blocker': 'Agent cannot determine appropriate processing mode',
                'recommended': 'Add cognitive_mode: evaluative, critical, analytical, or systematic'
            })

        # Issue for destructive audits
        if blockers.get('destructive'):
            issues.append({
                'audit_id': audit_id,
                'severity': 'critical',
                'issue': 'Audit marked as destructive',
                'field': 'audit.destructive',
                'blocker': 'Destructive operations require human supervision',
                'recommended': 'Add safeguards or convert to dry-run mode with optional execution'
            })

        # Issue for missing commands in steps
        steps = procedure.get('steps', [])
        steps_without_commands = 0
        for step in steps if isinstance(steps, list) else []:
            if isinstance(step, dict):
                if not step.get('commands') and not step.get('verification'):
                    steps_without_commands += 1

        if steps_without_commands > 0 and automation == 'full':
            issues.append({
                'audit_id': audit_id,
                'severity': 'medium',
                'issue': f'{steps_without_commands} procedure steps lack executable commands',
                'field': 'procedure.steps[].commands',
                'blocker': 'Steps without commands cannot be automated',
                'recommended': 'Add command templates for each step'
            })

        return issues

    def _generate_report(self) -> Dict[str, Any]:
        """Generate the final report in the required format."""
        # Count findings by severity
        findings_count = defaultdict(int)
        for issue in self.results['issues']:
            findings_count[issue['severity']] += 1

        # Aggregate manual blockers
        blocker_summary = []
        for blocker_type, instances in self.results['manual_blockers'].items():
            example_ids = [inst['audit_id'] for inst in instances[:5]]
            blocker_summary.append({
                'type': blocker_type,
                'count': len(instances),
                'example_audits': example_ids
            })

        # Sort issues by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_issues = sorted(
            self.results['issues'],
            key=lambda x: severity_order.get(x['severity'], 4)
        )

        # Calculate pass rate (fully + mostly automatable)
        total_scored = sum(self.results['readiness_scores'].values())
        ready_count = (
            self.results['readiness_scores']['fully_automatable'] +
            self.results['readiness_scores']['mostly_automatable']
        )
        pass_rate = ready_count / total_scored if total_scored > 0 else 0.0

        # Calculate category breakdown
        category_summary = {}
        for category, scores in self.results['category_readiness'].items():
            total = sum(scores.values())
            fully_ready = scores.get('fully_automatable', 0) + scores.get('mostly_automatable', 0)
            category_summary[category] = {
                'total_audits': total,
                'fully_ready': fully_ready,
                'pass_rate': round(fully_ready / total, 3) if total > 0 else 0.0,
                'breakdown': dict(scores)
            }

        # Sort categories by pass rate
        sorted_categories = sorted(
            category_summary.items(),
            key=lambda x: x[1]['pass_rate'],
            reverse=True
        )

        # Steps analysis
        steps_automation_rate = (
            self.results['steps_with_commands'] / self.results['total_steps']
            if self.results['total_steps'] > 0 else 0.0
        )

        # Closeout analysis
        closeout_automation_rate = (
            self.results['closeout_items']['automated'] / self.results['closeout_items']['total']
            if self.results['closeout_items']['total'] > 0 else 0.0
        )

        report = {
            'dimension_report': {
                'dimension': 'agent_readiness',
                'audits_analyzed': self.results['parsed_files'],
                'parse_errors': len(self.results['parse_errors']),

                'findings': {
                    'critical': findings_count['critical'],
                    'high': findings_count['high'],
                    'medium': findings_count['medium'],
                    'low': findings_count['low'],
                },

                'automation_distribution': dict(self.results['automation_distribution']),

                'cognitive_mode_distribution': dict(self.results['cognitive_modes']),

                'readiness_scores': dict(self.results['readiness_scores']),

                'procedure_analysis': {
                    'total_steps': self.results['total_steps'],
                    'steps_with_commands': self.results['steps_with_commands'],
                    'steps_without_commands': self.results['steps_without_commands'],
                    'automation_rate': round(steps_automation_rate, 3),
                },

                'closeout_analysis': {
                    'total_items': self.results['closeout_items']['total'],
                    'automated_verification': self.results['closeout_items']['automated'],
                    'manual_verification': self.results['closeout_items']['manual'],
                    'automation_rate': round(closeout_automation_rate, 3),
                },

                'automation_hooks': dict(self.results['automation_hooks']),

                'tool_availability': {
                    'known_tools': self.results['tool_availability']['known'],
                    'unknown_tools': self.results['tool_availability']['unknown'],
                },

                'tool_usage_top_20': dict(
                    sorted(self.results['tool_usage'].items(),
                           key=lambda x: x[1], reverse=True)[:20]
                ),

                'category_readiness': {
                    'best_categories': [
                        {'category': cat, **data}
                        for cat, data in sorted_categories[:10]
                    ],
                    'worst_categories': [
                        {'category': cat, **data}
                        for cat, data in sorted_categories[-10:]
                    ],
                },

                'issues': sorted_issues[:100],  # Top 100 issues

                'manual_blockers': blocker_summary,

                'fully_automatable_audits': self.results['fully_automatable_audits'][:50],

                'summary': {
                    'pass_rate': round(pass_rate, 3),
                    'fully_ready_for_agents': self.results['readiness_scores']['fully_automatable'],
                    'mostly_ready_for_agents': self.results['readiness_scores']['mostly_automatable'],
                    'partially_automatable': self.results['readiness_scores']['partially_automatable'],
                    'requires_human': self.results['readiness_scores']['requires_human'],
                    'needs_adaptation': (
                        self.results['readiness_scores']['partially_automatable'] +
                        self.results['readiness_scores']['requires_human']
                    ),
                    'categories_analyzed': len(self.results['files_by_category']),
                    'procedure_step_automation_rate': round(steps_automation_rate, 3),
                    'closeout_automation_rate': round(closeout_automation_rate, 3),
                }
            }
        }

        return report


def main():
    audits_dir = '/mnt/walnut-drive/dev/audits/audits'
    output_file = '/mnt/walnut-drive/dev/audits/meta-audit/agent-readiness-report.yaml'

    print(f"Analyzing audit files in: {audits_dir}")

    analyzer = AgentReadinessAnalyzer(audits_dir)
    report = analyzer.analyze_all()

    # Write report
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"\nReport written to: {output_file}")
    print(f"\n=== Summary ===")
    summary = report['dimension_report']['summary']
    print(f"Audits analyzed: {report['dimension_report']['audits_analyzed']}")
    print(f"Pass rate: {summary['pass_rate']*100:.1f}%")
    print(f"Fully ready: {summary['fully_ready_for_agents']}")
    print(f"Mostly ready: {summary['mostly_ready_for_agents']}")
    print(f"Partially automatable: {summary['partially_automatable']}")
    print(f"Requires human: {summary['requires_human']}")

    print(f"\n=== Automation Distribution ===")
    for level, count in report['dimension_report']['automation_distribution'].items():
        print(f"  {level}: {count}")

    print(f"\n=== Procedure Steps ===")
    proc = report['dimension_report']['procedure_analysis']
    print(f"  Total steps: {proc['total_steps']}")
    print(f"  With commands: {proc['steps_with_commands']} ({proc['automation_rate']*100:.1f}%)")
    print(f"  Without commands: {proc['steps_without_commands']}")

    print(f"\n=== Closeout Checklist ===")
    close = report['dimension_report']['closeout_analysis']
    print(f"  Total items: {close['total_items']}")
    print(f"  Automated: {close['automated_verification']} ({close['automation_rate']*100:.1f}%)")
    print(f"  Manual: {close['manual_verification']}")

    print(f"\n=== Findings ===")
    findings = report['dimension_report']['findings']
    print(f"  Critical: {findings['critical']}")
    print(f"  High: {findings['high']}")
    print(f"  Medium: {findings['medium']}")
    print(f"  Low: {findings['low']}")


if __name__ == '__main__':
    main()
