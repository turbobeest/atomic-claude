# Audit Agent Pairing Specification

This document defines how audits in the `audits` repository should specify their preferred expert agents and backup Ollama models for multi-agent audit collaboration.

## Overview

Each audit file should include YAML frontmatter that specifies:
1. **Preferred expert agent** - The specialized agent best suited to perform this audit
2. **Backup Ollama models** - Fallback models for airgapped/offline environments
3. **Model requirements** - Minimum capabilities needed for quality results

## Why Multi-Agent Audits?

Single-LLM audits miss nuanced expertise:

| Approach | Strengths | Weaknesses |
|----------|-----------|------------|
| Single LLM | Fast, simple | Generic analysis, misses domain expertise |
| Multi-agent | Deep expertise, cross-validation | More complex orchestration |

**Multi-agent audits** bring specialized knowledge:
- Security auditor knows OWASP, CVEs, attack patterns
- Architecture auditor knows patterns, coupling, scalability
- Requirements auditor knows RFC 2119, testability, traceability

## Audit YAML Frontmatter Template

Each audit markdown file in `categories/` should include:

```yaml
---
audit_id: security-trust.application-security.cors-policy
name: CORS Policy Audit
category: security-trust
subcategory: application-security
tier: focused
severity: high

# Agent pairing (NEW)
agent:
  # Primary expert agent from agents repository
  primary: security-auditor

  # Fallback agents if primary unavailable
  fallbacks:
    - api-security-analyst
    - general-security-reviewer

  # Model tier requirement
  model_tier: sonnet

  # Ollama fallback chain for airgapped environments
  ollama_fallbacks:
    - devstral:24b       # Best: strong reasoning, code analysis
    - llama3.1:70b       # Good: broad knowledge
    - codellama:34b      # Acceptable: code-focused
    - mistral:7b         # Minimum: fast but less thorough

  # Minimum requirements for quality results
  requirements:
    context_window: 16000
    capabilities:
      - security
      - code-analysis
      - reasoning

# SDLC phase applicability
phases:
  discovery: false
  prd: true
  task_decomposition: false
  specification: true
  implementation: true
  testing: true
  integration: true
  deployment: true
  post_production: true

# Automation status
automation:
  fully_automated: true
  semi_automated: false
  manual_only: false

# Dependencies
dependencies:
  tools: []
  files:
    - "*.ts"
    - "*.js"
    - "api/**/*"
---

# CORS Policy Audit

## Purpose
Verify Cross-Origin Resource Sharing policies are correctly configured...
```

## Expert Agent Categories

Map audit categories to specialized agents:

| Audit Category | Primary Agent | Expertise |
|----------------|---------------|-----------|
| `security-trust` | security-auditor | OWASP, CVEs, auth, encryption |
| `architecture` | architecture-auditor | Patterns, coupling, scalability |
| `code-quality` | code-quality-auditor | Complexity, duplication, standards |
| `testing` | testing-auditor | Coverage, TDD, test design |
| `performance` | performance-auditor | Latency, throughput, profiling |
| `documentation` | documentation-auditor | Completeness, accuracy, clarity |
| `compliance` | compliance-auditor | GDPR, HIPAA, SOC2, regulations |
| `operational` | ops-auditor | Monitoring, logging, alerting |
| `accessibility` | a11y-auditor | WCAG, screen readers, contrast |

## Ollama Model Recommendations by Audit Type

| Audit Type | Recommended Models | Rationale |
|------------|-------------------|-----------|
| Security | devstral:24b, llama3.1:70b | Need deep reasoning about attack vectors |
| Architecture | llama3.1:70b, qwen2:72b | Need broad pattern knowledge |
| Code Quality | codellama:34b, devstral:24b | Code-focused analysis |
| Testing | codellama:34b, llama3.1:8b | Test generation, coverage analysis |
| Performance | devstral:24b, phi3:medium | Metrics interpretation |
| Documentation | llama3.1:8b, phi3:mini | Text analysis, simpler task |
| Compliance | llama3.1:70b, qwen2:72b | Regulatory knowledge needed |

## Implementation: audit.sh Enhancement

The `lib/audit.sh` library should be enhanced to:

### 1. Load Agent from Audit YAML

```bash
# Extract agent configuration from audit file
_audit_get_agent_config() {
    local audit_file="$1"

    # Parse YAML frontmatter
    local frontmatter=$(sed -n '/^---$/,/^---$/p' "$audit_file" | tail -n +2 | head -n -1)

    # Extract agent settings
    local primary_agent=$(echo "$frontmatter" | grep -A1 "^agent:" | grep "primary:" | awk '{print $2}')
    local model_tier=$(echo "$frontmatter" | grep "model_tier:" | awk '{print $2}')

    echo "$primary_agent:$model_tier"
}
```

### 2. Multi-Agent Orchestration

```bash
# Execute audit with expert agent collaboration
_audit_execute_with_agents() {
    local audit_id="$1"
    local audit_file="$2"

    # Get agent config
    local agent_config=$(_audit_get_agent_config "$audit_file")
    local primary_agent=$(echo "$agent_config" | cut -d: -f1)
    local model_tier=$(echo "$agent_config" | cut -d: -f2)

    # Load agent prompt from agents repository
    local agent_prompt=""
    local agent_file="$AGENT_REPO/audit-agents/$primary_agent.md"
    if [[ -f "$agent_file" ]]; then
        agent_prompt=$(cat "$agent_file")
    fi

    # Build audit prompt with agent expertise
    local full_prompt="$agent_prompt

## Audit Task: $audit_id

$(cat "$audit_file")

## Artifacts to Analyze
..."

    # Invoke with model fallback support
    atomic_invoke "$full_prompt" "$output_file" "Audit: $audit_id" --model="$model_tier"
}
```

### 3. Cross-Validation (Optional)

For critical audits, use multiple agents:

```bash
# Cross-validate with secondary agent
_audit_cross_validate() {
    local primary_result="$1"
    local audit_file="$2"

    # Get fallback agent
    local fallback_agent=$(yq '.agent.fallbacks[0]' "$audit_file")

    # Run second opinion
    local secondary_result=$(_audit_invoke_agent "$fallback_agent" "$audit_file")

    # Reconcile findings
    _audit_reconcile_findings "$primary_result" "$secondary_result"
}
```

## AUDIT-INVENTORY.csv Enhancement

Add `agent_id` column to the inventory:

```csv
audit_id,audit_name,category,subcategory,...,agent_id,model_tier
security-trust.application-security.cors-policy,CORS Policy Audit,security-trust,application-security,...,security-auditor,sonnet
code-quality.testing.unit-test-coverage,Unit Test Coverage,code-quality,testing,...,testing-auditor,haiku
```

## Migration Plan

1. **Phase 1: Template Update**
   - Add `agent:` block to audit YAML template
   - Document required fields

2. **Phase 2: Inventory Enhancement**
   - Add `agent_id` and `model_tier` columns to AUDIT-INVENTORY.csv
   - Populate for all 2,200+ audits (can be LLM-assisted)

3. **Phase 3: Library Enhancement**
   - Update `lib/audit.sh` with agent loading
   - Add model fallback resolution
   - Implement cross-validation for critical audits

4. **Phase 4: Agent Repository**
   - Create `audit-agents/` directory in agents repo
   - Define expert agents for each audit category
   - Include model preferences in agent YAML

## Example: Complete Audit File

```yaml
---
audit_id: security-trust.authentication.jwt-validation
name: JWT Validation Audit
category: security-trust
subcategory: authentication
tier: expert
severity: critical

agent:
  primary: security-auditor
  fallbacks:
    - api-security-analyst
  model_tier: sonnet
  ollama_fallbacks:
    - devstral:24b
    - llama3.1:70b
  requirements:
    context_window: 32000
    capabilities:
      - security
      - jwt
      - cryptography

phases:
  prd: true
  specification: true
  implementation: true
  testing: true
  deployment: true

automation:
  fully_automated: true

dependencies:
  tools:
    - jwt-decode
  files:
    - "**/auth/**/*.{ts,js}"
    - "**/middleware/**/*.{ts,js}"
---

# JWT Validation Audit

## Purpose
Verify JSON Web Token implementation follows security best practices.

## Checklist

### Token Structure
- [ ] Uses RS256 or ES256 (not HS256 for multi-service)
- [ ] Includes standard claims (iss, sub, aud, exp, iat)
- [ ] Token expiration is reasonable (< 1 hour for access tokens)

### Validation
- [ ] Signature verified before claims processed
- [ ] Algorithm specified explicitly (prevents "alg: none" attacks)
- [ ] Issuer and audience validated
- [ ] Clock skew tolerance configured

### Storage
- [ ] Tokens not stored in localStorage (XSS vulnerable)
- [ ] HttpOnly cookies or memory-only storage
- [ ] Refresh tokens have longer expiry and rotation

### Revocation
- [ ] Token blacklist/revocation mechanism exists
- [ ] Logout invalidates all user tokens
- [ ] Compromised token detection

## Evidence Required
- Authentication middleware code
- Token generation configuration
- Token storage implementation
- Logout flow implementation
```

## Next Steps

1. Create this template in the audits repository root
2. Update ATOMIC-CLAUDE's `lib/audit.sh` to support agent loading
3. Create initial audit agents in agents repository
4. Migrate high-priority audits to new format
5. Build LLM-assisted migration tool for remaining audits
