# Agent Assignment Protocol for Audits

## Overview

This document defines the protocol for intelligently assigning agents from the agents repository (`~/walnut-drive/dev/agents`) to each of the 2,189 audits in this repository, enabling multi-agent collaboration and parallel execution across ollama servers.

**Status**: Draft - Pending Multi-Dimensional Audit Review

---

## Part 1: Agent Assignment Schema

### Schema Extension for Audit YAML Files

Add a new `agent_assignment` section (Section 16) to each audit YAML file:

```yaml
# ============================================================
# SECTION 16: AGENT ASSIGNMENT
# ============================================================

agent_assignment:
  # Primary agent responsible for executing this audit
  primary_agent:
    agent_id: "security-auditor"           # Agent identifier from agents repo
    role: "auditor"                        # auditor|executor|advisor
    cognitive_mode: "critical"             # Match audit's procedure.context.cognitive_mode
    confidence_required: 0.7               # Minimum confidence threshold (default: 0.6)
    fallback_agent: "penetration-tester"   # Alternative if primary unavailable

  # Supporting agents providing specialized expertise
  supporting_agents:
    - agent_id: "python-pro"
      role: "input_provider"
      contribution: "Python-specific code pattern analysis"
      ensemble_role: "panel_member"
      required: false

    - agent_id: "cryptography-specialist"
      role: "input_provider"
      contribution: "Cryptographic implementation review"
      ensemble_role: "panel_member"
      required: true                       # Audit cannot proceed without this agent

  # Specialists for specific discovery methods or tooling
  specialists:
    - agent_id: "database-optimizer"
      trigger: "scope == 'database'"       # Conditional activation
      for_section: "discovery.metrics_queries"

    - agent_id: "kubernetes-expert"
      trigger: "tooling.infrastructure_tools contains 'kubectl'"
      for_section: "tooling.infrastructure_tools"

  # Panel composition for multi-agent reviews
  panel_composition:
    mode: "collaborative"                  # collaborative|sequential|parallel
    quorum: 2                              # Minimum agents required for consensus
    decision_rule: "majority"              # majority|unanimous|weighted

    roles:
      lead_auditor: "security-auditor"
      domain_experts: ["python-pro", "cryptography-specialist"]
      quality_reviewer: "first-principles-engineer"  # PhD tier for complex decisions

  # Execution preferences
  execution:
    parallel_capable: true                 # Can supporting agents run in parallel?
    ollama_server_affinity: []             # Preferred servers for model distribution
    max_concurrent_agents: 3               # Limit parallel execution
    tier_escalation_path:
      - tier: "focused"
        threshold: 0.8
      - tier: "expert"
        threshold: 0.6
      - tier: "phd"
        threshold: 0.4

  # Gap handling
  gap_handling:
    no_primary_agent: "escalate_to_human"  # escalate_to_human|create_on_demand|skip
    missing_specialist: "proceed_with_warning"
    agent_invention_context:
      domain_hints: []
      knowledge_sources_required: []
```

---

## Part 2: Mapping Rules

### Category-to-Agent Primary Mappings

| # | Audit Category | Primary Agent(s) | Supporting Agents |
|---|----------------|------------------|-------------------|
| 01 | security-trust | security-auditor, penetration-tester | cryptography-specialist, compliance-checker |
| 02 | performance-efficiency | performance-engineer | database-optimizer, cache-expert |
| 03 | reliability-resilience | architect-reviewer | kubernetes-expert |
| 04 | scalability-capacity | performance-engineer, architect-reviewer | kubernetes-expert |
| 05 | observability-instrumentation | prometheus-expert, grafana-expert | elk-expert |
| 06 | code-quality | [language]-pro | architect-reviewer |
| 07 | architecture-design | architect-reviewer, backend-architect | graphql-architect |
| 08 | data-state-management | database-optimizer, sql-pro | neo4j-expert |
| 09 | api-integration | graphql-architect, typescript-pro | security-auditor |
| 10 | testing-quality-assurance | [language]-pro | security-auditor |
| 11 | devops-ci-cd | terraform-expert, ansible-expert | docker-expert |
| 12 | cloud-infrastructure | aws-expert, gcp-expert, azure-expert | kubernetes-expert |
| 13 | infrastructure-as-code | terraform-expert, pulumi-expert | ansible-expert |
| 14 | usability-interaction | ui-ux-designer | frontend-developer |
| 15 | accessibility-inclusion | ui-ux-designer | frontend-developer |
| 16 | seo-discoverability | nextjs-expert | frontend-developer |
| 17 | human-organizational | first-principles-engineer | documentation-curator |
| 18 | ethical-societal | first-principles-engineer | - |
| 19 | compliance-legal | compliance-checker | security-auditor |
| 20 | vendor-third-party | compliance-checker | security-auditor |
| 21-36 | (various process/governance) | See detailed mapping | - |
| 37 | machine-learning-ai | ml-engineer, mlops-engineer | data-scientist, ai-engineer |
| 38 | sensors-physical-systems | esp32-expert, arduino-expert | raspberry-pi-expert |
| 39 | real-time-embedded | esp32-expert, rust-pro | c-pro, cpp-pro |
| 40 | signal-processing-data-acquisition | monostatic-radar-expert, lidar-expert | acoustic-expert |
| 41 | blockchain-distributed-ledger | solidity-expert, web3-developer | defi-architect |
| 42 | quantum-computing | first-principles-engineer (PhD) | - |
| 43 | metaverse-immersive | unity-developer, cesiumjs-expert | arkit-expert |

### Scope-to-Agent Mapping

| Scope Type | Required Tools | Preferred Agents |
|------------|----------------|------------------|
| codebase | Read, Grep, Glob, Bash | [language]-pro based on detection |
| config | Read, Grep, Glob | kubernetes-expert, terraform-expert |
| infrastructure | Bash, Read, Grep | cloud platform experts |
| metrics | Bash, WebFetch | prometheus-expert, performance-engineer |
| organizational | Read | first-principles-engineer |
| qualitative | Read | first-principles-engineer (PhD) |
| ml-systems | Read, Grep, Glob, Bash | ml-engineer, mlops-engineer |

### Tier Alignment

| Audit Tier | Agent Tier | Model | Suitability |
|------------|------------|-------|-------------|
| focused | focused | haiku | optimal |
| focused | expert | sonnet | acceptable |
| expert | expert | sonnet | optimal |
| expert | phd | opus | acceptable |
| phd | phd | opus | required |

---

## Part 3: Scoring Algorithm

```
score = (category_match × 0.25) +
        (scope_match × 0.20) +
        (tier_alignment × 0.15) +
        (tooling_match × 0.20) +
        (trigger_match × 0.10) +
        (cognitive_mode × 0.10)
```

**Thresholds:**
- Primary agent minimum: 0.65
- Supporting agent minimum: 0.45
- Specialist minimum: 0.55

**Tiebreaking Order:**
1. Higher tier preferred (PhD > Expert > Focused)
2. More specific agent preferred
3. Lower model cost when capabilities equal
4. Alphabetical (final)

---

## Part 4: Multi-Agent Execution

### Panel Modes

**Collaborative** (Default for complex audits)
- Multiple agents analyze simultaneously
- Cross-validation of findings
- Consensus-based decisions

**Sequential** (For dependent analysis)
- Discovery → Analysis → Verification → Remediation
- Each stage builds on previous output

**Parallel** (For independent tracks)
- Multiple agents on separate concerns
- Orchestrator merges results

### Ollama Server Distribution

```yaml
servers:
  ollama-primary:    # opus, sonnet, haiku
  ollama-secondary:  # sonnet, haiku
  ollama-edge:       # haiku only

distribution_strategy:
  opus:    ollama-primary only
  sonnet:  ollama-primary, ollama-secondary
  haiku:   ollama-edge preferred, others as fallback
```

---

## Part 5: Gap Detection

### Gap Types

| Gap Type | Severity | Blocking | Default Action |
|----------|----------|----------|----------------|
| no_primary_agent | critical | yes | escalate_to_human |
| missing_specialist (required) | high | yes | escalate_to_human |
| missing_specialist (optional) | medium | no | proceed_with_warning |
| tier_mismatch | medium | no | use_higher_tier |
| tooling_gap | medium | conditional | compose_panel |
| domain_gap | high | yes | invoke_agent_inventor |

### Expected Gaps Requiring New Agents

| Domain | Gap | Suggested Agent |
|--------|-----|-----------------|
| Functional Safety (Cat 38) | IEC 61508, SIL analysis | functional-safety-auditor (PhD) |
| Formal Verification (Cat 42) | Theorem proving | formal-verification-specialist (PhD) |
| Quantum Computing (Cat 42) | Quantum algorithms | quantum-computing-specialist (PhD) |
| Accessibility (Cat 15) | WCAG deep expertise | accessibility-auditor (Expert) |
| Industrial Protocols (Cat 39) | OPC-UA, Modbus | industrial-protocol-expert (Expert) |

---

## Part 6: Implementation Files

### To Create

| File | Purpose |
|------|---------|
| `tooling/agent-mapping-config.yaml` | Complete mapping configuration |
| `tooling/scripts/assign-agents.py` | Assignment engine |
| `tooling/gap-report.yaml` | Generated gap analysis |

### To Modify

| File | Change |
|------|--------|
| `schema/AUDIT-TEMPLATE-BLANK.yaml` | Add Section 16: Agent Assignment |
| All 2,189 audit YAML files | Add agent_assignment section |

### Reference Files

| File | Purpose |
|------|---------|
| `~/walnut-drive/dev/agents/agent-manifest.json` | Agent registry |
| `~/walnut-drive/dev/agents/TIER-CLASSIFICATION.md` | Tier definitions |
| `AUDIT-INVENTORY.csv` | All audit metadata |

---

## Next Steps: Multi-Dimensional Audit Strategy

Before implementing agent assignments, we should first audit the audits themselves to ensure quality and fitness for purpose. See `MULTI-DIMENSIONAL-AUDIT-STRATEGY.md` for the meta-audit framework.

**Dimensions to evaluate:**
1. Clarity - Are instructions unambiguous?
2. Alignment - Does each audit serve core mission?
3. Context Management - Appropriate token budget for tier?
4. Completeness - All required sections populated?
5. Actionability - Can signals be detected with specified patterns?
6. Agent Readiness - Is the audit structured for agent execution?

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2026-01-24 | Claude Opus 4.5 | Initial protocol design |
