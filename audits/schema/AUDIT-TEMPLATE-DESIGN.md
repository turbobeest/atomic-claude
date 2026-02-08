# Audit Template Design Philosophy

This document explains the rationale behind the audit YAML structure and field choices.

## Core Principles

### 1. Domain-Agnostic Structure

The template adapts to multiple audit domains without forcing inappropriate patterns:

- **Code audits** use `code_patterns` and static analysis
- **Infrastructure audits** use `metrics_queries` and CLI commands
- **Organizational audits** use `interviews` and qualitative assessment
- **Documentation audits** use `file_patterns` and checklist verification

### 2. Self-Contained Execution

Each audit file contains everything needed to execute:

- Clear prerequisites
- Discovery mechanisms
- Signal definitions with evidence patterns
- Verification commands
- External knowledge source references

### 3. AI-Agent Optimized

The structure is designed for AI orchestration:

- Hierarchical IDs enable precise targeting
- Profile membership allows bundle execution
- Knowledge sources provide grounding context
- Closeout checklists provide concrete verification steps

## Field Design Decisions

### Hierarchical IDs

```yaml
id: "security-trust.authentication.oauth2-implementation"
```

**Why**: Enables:
- Precise bundle references
- Category/subcategory filtering
- Cross-audit relationships
- Clear taxonomy navigation

### Completeness Field

```yaml
completeness: "complete" | "requires_discovery"
```

**Why**: Signals to orchestrators whether the audit can run immediately or needs a discovery phase first.

### Automatable Classification

```yaml
automatable: "yes" | "partial" | "manual"
```

**Why**:
- `yes`: Agent can execute fully automated
- `partial`: Mix of automated checks and human judgment
- `manual`: Requires interviews, expert review, or qualitative assessment

### Signal Severity Levels

```yaml
severity: "critical" | "high" | "medium" | "low"
```

**Why**: Maps to standard risk frameworks:
- `critical`: Blocks deployment, immediate action required
- `high`: Significant risk, must address before production
- `medium`: Should address, improves quality
- `low`: Nice to have, consider addressing

### Evidence Patterns vs Evidence Indicators

**Evidence Patterns** (code/config audits):
```yaml
evidence_pattern: "password\\s*=\\s*['\"][^'\"]+['\"]"
```
Regex or grep-able patterns for automated detection.

**Evidence Indicators** (organizational audits):
```yaml
evidence_indicators:
  - "Only one person knows the deployment process"
  - "No documentation exists for critical system"
```
Qualitative observations from interviews or review.

### Knowledge Sources

```yaml
knowledge_sources:
  external:
    - name: "OWASP ASVS"
      url: "https://owasp.org/asvs"
      relevance: "Section 3.5 - Session Management"
      cacheable: true
```

**Why**:
- Provides authoritative grounding for AI agents
- `cacheable: true` enables offline execution
- Specific relevance helps focus agent attention

### Closeout Checklist

```yaml
closeout_checklist:
  - action: "Verify session timeout"
    verification: "grep -r 'session.timeout' config/"
    verification_expected: "timeout <= 3600"
```

**Why**: Provides concrete, verifiable completion criteria that both humans and AI can evaluate.

## Extensibility

The template is designed for extension:

1. **New fields** can be added to any section
2. **Industry overlays** add domain-specific signals
3. **Custom tooling** references can be added to discovery
4. **Compliance mappings** scale to any framework

## Relationship to Bundles

Audits are atomic units. Bundles compose them:

```yaml
# bundles/profiles/security.yaml
audits:
  - security-trust.authentication.oauth2-implementation
  - security-trust.authentication.session-management
  - security-trust.cryptography.encryption-in-transit
```

This separation keeps audits focused and reusable while enabling flexible composition.
