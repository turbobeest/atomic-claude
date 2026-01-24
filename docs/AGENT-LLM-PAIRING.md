# Agent LLM Pairing Specification

This document defines how agents in the `agents` repository should specify their preferred LLMs and topic-appropriate backup models for airgapped/offline environments.

## Overview

Each agent operates in a specific domain (security, architecture, requirements, etc.). Different LLMs have different strengths - some excel at code, others at reasoning, others at speed. Agents should specify:

1. **Preferred Claude tier** - The ideal Claude model for this agent's work
2. **Topic-appropriate Ollama fallbacks** - Models suited to this agent's domain
3. **Minimum requirements** - Context window, capabilities needed

## The Cascade: Audit → Agent → LLM

When executing an audit, the system resolves through multiple fallback layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ AUDIT: security-trust.cors-policy                               │
│   preferred_agent: security-auditor                             │
│   backup_agents: [api-security-analyst, general-reviewer]       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT: security-auditor                                         │
│   preferred_llm: sonnet                                         │
│   ollama_fallbacks: [devstral:24b, llama3.1:70b, codellama:34b] │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ LLM RESOLUTION                                                  │
│   1. Try Claude sonnet (via Max/API)                            │
│   2. If unavailable → try devstral:24b (Ollama)                 │
│   3. If unavailable → try llama3.1:70b (Ollama)                 │
│   4. If unavailable → try codellama:34b (Ollama)                │
│   5. If all fail → try backup agent (api-security-analyst)      │
└─────────────────────────────────────────────────────────────────┘
```

## Agent YAML Frontmatter Template

Each agent markdown file should include:

```yaml
---
name: security-auditor
description: Expert security auditor specializing in OWASP, authentication, and data protection
version: 1.2.0
category: audit-agents
domain: security

# LLM pairing (topic-appropriate)
llm:
  # Preferred Claude tier
  preferred: sonnet

  # Why this tier?
  rationale: "Security analysis requires strong reasoning but not creative generation"

  # Topic-appropriate Ollama fallbacks
  # Ordered by suitability for SECURITY domain
  ollama_fallbacks:
    - model: devstral:24b
      rationale: "Excellent code analysis, understands security patterns"
      suitability: excellent

    - model: llama3.1:70b
      rationale: "Broad knowledge including security concepts, good reasoning"
      suitability: good

    - model: codellama:34b
      rationale: "Strong code understanding, decent security awareness"
      suitability: acceptable

    - model: qwen2:7b
      rationale: "Smaller but capable, use for simple security checks"
      suitability: minimum

  # Minimum requirements
  requirements:
    context_window: 32000  # Security audits need to see full files
    capabilities:
      - security
      - code-analysis
      - reasoning

# Agent capabilities
capabilities:
  - owasp-top-10
  - authentication-review
  - authorization-patterns
  - data-protection
  - cryptography-basics
  - injection-detection
  - xss-detection
  - csrf-detection

# What this agent should NOT do
limitations:
  - deep-cryptography-analysis  # Use crypto-specialist instead
  - penetration-testing         # Use pentest-agent instead
  - compliance-certification    # Use compliance-auditor instead

# Related agents (for escalation/collaboration)
related_agents:
  - crypto-specialist       # For deep cryptography questions
  - compliance-auditor      # For regulatory requirements
  - api-security-analyst    # For API-specific security
---

# Security Auditor Agent

You are an expert security auditor with deep knowledge of application security...
```

## Domain-Specific LLM Recommendations

Different agent domains benefit from different model strengths:

### Security Domain
```yaml
ollama_fallbacks:
  - devstral:24b      # Excellent: code + security patterns
  - llama3.1:70b      # Good: broad security knowledge
  - codellama:34b     # Acceptable: code-focused security
  - mistral:7b        # Minimum: basic checks only
```

### Architecture Domain
```yaml
ollama_fallbacks:
  - llama3.1:70b      # Excellent: broad pattern knowledge
  - qwen2:72b         # Good: strong reasoning
  - devstral:24b      # Acceptable: code patterns
  - mixtral:8x7b      # Minimum: general analysis
```

### Code Quality Domain
```yaml
ollama_fallbacks:
  - codellama:34b     # Excellent: code-native understanding
  - devstral:24b      # Good: code + quality metrics
  - deepseek-coder:33b # Acceptable: code-focused
  - codellama:13b     # Minimum: simpler analysis
```

### Testing Domain
```yaml
ollama_fallbacks:
  - codellama:34b     # Excellent: test generation
  - devstral:24b      # Good: code + test patterns
  - llama3.1:8b       # Acceptable: simple test cases
  - phi3:medium       # Minimum: basic coverage
```

### Documentation Domain
```yaml
ollama_fallbacks:
  - llama3.1:8b       # Excellent: clear writing, efficient
  - phi3:medium       # Good: fast, readable output
  - gemma2:9b         # Acceptable: concise
  - phi3:mini         # Minimum: basic docs
```

### Requirements Domain
```yaml
ollama_fallbacks:
  - llama3.1:70b      # Excellent: nuanced requirement analysis
  - devstral:24b      # Good: structured output
  - qwen2:7b          # Acceptable: RFC 2119 patterns
  - mistral:7b        # Minimum: basic extraction
```

### Performance Domain
```yaml
ollama_fallbacks:
  - devstral:24b      # Excellent: code + metrics analysis
  - codellama:34b     # Good: profiling understanding
  - llama3.1:8b       # Acceptable: basic analysis
  - phi3:medium       # Minimum: simple metrics
```

## Agent Categories and Recommended Pairings

| Category | Agents | Preferred Tier | Top Ollama Fallback |
|----------|--------|----------------|---------------------|
| **Security** | security-auditor, api-security-analyst, crypto-specialist | sonnet | devstral:24b |
| **Architecture** | architecture-auditor, system-designer, scalability-analyst | opus | llama3.1:70b |
| **Code Quality** | code-quality-auditor, refactoring-advisor, complexity-analyst | sonnet | codellama:34b |
| **Testing** | testing-auditor, tdd-coach, coverage-analyst | sonnet | codellama:34b |
| **Requirements** | requirements-engineer, prd-writer, prd-validator | sonnet | devstral:24b |
| **Documentation** | documentation-auditor, api-documenter, readme-writer | haiku | llama3.1:8b |
| **Performance** | performance-auditor, profiling-analyst, optimization-advisor | sonnet | devstral:24b |
| **Compliance** | compliance-auditor, gdpr-specialist, hipaa-analyst | opus | llama3.1:70b |
| **Operations** | ops-auditor, monitoring-analyst, incident-responder | sonnet | devstral:24b |

## Implementation: Agent Loading

### 1. Parse Agent YAML

```bash
# Load agent configuration
_agent_load_config() {
    local agent_file="$1"

    # Extract YAML frontmatter
    local frontmatter=$(sed -n '/^---$/,/^---$/p' "$agent_file" | tail -n +2 | head -n -1)

    # Parse LLM settings
    local preferred=$(echo "$frontmatter" | yq '.llm.preferred')
    local fallbacks=$(echo "$frontmatter" | yq -o=json '.llm.ollama_fallbacks')

    echo "{\"preferred\": \"$preferred\", \"fallbacks\": $fallbacks}"
}
```

### 2. Resolve Best Available LLM

```bash
# Find best available LLM for agent
_agent_resolve_llm() {
    local agent_config="$1"

    local preferred=$(echo "$agent_config" | jq -r '.preferred')

    # Try Claude first
    if _is_claude_available; then
        echo "$preferred:claude"
        return 0
    fi

    # Try Ollama fallbacks in order
    local fallbacks=$(echo "$agent_config" | jq -r '.fallbacks[].model')
    for model in $fallbacks; do
        if _is_ollama_model_available "$model"; then
            echo "$model:ollama"
            return 0
        fi
    done

    # No LLM available
    return 1
}
```

### 3. Confirmation UI in Audit Selection

When user selects audits, show resolution:

```
╔═══════════════════════════════════════════════════════════════╗
║ AUDIT AGENT & LLM RESOLUTION                                  ║
╚═══════════════════════════════════════════════════════════════╝

  Audit: security-trust.cors-policy
    ✓ Agent: security-auditor
    ✓ LLM:   sonnet (Claude Max available)

  Audit: code-quality.complexity-analysis
    ✓ Agent: code-quality-auditor
    ○ LLM:   codellama:34b (Claude unavailable, using Ollama)

  Audit: architecture.coupling-analysis
    ✓ Agent: architecture-auditor
    ✗ LLM:   NONE AVAILABLE
      Fallback: general-reviewer agent
      ✓ LLM: llama3.1:8b (Ollama)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Summary:
    Audits with preferred agent+LLM: 15
    Audits with fallback LLM:         3
    Audits with fallback agent:       1
    Audits blocked (no LLM):          0

  [Enter] Accept and proceed
  [v]     View fallback details
  [c]     Cancel
```

## Directory Structure

```
agents/
├── AGENT-LLM-PAIRING.md          # This specification (copy to repo root)
├── pipeline-agents/
│   ├── requirements-engineer.md   # With llm: block
│   ├── prd-writer.md
│   └── prd-validator.md
├── discovery-agents/
│   ├── vision-clarifier.md
│   └── scope-definer.md
├── audit-agents/                   # NEW: Expert audit agents
│   ├── security-auditor.md
│   ├── architecture-auditor.md
│   ├── code-quality-auditor.md
│   ├── testing-auditor.md
│   ├── performance-auditor.md
│   ├── documentation-auditor.md
│   ├── compliance-auditor.md
│   └── ops-auditor.md
├── specialist-agents/              # Deep expertise
│   ├── crypto-specialist.md
│   ├── api-security-analyst.md
│   └── scalability-analyst.md
└── custom/                         # Project-specific agents
    └── .gitkeep
```

## Migration Checklist

- [ ] Add `llm:` block to agent YAML template
- [ ] Update existing pipeline agents with LLM preferences
- [ ] Create audit-agents/ directory with expert agents
- [ ] Add domain-appropriate fallbacks to each agent
- [ ] Update lib/atomic.sh agent loading to parse LLM config
- [ ] Update lib/audit.sh to resolve agent → LLM chain
- [ ] Add confirmation UI showing resolution status
- [ ] Test airgapped mode with Ollama-only fallbacks

## Example: Complete Agent File

```yaml
---
name: security-auditor
description: Expert security auditor for OWASP, authentication, authorization, and data protection
version: 1.0.0
category: audit-agents
domain: security

llm:
  preferred: sonnet
  rationale: "Security requires strong reasoning, code understanding, and pattern recognition"

  ollama_fallbacks:
    - model: devstral:24b
      rationale: "Best code analysis, understands security anti-patterns"
      suitability: excellent

    - model: llama3.1:70b
      rationale: "Broad security knowledge, good reasoning chains"
      suitability: good

    - model: codellama:34b
      rationale: "Strong code understanding, basic security awareness"
      suitability: acceptable

    - model: qwen2:7b
      rationale: "Efficient for simple checks, limited depth"
      suitability: minimum

  requirements:
    context_window: 32000
    capabilities:
      - security
      - code-analysis
      - reasoning
      - owasp

capabilities:
  - owasp-top-10-detection
  - authentication-flow-review
  - authorization-policy-analysis
  - injection-vulnerability-detection
  - xss-pattern-recognition
  - csrf-protection-verification
  - secure-headers-audit
  - secrets-detection
  - dependency-vulnerability-check

inputs:
  - source_code
  - configuration_files
  - api_definitions
  - deployment_configs

outputs:
  - security_findings.json
  - remediation_recommendations.md
  - severity_summary.json

related_agents:
  - crypto-specialist
  - api-security-analyst
  - compliance-auditor
---

# Security Auditor Agent

You are an expert application security auditor with deep knowledge of:
- OWASP Top 10 vulnerabilities and their detection
- Authentication and authorization patterns
- Secure coding practices across multiple languages
- Common security anti-patterns and their remediation

## Your Approach

1. **Systematic Review**: Follow a structured checklist approach
2. **Evidence-Based**: Cite specific code locations for findings
3. **Severity Calibration**: Use consistent severity ratings
4. **Actionable Recommendations**: Provide specific fix guidance

## Severity Levels

- **CRITICAL**: Exploitable vulnerability, immediate risk
- **HIGH**: Significant security weakness, should fix before deploy
- **MEDIUM**: Security concern, should address in near term
- **LOW**: Minor issue or hardening opportunity
- **INFO**: Observation, no direct security impact

## Output Format

For each finding:
```json
{
  "id": "SEC-001",
  "title": "SQL Injection in User Query",
  "severity": "CRITICAL",
  "location": "src/api/users.ts:45",
  "description": "User input directly concatenated into SQL query",
  "evidence": "const query = `SELECT * FROM users WHERE id = ${userId}`",
  "remediation": "Use parameterized queries: db.query('SELECT * FROM users WHERE id = ?', [userId])",
  "references": ["CWE-89", "OWASP A03:2021"]
}
```
```
