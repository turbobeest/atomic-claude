# AUDIT GENERATION QUICK REFERENCE

## Pattern Selection Decision Tree

```
Is this audit about CODE or CONFIG?
│
├─► YES: Is it SECURITY-focused?
│        ├─► YES → Use OAuth2 pattern (AUDIT-TEMPLATE.yaml)
│        │         • code_patterns, static analysis
│        │         • CWE mappings, security signals
│        │         • automatable: "yes" or "partial"
│        │
│        └─► NO → Is it INFRASTRUCTURE?
│                 ├─► YES → Use Container pattern (example 02)
│                 │         • kubectl, cloud CLI, metrics_queries
│                 │         • quantitative thresholds
│                 │         • automatable: "yes"
│                 │
│                 └─► NO → Use OAuth2 pattern (code quality, API, etc.)
│
└─► NO: Is this about PEOPLE or TEAMS?
         │
         ├─► YES → Use Bus Factor pattern (example 01)
         │         • interviews, documents_to_review
         │         • evidence_indicators (not evidence_pattern)
         │         • automatable: "manual"
         │         • verification: "manual" with verification_notes
         │
         └─► NO → Use Runbook pattern (example 03)
                  • file_patterns, analysis_checklist
                  • mixed automated + manual verification
                  • automatable: "partial"
```

---

## Category-to-Pattern Quick Map

| Categories | Pattern | Key Markers |
|------------|---------|-------------|
| 01 Security & Trust | OAuth2/Code | CWE, OWASP, static analysis |
| 02 Performance | Infrastructure | metrics_queries, thresholds |
| 03 Reliability | Mixed | fault patterns + metrics |
| 04 Scalability | Infrastructure | capacity thresholds |
| 05 Observability | Infrastructure | monitoring queries |
| 06 Code Quality | OAuth2/Code | linters, static analysis |
| 07 Architecture | Mixed | design review + patterns |
| 08 Data & State | Mixed | schema checks + queries |
| 09 API & Integration | OAuth2/Code | contract testing |
| 10 Messaging | Infrastructure | queue metrics |
| 11 Time & Scheduling | Code | time pattern checks |
| 12 Versioning | Documentation | process review |
| 13-16 Infrastructure | Infrastructure | kubectl, cloud CLI |
| 17 Usability | Organizational | heuristic evaluation |
| 18 Accessibility | Mixed | automated scans + manual |
| 19 SEO | Infrastructure | crawl scores |
| 20-23 Human/Experience | **Organizational** | interviews, surveys |
| 24-30 Process/Governance | Documentation | artifact review |
| 31 Cost & Economics | Infrastructure | cost queries |
| 32 Dependencies | Code | SBOM, vulnerability scan |
| 33 Legacy | Mixed | assessment + code |
| 34 Business Logic | Code | domain rule checks |
| 35 Developer Experience | Mixed | tooling + surveys |
| 36 i18n/L10n | Code | i18n pattern checks |
| 37 ML/AI | Mixed | metrics + qualitative |
| 38-40 Sensors/RT/Signal | Infrastructure | embedded metrics |
| 41 Blockchain | Code (security) | smart contract analysis |
| 42-43 Quantum/Metaverse | Mixed | novel domains |

---

## Required Fields Checklist

```yaml
audit:
  id: ✓ REQUIRED         # category.subcategory.audit-slug
  name: ✓ REQUIRED       # Human-readable name
  version: ✓ REQUIRED    # "1.0.0"
  status: ✓ REQUIRED     # "active"
  category: ✓ REQUIRED   # category-slug
  category_number: ✓ REQUIRED  # 1-43
  subcategory: ✓ REQUIRED
  tier: ✓ REQUIRED       # focused|expert|phd
  completeness: ✓ REQUIRED    # complete|requires_discovery
  requires_runtime: ✓ REQUIRED
  destructive: ✓ REQUIRED

execution:
  automatable: ✓ REQUIRED     # yes|partial|manual
  severity: ✓ REQUIRED        # critical|high|medium|low
  scope: ✓ REQUIRED           # codebase|infrastructure|organizational|documentation|...
  default_profiles: ✓ REQUIRED

description:
  what: ✓ REQUIRED
  why_it_matters: ✓ REQUIRED

signals:
  critical: ✓ REQUIRED (at least 1)
  high: ✓ REQUIRED (at least 1)
  medium: ✓ REQUIRED (at least 1)

procedure:
  context:
    cognitive_mode: ✓ REQUIRED
    ensemble_role: ✓ REQUIRED
  steps: ✓ REQUIRED (at least 2)

output:
  confidence_guidance: ✓ REQUIRED

closeout_checklist: ✓ REQUIRED (at least 2 items)

profiles:
  membership: ✓ REQUIRED
```

---

## Signal Structure by Pattern

### Code/Security Pattern
```yaml
signals:
  critical:
    - id: "{CAT}-CRIT-001"
      signal: "Description"
      evidence_pattern: "regex or grep pattern"
      verification_command: "bash command"
      verification_expected: "expected output"
      cwe: "CWE-XXX"
      remediation: "How to fix"
```

### Infrastructure Pattern
```yaml
signals:
  critical:
    - id: "{CAT}-CRIT-001"
      signal: "Description"
      evidence_threshold: "metric > X or < Y"
      verification_command: "kubectl/query command"
      verification_expected: "0" or "PASS"
      remediation: "How to fix"
```

### Organizational Pattern
```yaml
signals:
  critical:
    - id: "{CAT}-CRIT-001"
      signal: "Description"
      evidence_indicators:
        - "Observable behavior 1"
        - "Observable behavior 2"
      explanation: "Why this matters"
      remediation: "How to address"
```

---

## Closeout Checklist Patterns

### Automated (bash)
```yaml
closeout_checklist:
  - id: "audit-001"
    item: "What is verified"
    level: "CRITICAL"  # CRITICAL|BLOCKING|WARNING
    verification: "bash command that outputs PASS or FAIL"
    expected: "PASS"
```

### Manual (human review)
```yaml
closeout_checklist:
  - id: "audit-002"
    item: "What is verified"
    level: "BLOCKING"
    verification: "manual"
    verification_notes: "What reviewer should confirm"
    expected: "Confirmed by reviewer"
```

---

## File Path Formula

```
audits/{NN}-{category-slug}/{subcategory-slug}/{audit-slug}.yaml
```

Where:
- `{NN}` = zero-padded category number (01-43)
- `{category-slug}` = lowercase-hyphenated category name
- `{subcategory-slug}` = lowercase-hyphenated subcategory name
- `{audit-slug}` = lowercase-hyphenated audit name

---

## Common Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Using grep for org audits | Use interviews/evidence_indicators |
| `automatable: "yes"` for interviews | Use `automatable: "manual"` |
| Vague signals like "security issue" | Be specific: "tokens stored in localStorage" |
| Generic remediation "fix this" | Specific: "Move tokens to httpOnly cookies" |
| Missing CWE for security signals | Add CWE-XXX reference |
| Wrong pattern for category 20-23 | Must use organizational pattern |
| Bash commands for qualitative | Use `verification: "manual"` |

---

## Agent Cycle Summary

```
🔍 RESEARCHER → Research brief with sources, signals, approaches
       ↓
✍️ WRITER → Complete YAML file using correct pattern
       ↓
🎯 SPECIALIST → Review checklist, approve or request revision
       ↓
💾 SAVE → audits/{path}/{file}.yaml
```

---

*Quick Reference v1.0*
