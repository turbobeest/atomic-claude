
![audits](https://github.com/user-attachments/assets/8338f5e4-f305-4217-aa3f-7cf52753f73d)



# Software Stack Audit Taxonomy

A comprehensive, multi-dimensional taxonomy of software stack audits designed as knowledge grounding for AI-powered audit agents.

## What This Is

This repository contains **2186 structured audit definitions** covering every meaningful dimension of software quality: security, performance, reliability, accessibility, compliance, ethics, and more.

**[Browse the Audit Catalog](https://turbobeest.github.io/audits/)** - Interactive web UI for exploring and filtering audits.

Each audit is a YAML file that defines:
- **What to look for** (signals at critical/high/medium/low severity)
- **How to find it** (discovery patterns, commands, interview questions)
- **Why it matters** (business and technical context)
- **How to fix it** (remediation guidance)
- **How to verify** (closeout checklists)

## Purpose

### For AI Agents
The taxonomy provides structured knowledge that enables AI agents to perform sophisticated, context-aware audits. Each audit includes:
- Cognitive mode guidance (critical, evaluative, informative)
- Tier classification (focused, expert, PhD-level)
- Escalation triggers for edge cases
- Tool and verification command references

### For Humans
An exhaustive reference catalog of audit concerns, organized hierarchically so teams can cherry-pick relevant audits for their specific stack and compliance requirements.

## Taxonomy Structure

```
audits/
├── 01-security-trust/           # Authentication, authorization, cryptography
├── 02-performance-efficiency/   # Latency, throughput, resource usage
├── 03-reliability-resilience/   # Fault tolerance, recovery, chaos engineering
├── ...
├── 19-compliance-legal/         # GDPR, SOC2, HIPAA, PCI-DSS
├── 20-vendor-third-party/       # Supply chain, SLAs, vendor risk
├── 21-responsible-design/         # Bias, fairness, environmental impact
├── 22-gamification-behavioral/  # Engagement ethics, dark patterns
├── 23-emotional-design-trust/   # Trust signals, social proof, credibility
├── 24-compliance-governance/    # Regulatory compliance, data privacy
├── 25-43...                     # Operational excellence through specialized domains
└── 43-metaverse-immersive/      # AR/VR/XR, spatial computing
```

### Categories by Cluster

| Cluster | Categories | Focus | Audits |
|---------|------------|-------|--------|
| **Core Technical** | 1-12 | Security, performance, reliability, architecture, data, APIs | ~756 |
| **Infrastructure** | 13-16 | IaC, usability, accessibility, SEO | ~205 |
| **Human & Experience** | 17-23 | Organizational, ethics, gamification, emotional design | ~272 |
| **Process & Governance** | 24-30 | Compliance, operations, documentation, risk | ~327 |
| **Economics & Dependencies** | 31-33 | Cost, supply chain, legacy migration | ~152 |
| **Specialized Domains** | 34-43 | ML/AI, embedded, blockchain, quantum, metaverse | ~477 |

## Current Status

| Metric | Value |
|--------|-------|
| Total Audits | 2186 |
| Categories Complete | 1-43 (all) |
| Target | ~2,200 audits |
| Completion | 99.5% |

## Audit File Format

```yaml
audit:
  id: "security-trust.authentication.oauth2-implementation"
  name: "OAuth2 Implementation Audit"
  tier: "expert"

description:
  what: |
    Evaluates OAuth2 implementation for security best practices...
  why_it_matters: |
    Flawed OAuth2 enables account takeover and privilege escalation...

signals:
  critical:
    - id: "OAUTH-CRIT-001"
      signal: "Authorization code used without PKCE"
      remediation: "Implement PKCE for all public clients"
  high:
    - id: "OAUTH-HIGH-001"
      signal: "Token refresh without rotation"

procedure:
  steps:
    - id: "1"
      name: "Identify OAuth flows"
      commands:
        - "grep -r 'oauth\\|authorize' --include='*.ts'"

closeout_checklist:
  - id: "oauth-001"
    item: "PKCE implementation verified"
    verification: "grep -r 'code_challenge' src/"
```

## Design Principles

### 1. Audits Have Two Components
- **Static Framework** (this taxonomy): What to check, signals, remediation
- **Project Grounding** (your project): PRDs, SLAs, compliance requirements

### 2. Completeness Varies
Some audits are **complete** (can run without project context):
- SQL Injection Audit
- TLS Configuration Audit

Some audits **require discovery** first:
- SLA Compliance Audit (needs: stated SLAs)
- Requirements Traceability (needs: requirements docs)

### 3. Cherry-Pick Per Project
Not every project needs every audit. A healthcare SaaS might select:
- Security & Trust (full)
- Compliance (with HIPAA overlay)
- Accessibility
- Performance (subset)

An embedded system might select:
- Real-Time & Embedded (full)
- Reliability & Resilience
- Security (subset)

## Industry Overlays

Domain-specific requirements extend the core taxonomy:

| Overlay | Standards | Key Concerns |
|---------|-----------|--------------|
| Healthcare | HIPAA, HL7, FHIR | PHI protection, clinical data |
| Finance | SOX, PCI-DSS | Trade surveillance, regulatory reporting |
| Defense | ITAR, NIST 800-53 | Classification, TEMPEST |
| Automotive | ISO 26262 | Functional safety |

## Repository Structure

```
.
├── audits/                  # The audit taxonomy (2186 YAML files across 43 categories)
│   ├── 01-security-trust/
│   ├── 02-performance-efficiency/
│   └── ... (43 categories total)
├── audit-browser/           # SvelteKit web UI for browsing audits
│   ├── src/
│   └── static/data/
├── schema/                  # Audit file templates and schemas
│   └── AUDIT-TEMPLATE-BLANK.yaml
├── docs/                    # Documentation
│   └── auditing-whitepaper.txt
├── AUDIT-INVENTORY.csv      # Machine-readable audit index for AI agents
└── README.md
```

## Usage

### Browse Audits
Explore the `audits/` directory by category and subcategory.

### Find Relevant Audits
```bash
# Find all authentication-related audits
find audits -name "*.yaml" -path "*auth*"

# Search for GDPR-related content
grep -r "GDPR" audits/ --include="*.yaml"
```

### Integrate with AI Agents
Load audit definitions as context for AI-powered code review, security scanning, or compliance checking.

## Contributing

The taxonomy is nearly complete with 2186 audits across 43 categories. Contributions welcome for:
- Improvements to existing audit signals and remediation guidance
- Industry overlay definitions (Healthcare, Finance, Defense, etc.)
- Tool integration references
- Bug fixes in YAML syntax

## License

[TBD]

---

*For the full design rationale, see [docs/auditing-whitepaper.txt](docs/auditing-whitepaper.txt)*
