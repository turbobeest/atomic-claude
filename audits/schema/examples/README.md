# Audit Pattern Selection Guide

This directory contains example audits demonstrating the three primary patterns in the taxonomy. **Select the appropriate pattern based on your audit's domain, not by copying blindly.**

## Pattern Overview

| Pattern | Example File | Best For | Automatable |
|---------|--------------|----------|-------------|
| Organizational | `01-bus-factor-audit.yaml` | Team assessments, knowledge distribution, culture | Manual |
| Infrastructure | `02-container-resource-limits-audit.yaml` | Metrics, configs, Kubernetes, cloud resources | Yes |
| Documentation | `03-runbook-completeness-audit.yaml` | Process artifacts, runbooks, ADRs | Partial |
| Code/Security | `../AUDIT-TEMPLATE-BLANK.yaml` | Code patterns, static analysis, vulnerabilities | Yes/Partial |

## Pattern Selection Logic

```
IF audit assesses people, teams, or organizational factors:
    USE Organizational pattern (01-bus-factor-audit.yaml)
    - interviews instead of code_patterns
    - evidence_indicators instead of regex
    - automatable: "manual"

ELIF audit checks infrastructure metrics or configs:
    USE Infrastructure pattern (02-container-resource-limits-audit.yaml)
    - kubectl/cloud CLI commands
    - metrics_queries with thresholds
    - automatable: "yes"

ELIF audit reviews documentation or process artifacts:
    USE Documentation pattern (03-runbook-completeness-audit.yaml)
    - file_patterns and documents_to_review
    - mixed automated + manual verification
    - automatable: "partial"

ELSE (code analysis, security vulnerabilities, config patterns):
    USE Code/Security pattern (AUDIT-TEMPLATE-BLANK.yaml)
    - code_patterns with regex
    - static analysis tooling
    - CWE mappings for security
```

## Key Differences by Pattern

### Organizational Pattern (Categories 17-23)

```yaml
discovery:
  interviews:
    - role: "Engineering Manager"
      questions:
        - "How many people can deploy to production?"
        - "What happens if [key person] is unavailable?"

signals:
  critical:
    - signal: "Single point of failure"
      evidence_indicators:
        - "Only one person knows system X"
        - "No documentation for critical process Y"
      remediation: "Cross-train team members..."

closeout_checklist:
  - action: "Conduct team interviews"
    verification: "manual"
    verification_notes: "Interview at least 3 team members"
```

### Infrastructure Pattern (Categories 13-16)

```yaml
discovery:
  metrics_queries:
    - system: "Prometheus"
      query: "container_memory_usage_bytes / container_spec_memory_limit_bytes"
      threshold: "> 0.8"

  kubernetes_resources:
    - api_version: "v1"
      kind: "Pod"
      namespace: "all"

signals:
  critical:
    - signal: "No resource limits defined"
      evidence_pattern: "resources.limits == null"
      remediation: "Add memory and CPU limits..."

closeout_checklist:
  - action: "Verify all pods have resource limits"
    verification: "kubectl get pods -A -o json | jq '.items[] | select(.spec.containers[].resources.limits == null)'"
    verification_expected: "Empty output"
```

### Documentation Pattern (Categories 24-30)

```yaml
discovery:
  file_patterns:
    - pattern: "**/runbook*.md"
    - pattern: "**/docs/operations/**"

  documents_to_review:
    - type: "Runbook"
      required_sections:
        - "Overview"
        - "Prerequisites"
        - "Step-by-step instructions"
        - "Rollback procedure"

signals:
  high:
    - signal: "Missing rollback procedures"
      evidence_pattern: "Document lacks 'rollback' or 'recovery' section"
      remediation: "Add rollback instructions..."

closeout_checklist:
  - action: "Review runbook completeness"
    verification: "partial"
    verification_notes: "Automated check for sections, manual review for quality"
```

### Code/Security Pattern (Categories 1-12)

```yaml
discovery:
  code_patterns:
    - pattern: "OAuth|OIDC|openid"
      file_types: ["*.py", "*.js", "*.ts", "*.java"]
    - pattern: "client_secret|client_id"
      file_types: ["*.yaml", "*.json", "*.env"]

signals:
  critical:
    - signal: "Client secret exposed in code"
      evidence_pattern: "client_secret\\s*=\\s*['\"][^'\"]+['\"]"
      cwe: "CWE-798"
      remediation: "Move secrets to secure vault..."

closeout_checklist:
  - action: "Scan for hardcoded secrets"
    verification: "semgrep --config p/secrets ."
    verification_expected: "No findings"
```

## Anti-Patterns to Avoid

**DO NOT** use grep patterns for organizational audits:
```yaml
# WRONG - bus factor cannot be grepped
signals:
  critical:
    - evidence_pattern: "grep -r 'bus factor' docs/"
```

**DO NOT** claim organizational audits are automatable:
```yaml
# WRONG - interviews cannot be automated
execution:
  automatable: "yes"
```

**DO NOT** use vague signals:
```yaml
# WRONG - not actionable
signals:
  critical:
    - signal: "Security is bad"
      remediation: "Make it better"
```

## When in Doubt

1. Check which category number your audit belongs to
2. Categories 17-23 (Human & Experience) → Organizational pattern
3. Categories 13-16 (Infrastructure) → Infrastructure pattern
4. Categories 24-30 (Process & Governance) → Often Documentation pattern
5. Categories 1-12 (Core Technical) → Usually Code/Security pattern
6. Categories 31-43 vary - use judgment based on what's being assessed
