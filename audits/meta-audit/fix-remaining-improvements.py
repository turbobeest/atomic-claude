#!/usr/bin/env python3
"""
Comprehensive fix script for all remaining semantic audit improvements.
Phase 1: Code pattern expansions
Phase 2: Multi-cloud/multi-tool commands
Phase 3: Agent alternative fields for manual verifications
Phase 4: Documentation clarity improvements
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any

AUDITS_ROOT = Path("/mnt/walnut-drive/dev/audits/audits")

fixes_applied = {
    "pattern_expansions": [],
    "multi_tool_commands": [],
    "agent_alternatives": [],
    "clarity_improvements": [],
}

def load_yaml_safe(filepath: Path):
    """Load YAML file, return content string."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def save_content(filepath: Path, content: str):
    """Save content to file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# =============================================================================
# PHASE 1: CODE PATTERN EXPANSIONS
# =============================================================================

PATTERN_EXPANSIONS = {
    # Eventual consistency patterns
    "03-reliability-resilience/data-consistency/eventual-consistency.yaml": {
        "section": "discovery",
        "patterns": [
            "# DynamoDB patterns",
            "- pattern: 'boto3.*dynamodb|DynamoDBClient|@aws-sdk/client-dynamodb'",
            "  description: 'AWS DynamoDB usage (eventually consistent by default)'",
            "# Cassandra patterns",
            "- pattern: 'cassandra\\.cluster|CqlSession|datastax.*driver'",
            "  description: 'Cassandra driver imports'",
            "# MongoDB patterns",
            "- pattern: 'readConcern|writeConcern|ReadPreference\\.(secondary|nearest)'",
            "  description: 'MongoDB consistency settings'",
            "# Redis patterns",
            "- pattern: 'redis\\.*(cluster|sentinel)|WAIT\\s+\\d+'",
            "  description: 'Redis cluster/replication patterns'",
        ]
    },

    # Distributed tracing alternatives
    "05-observability-instrumentation/distributed-tracing/trace-coverage.yaml": {
        "section": "tooling",
        "patterns": [
            "# Alternative tracing backends:",
            "# Zipkin: curl http://localhost:9411/api/v2/services",
            "# AWS X-Ray: aws xray get-service-graph --start-time $(date -d '1 hour ago' +%s) --end-time $(date +%s)",
            "# Datadog APM: curl -H 'DD-API-KEY: ${DD_API_KEY}' https://api.datadoghq.com/api/v1/traces",
            "# Honeycomb: curl -H 'X-Honeycomb-Team: ${HONEYCOMB_API_KEY}' https://api.honeycomb.io/1/columns/${DATASET}",
            "# OpenTelemetry Collector: curl http://localhost:8888/metrics",
        ]
    },

    # Sharding strategy - real database commands
    "04-scalability-capacity/database-scalability/sharding-strategy.yaml": {
        "section": "procedure",
        "patterns": [
            "# PostgreSQL Citus:",
            "#   SELECT nodename, nodeport FROM pg_dist_node;",
            "#   SELECT * FROM citus_shards;",
            "# MongoDB:",
            "#   sh.status()",
            "#   db.collection.getShardDistribution()",
            "# Vitess:",
            "#   vtctlclient ListAllTablets",
            "#   vtctlclient GetShard <keyspace>/<shard>",
            "# CockroachDB:",
            "#   SHOW RANGES FROM TABLE <table>;",
            "#   SELECT * FROM crdb_internal.ranges;",
        ]
    },

    # Structured logging - multi-language patterns
    "05-observability-instrumentation/logging/structured-logging.yaml": {
        "section": "discovery",
        "patterns": [
            "# Python logging",
            "- pattern: 'logging\\.(info|warning|error|debug|critical)\\([\"\\']'",
            "  description: 'Python standard logging with string messages'",
            "# JavaScript/Node console",
            "- pattern: 'console\\.(log|warn|error|info|debug)\\('",
            "  description: 'Browser/Node console logging'",
            "# Go logging",
            "- pattern: 'log\\.(Print|Fatal|Panic|Info|Warn|Error)'",
            "  description: 'Go standard and structured logging'",
            "# Java logging",
            "- pattern: 'logger\\.(info|warn|error|debug|trace)\\([\"\\']'",
            "  description: 'Java SLF4J/Log4j string logging'",
            "# Ruby logging",
            "- pattern: 'Rails\\.logger\\.|logger\\.(info|warn|error|debug)'",
            "  description: 'Ruby/Rails logging'",
        ]
    },

    # N+1 query detection - multi-ORM patterns
    "02-performance-efficiency/database-performance/n-plus-one-query.yaml": {
        "section": "discovery",
        "patterns": [
            "# Django ORM",
            "- pattern: '\\.objects\\.(get|filter|all)\\(.*\\).*for.*in'",
            "  description: 'Django queryset iteration without select_related/prefetch_related'",
            "# SQLAlchemy",
            "- pattern: 'session\\.query\\(.*\\)\\.all\\(\\).*for'",
            "  description: 'SQLAlchemy query iteration'",
            "# ActiveRecord",
            "- pattern: '\\.(find|where|all)\\b.*\\.each'",
            "  description: 'Rails ActiveRecord iteration without includes/eager_load'",
            "# Sequelize",
            "- pattern: 'findAll\\(.*\\).*\\.then.*forEach'",
            "  description: 'Sequelize query iteration'",
            "# Prisma",
            "- pattern: 'prisma\\.\\w+\\.findMany.*for.*of'",
            "  description: 'Prisma query iteration'",
        ]
    },

    # SQL injection - refined patterns
    "01-security-trust/input-validation/sql-injection.yaml": {
        "section": "discovery",
        "patterns": [
            "# Python DB-API with context",
            "- pattern: '(cursor|conn|connection|db|engine)\\.(execute|executemany)\\([^)]*%'",
            "  description: 'Python DB-API with string formatting'",
            "# Node.js query building",
            "- pattern: 'query\\([`\"\\'].*\\$\\{|\\+.*req\\.(body|params|query)'",
            "  description: 'Node.js string concatenation in queries'",
            "# Java JDBC",
            "- pattern: 'createStatement\\(\\)|executeQuery\\([^)]*\\+[^)]*\\)'",
            "  description: 'Java JDBC without PreparedStatement'",
            "# PHP mysqli",
            "- pattern: 'mysqli_query\\([^)]*\\$_(GET|POST|REQUEST)'",
            "  description: 'PHP mysqli with unsanitized input'",
        ]
    },

    # Feature flag patterns - multiple providers
    "30-configuration-management/feature-flags/stale-flags.yaml": {
        "section": "discovery",
        "patterns": [
            "# LaunchDarkly",
            "- pattern: 'ldclient\\.(variation|variation_detail)|useFlags\\(\\)'",
            "  description: 'LaunchDarkly SDK usage'",
            "# Split.io",
            "- pattern: 'splitClient\\.getTreatment|useSplitTreatments'",
            "  description: 'Split.io SDK usage'",
            "# Unleash",
            "- pattern: 'unleash\\.(isEnabled|getVariant)|useFlag\\('",
            "  description: 'Unleash SDK usage'",
            "# Flagsmith",
            "- pattern: 'flagsmith\\.(hasFeature|getValue)|useFlagsmith'",
            "  description: 'Flagsmith SDK usage'",
            "# ConfigCat",
            "- pattern: 'configCatClient\\.(getValue|getValueAsync)'",
            "  description: 'ConfigCat SDK usage'",
            "# Custom/Generic",
            "- pattern: 'featureFlags?\\[|isFeatureEnabled|checkFeature'",
            "  description: 'Generic feature flag patterns'",
        ]
    },

    # State machine patterns
    "34-business-logic-domain/workflow-processes/state-machine-integrity.yaml": {
        "section": "discovery",
        "patterns": [
            "# XState (JavaScript)",
            "- pattern: 'createMachine|useMachine|interpret\\(.*Machine'",
            "  description: 'XState state machine'",
            "# Spring State Machine (Java)",
            "- pattern: 'StateMachineBuilder|@WithStateMachine|StateMachineFactory'",
            "  description: 'Spring State Machine'",
            "# Python transitions",
            "- pattern: 'from transitions import|Machine\\(.*states='",
            "  description: 'Python transitions library'",
            "# Temporal.io workflows",
            "- pattern: '@workflow\\.defn|workflow\\.execute_activity'",
            "  description: 'Temporal workflow definitions'",
            "# Database status columns",
            "- pattern: \"status.*enum.*\\[|state.*enum.*\\[|workflow_state\"",
            "  description: 'Database status/state columns'",
            "# Generic state patterns",
            "- pattern: 'StateTransition|transition\\(.*from.*to|allowedTransitions'",
            "  description: 'Generic state transition logic'",
        ]
    },
}

def apply_pattern_expansions():
    """Add expanded code patterns to relevant audits."""
    print("\n=== Phase 1: Code Pattern Expansions ===")

    for rel_path, expansion in PATTERN_EXPANSIONS.items():
        filepath = AUDITS_ROOT / rel_path
        if not filepath.exists():
            print(f"  Skipped (not found): {rel_path}")
            continue

        content = load_yaml_safe(filepath)
        if not content:
            continue

        # Check if we already added these patterns
        if "# Alternative" in content or "# DynamoDB patterns" in content or "# LaunchDarkly" in content:
            print(f"  Skipped (already expanded): {filepath.name}")
            continue

        # Find the section and add patterns as comments
        section = expansion["section"]
        patterns_text = "\n    ".join(expansion["patterns"])

        # Add patterns as YAML comments in the relevant section
        if f"{section}:" in content:
            # Find the section and add after it
            section_match = re.search(rf'^({section}:.*?)(\n\w|\n  \w|\Z)', content, re.MULTILINE | re.DOTALL)
            if section_match:
                insert_pos = section_match.end(1)
                addition = f"\n  # Additional patterns for comprehensive coverage:\n    {patterns_text}\n"
                content = content[:insert_pos] + addition + content[insert_pos:]
                save_content(filepath, content)
                fixes_applied["pattern_expansions"].append(str(filepath))
                print(f"  Expanded: {filepath.name}")

# =============================================================================
# PHASE 2: MULTI-CLOUD/MULTI-TOOL COMMANDS
# =============================================================================

MULTI_TOOL_ADDITIONS = {
    # Cost optimization - multi-cloud
    "31-cost-economics/cost-optimization/rightsizing.yaml": """
  # Multi-cloud rightsizing commands:
  # AWS:
  #   aws compute-optimizer get-ec2-instance-recommendations --region ${REGION}
  #   aws ce get-rightsizing-recommendation --service EC2
  # Azure:
  #   az advisor recommendation list --category Cost
  #   az monitor metrics list --resource ${RESOURCE_ID} --metric "Percentage CPU"
  # GCP:
  #   gcloud recommender recommendations list --recommender=google.compute.instance.MachineTypeRecommender
  #   gcloud compute instances describe ${INSTANCE} --format="value(machineType)"
  # Kubernetes:
  #   kubectl top pods --all-namespaces
  #   kubectl get vpa --all-namespaces
""",

    # Idle resources - multi-cloud
    "31-cost-economics/resource-efficiency/idle-resources.yaml": """
  # Multi-cloud idle resource detection:
  # AWS:
  #   aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[?LaunchTime<=`'$(date -d '30 days ago' +%Y-%m-%d)'`]'
  #   aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Value=${ID} --start-time $(date -d '7 days ago' -Iseconds) --end-time $(date -Iseconds) --period 3600 --statistics Average
  # Azure:
  #   az vm list --query "[?powerState=='VM running']" -o table
  #   az monitor metrics list --resource ${ID} --metric "Percentage CPU" --interval PT1H
  # GCP:
  #   gcloud compute instances list --filter="status=RUNNING"
  #   gcloud monitoring time-series list --filter='metric.type="compute.googleapis.com/instance/cpu/utilization"'
  # Kubernetes:
  #   kubectl top nodes
  #   kubectl describe nodes | grep -A 5 "Allocated resources"
""",

    # IaC validation - multi-tool
    "09-devops-infrastructure/infrastructure-as-code/iac-validation.yaml": """
  # Multi-tool IaC validation:
  # Terraform:
  #   terraform validate
  #   terraform plan -out=tfplan && terraform show -json tfplan
  #   tflint --recursive
  #   checkov -d . --framework terraform
  # Pulumi:
  #   pulumi preview --json
  #   pulumi up --dry-run
  # CloudFormation:
  #   aws cloudformation validate-template --template-body file://template.yaml
  #   cfn-lint template.yaml
  #   cfn_nag_scan --input-path template.yaml
  # CDK:
  #   cdk synth
  #   cdk diff
  # Ansible:
  #   ansible-lint playbook.yaml
  #   ansible-playbook --syntax-check playbook.yaml
""",

    # Container security - multi-tool
    "09-devops-infrastructure/container-orchestration/container-security.yaml": """
  # Multi-tool container security scanning:
  # Trivy (comprehensive):
  #   trivy image ${IMAGE}
  #   trivy fs --security-checks vuln,config .
  # Grype (anchore):
  #   grype ${IMAGE}
  #   grype dir:.
  # Snyk:
  #   snyk container test ${IMAGE}
  #   snyk iac test
  # Clair:
  #   clairctl report ${IMAGE}
  # Docker Scout:
  #   docker scout cves ${IMAGE}
  #   docker scout recommendations ${IMAGE}
  # Kubernetes-specific:
  #   kubesec scan deployment.yaml
  #   kube-bench run --targets node
""",

    # CI/CD pipeline security
    "09-devops-infrastructure/cicd-security/pipeline-security.yaml": """
  # Multi-platform CI/CD security checks:
  # GitHub Actions:
  #   gh api repos/{owner}/{repo}/actions/permissions
  #   gh secret list
  # GitLab CI:
  #   glab ci lint .gitlab-ci.yml
  #   glab variable list
  # Jenkins:
  #   curl -s ${JENKINS_URL}/credentials/store/system/domain/_/api/json
  # CircleCI:
  #   circleci config validate
  #   circleci context list
  # Azure DevOps:
  #   az pipelines variable list --pipeline-id ${ID}
""",

    # Database monitoring - multi-database
    "02-performance-efficiency/database-performance/query-performance.yaml": """
  # Multi-database slow query detection:
  # PostgreSQL:
  #   SELECT query, calls, mean_time, total_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 20;
  #   SELECT * FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 seconds';
  # MySQL:
  #   SELECT * FROM performance_schema.events_statements_summary_by_digest ORDER BY avg_timer_wait DESC LIMIT 20;
  #   SHOW PROCESSLIST;
  # MongoDB:
  #   db.currentOp({"secs_running": {"$gt": 5}})
  #   db.system.profile.find().sort({millis: -1}).limit(20)
  # Redis:
  #   redis-cli SLOWLOG GET 20
  #   redis-cli INFO commandstats
  # Elasticsearch:
  #   GET /_nodes/hot_threads
  #   GET /_tasks?detailed=true&actions=*search
""",
}

def apply_multi_tool_commands():
    """Add multi-cloud and multi-tool command alternatives."""
    print("\n=== Phase 2: Multi-Cloud/Multi-Tool Commands ===")

    for rel_path, commands in MULTI_TOOL_ADDITIONS.items():
        filepath = AUDITS_ROOT / rel_path
        if not filepath.exists():
            # Try to find the file with glob
            matches = list(AUDITS_ROOT.glob(f"**/{rel_path.split('/')[-1]}"))
            if matches:
                filepath = matches[0]
            else:
                print(f"  Skipped (not found): {rel_path}")
                continue

        content = load_yaml_safe(filepath)
        if not content:
            continue

        # Check if already added
        if "# Multi-cloud" in content or "# Multi-tool" in content or "# Multi-platform" in content or "# Multi-database" in content:
            print(f"  Skipped (already has multi-tool): {filepath.name}")
            continue

        # Add commands before the last section or at the end
        content = content.rstrip() + "\n" + commands
        save_content(filepath, content)
        fixes_applied["multi_tool_commands"].append(str(filepath))
        print(f"  Added multi-tool commands: {filepath.name}")

# =============================================================================
# PHASE 3: AGENT ALTERNATIVE FIELDS
# =============================================================================

AGENT_ALTERNATIVES = {
    # For manual verification items, add automated alternatives
    "verification: manual": [
        ("Review with stakeholders", "agent_alternative: Check for stakeholder approval comments in PR history or CODEOWNERS file"),
        ("Visual inspection", "agent_alternative: Use automated screenshot comparison tools (Percy, Chromatic) or check for visual regression test results"),
        ("User testing", "agent_alternative: Check for user study documentation, A/B test results in analytics configs, or usability test reports"),
        ("Interview team", "agent_alternative: Parse README, ADR files, or Slack export for architectural decisions; check for runbook documentation"),
        ("Manual review", "agent_alternative: Use static analysis tools to generate metrics; check for existing code review comments"),
        ("Physical access", "agent_alternative: Check for hardware test reports, calibration certificates, or IoT device logs"),
        ("Perception testing", "agent_alternative: Check for documented comfort thresholds, user study results, or automated motion analysis logs"),
    ],
}

def apply_agent_alternatives():
    """Add agent_alternative fields for manual verification steps."""
    print("\n=== Phase 3: Agent Alternative Fields ===")

    count = 0
    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        content = load_yaml_safe(yaml_file)
        if not content:
            continue

        if "verification: manual" not in content.lower():
            continue

        if "agent_alternative:" in content:
            continue

        modified = False
        original = content

        # Add agent_alternative after verification: manual lines
        for pattern, replacement in AGENT_ALTERNATIVES["verification: manual"]:
            pattern_lower = pattern.lower()
            if pattern_lower in content.lower():
                # Find the verification: manual line and add alternative after
                lines = content.split('\n')
                new_lines = []
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if 'verification: manual' in line.lower() or 'verification: "manual"' in line.lower():
                        # Check context to pick appropriate alternative
                        context = '\n'.join(lines[max(0,i-5):i+5]).lower()
                        for pat, alt in AGENT_ALTERNATIVES["verification: manual"]:
                            if pat.lower() in context:
                                indent = len(line) - len(line.lstrip())
                                new_lines.append(' ' * indent + alt)
                                modified = True
                                break
                content = '\n'.join(new_lines)
                break

        if modified and content != original:
            save_content(yaml_file, content)
            fixes_applied["agent_alternatives"].append(str(yaml_file))
            count += 1
            if count <= 10:
                print(f"  Added alternative: {yaml_file.name}")

    if count > 10:
        print(f"  ... and {count - 10} more files")

# =============================================================================
# PHASE 4: DOCUMENTATION CLARITY
# =============================================================================

CLARITY_ADDITIONS = {
    # CAP theorem explanation
    "03-reliability-resilience/data-consistency/eventual-consistency.yaml": {
        "find": "CAP theorem",
        "addition": """
# NOTE: CAP Theorem Explanation
# The CAP theorem states that a distributed system can only guarantee 2 of 3 properties:
# - Consistency: All nodes see the same data at the same time
# - Availability: Every request receives a response (success/failure)
# - Partition tolerance: System continues operating despite network partitions
# Eventually consistent systems prioritize Availability and Partition tolerance over immediate Consistency.
"""
    },

    # SRP domain definition
    "07-architecture-design/design-principles/single-responsibility.yaml": {
        "find": "domain",
        "addition": """
# NOTE: Domain Definition for SRP
# A "domain" in this context refers to a cohesive area of business functionality:
# - Business capability: e.g., payments, inventory, user management
# - Bounded context (DDD): A self-contained model with clear boundaries
# - Functional area: e.g., validation, persistence, notification, formatting
# A class violates SRP when it handles multiple domains (e.g., both validation AND persistence).
"""
    },

    # Tier criteria documentation
    "01-security-trust/authentication/authentication-bypass.yaml": {
        "find": "tier:",
        "addition": """
# Tier Criteria Reference:
# - focused: Single tool/pattern analysis, <2 hours, minimal context needed
# - expert: Multiple tools, domain knowledge required, 2-6 hours, cross-cutting concerns
# - phd: Research-level analysis, novel synthesis, >6 hours, cutting-edge expertise needed
"""
    },
}

def apply_clarity_improvements():
    """Add documentation clarity improvements."""
    print("\n=== Phase 4: Documentation Clarity ===")

    for rel_path, clarity in CLARITY_ADDITIONS.items():
        filepath = AUDITS_ROOT / rel_path
        if not filepath.exists():
            print(f"  Skipped (not found): {rel_path}")
            continue

        content = load_yaml_safe(filepath)
        if not content:
            continue

        # Check if we already added this
        if "NOTE:" in content and clarity["find"] in content:
            print(f"  Skipped (already has notes): {filepath.name}")
            continue

        # Add the clarification near the relevant content
        if clarity["find"] in content:
            # Add after the description section
            if "description:" in content:
                desc_match = re.search(r'(description:.*?)(\n\w|\nprocedure:|\nsignals:)', content, re.DOTALL)
                if desc_match:
                    insert_pos = desc_match.end(1)
                    content = content[:insert_pos] + clarity["addition"] + content[insert_pos:]
                    save_content(filepath, content)
                    fixes_applied["clarity_improvements"].append(str(filepath))
                    print(f"  Added clarity notes: {filepath.name}")

# =============================================================================
# PHASE 5: ADDITIONAL TARGETED FIXES
# =============================================================================

def fix_file_patterns_go():
    """Add *.go to file_patterns where Go code patterns exist."""
    print("\n=== Phase 5a: Adding Missing Go File Patterns ===")

    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        content = load_yaml_safe(yaml_file)
        if not content:
            continue

        # Check if has Go code patterns but missing *.go in file_patterns
        has_go_patterns = any(p in content for p in ['math/rand', 'crypto/rand', 'log.', 'fmt.', 'func ', 'package '])
        has_go_files = '*.go' in content
        has_file_patterns = 'file_patterns:' in content

        if has_go_patterns and has_file_patterns and not has_go_files:
            # Add *.go to file_patterns
            content = re.sub(
                r'(file_patterns:\s*\n)',
                r'\1    - "*.go"\n',
                content
            )
            save_content(yaml_file, content)
            print(f"  Added *.go: {yaml_file.name}")

def fix_duration_format():
    """Standardize duration formats to use consistent notation."""
    print("\n=== Phase 5b: Standardizing Duration Formats ===")

    count = 0
    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        content = load_yaml_safe(yaml_file)
        if not content:
            continue

        original = content

        # Convert "X-Y hours" to structured format comment
        duration_match = re.search(r'estimated_duration:\s*["\']?(\d+)-(\d+)\s*hours?["\']?', content)
        if duration_match:
            min_h, max_h = duration_match.groups()
            avg = (int(min_h) + int(max_h)) // 2
            # Keep original but add clarifying comment
            old_line = duration_match.group(0)
            if '# median:' not in content:
                new_line = f'{old_line}  # median: {avg}h'
                content = content.replace(old_line, new_line)
                count += 1

        if content != original:
            save_content(yaml_file, content)

    print(f"  Standardized {count} duration formats")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def generate_report():
    """Generate summary report."""
    print("\n" + "="*60)
    print("REMAINING IMPROVEMENTS - FIX REPORT")
    print("="*60)

    total = 0
    for category, items in fixes_applied.items():
        count = len(items)
        total += count
        print(f"\n{category.replace('_', ' ').title()}: {count}")
        if count > 0 and count <= 8:
            for item in items:
                print(f"  - {Path(item).name}")
        elif count > 8:
            print(f"  (showing first 5 of {count})")
            for item in items[:5]:
                print(f"  - {Path(item).name}")

    print(f"\n{'='*60}")
    print(f"TOTAL ADDITIONAL FIXES: {total}")
    print("="*60)

    # Save report
    report_path = Path("/mnt/walnut-drive/dev/audits/meta-audit/remaining-improvements-report.txt")
    with open(report_path, 'w') as f:
        f.write("REMAINING IMPROVEMENTS REPORT\n")
        f.write(f"Generated: 2026-01-24\n")
        f.write("="*60 + "\n\n")
        for category, items in fixes_applied.items():
            f.write(f"\n{category.upper()}: {len(items)} fixes\n")
            f.write("-"*40 + "\n")
            for item in items:
                f.write(f"  {item}\n")
        f.write(f"\n\nTOTAL: {total} fixes\n")

    print(f"\nReport saved to: {report_path}")

def main():
    print("="*60)
    print("REMAINING IMPROVEMENTS FIX SCRIPT")
    print("="*60)

    apply_pattern_expansions()
    apply_multi_tool_commands()
    apply_agent_alternatives()
    apply_clarity_improvements()
    fix_file_patterns_go()
    fix_duration_format()

    generate_report()

if __name__ == "__main__":
    main()
