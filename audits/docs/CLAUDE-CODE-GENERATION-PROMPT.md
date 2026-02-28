# AUDIT TAXONOMY GENERATION PROMPT
## Claude Code Multi-Agent Orchestration for ~2,200 Audit Files

---

## MISSION

You are orchestrating the generation of approximately 2,200 individual audit YAML files for a comprehensive Software Stack Audit Taxonomy. This taxonomy will serve as knowledge grounding for AI-powered audit agents.

You will operate as a **trio of specialized agents**, cycling through each audit systematically:

1. **Researcher Agent** — Investigates the audit topic to gather authoritative requirements
2. **Writer Agent** — Transforms research into a properly structured audit file
3. **Specialist Agent** — Reviews for domain accuracy and auditing best practices

---

## PROVIDED MATERIALS

You have been given these reference materials:

| Material | Purpose |
|----------|---------|
| `AUDIT-MENU.md` | Master index listing all ~2,200 audits organized by category/subcategory |
| `AUDIT-TEMPLATE.yaml` | Full template with OAuth2 as example |
| `AUDIT-TEMPLATE-BLANK.yaml` | Blank template with placeholder markers |
| `schema/examples/README.md` | Pattern selection guide (organizational vs infrastructure vs documentation) |
| `schema/examples/01-bus-factor-audit.yaml` | Example: Organizational/qualitative pattern |
| `schema/examples/02-container-resource-limits-audit.yaml` | Example: Infrastructure/metrics pattern |
| `schema/examples/03-runbook-completeness-audit.yaml` | Example: Process/documentation pattern |
| `REPO-STRUCTURE.md` | Repository layout and naming conventions |
| `audit-taxonomy-whitepaper.md` | Design philosophy and taxonomy rationale |
| `categories/*.md` | Category overview documents (43 files) |

**CRITICAL**: Before writing ANY audit, review `schema/examples/README.md` to select the appropriate pattern for the audit's domain. Not all audits follow the OAuth2/security code pattern.

---

## THE THREE AGENTS

### Agent 1: RESEARCHER 🔍

**Role**: Domain expert who investigates the audit topic

**Responsibilities**:
- Research authoritative sources for the audit topic (RFCs, OWASP, NIST, CIS, vendor docs, academic papers)
- Identify what signals/findings this audit should detect
- Determine appropriate tooling and verification approaches
- Understand the business impact and "why it matters"
- Find relevant compliance framework mappings (SOC2, ISO27001, etc.)

**Output**: A research brief containing:
```
RESEARCH BRIEF: {Audit Name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOMAIN PATTERN: {organizational | infrastructure | code-security | documentation | mixed}

AUTHORITATIVE SOURCES:
- {Source 1}: {URL or reference}
- {Source 2}: {URL or reference}
- ...

KEY CONCEPTS:
- {Concept 1}: {Brief explanation}
- ...

CRITICAL SIGNALS (what bad looks like):
- {Signal 1}: {Evidence pattern}
- {Signal 2}: {Evidence pattern}
- ...

POSITIVE SIGNALS (what good looks like):
- {Signal 1}: {Evidence pattern}
- ...

VERIFICATION APPROACHES:
- Automated: {Tools, commands, queries}
- Manual: {Review procedures, interviews}

COMPLIANCE MAPPINGS:
- {Framework}: {Control IDs}
- ...

BUSINESS IMPACT:
{Why this matters - what goes wrong if neglected}

RELATED AUDITS:
- {Related audit ID 1}
- {Related audit ID 2}
```

---

### Agent 2: WRITER ✍️

**Role**: Technical writer who creates the audit file

**Responsibilities**:
- Select the correct template pattern based on Researcher's domain classification
- Transform research into properly structured YAML
- Ensure all required fields are populated
- Write clear, actionable signal descriptions
- Create executable verification commands where applicable
- Maintain consistent naming conventions and ID formats

**Pattern Selection Logic**:
```
IF domain == "organizational" OR domain == "qualitative":
    USE pattern from 01-bus-factor-audit.yaml
    - interviews instead of code_patterns
    - evidence_indicators instead of evidence_pattern
    - manual verification with verification_notes
    - automatable: "manual"
    
ELIF domain == "infrastructure" OR domain == "metrics":
    USE pattern from 02-container-resource-limits-audit.yaml
    - kubectl/cloud CLI commands
    - metrics_queries with thresholds
    - quantitative verification_expected
    - automatable: "yes"
    
ELIF domain == "documentation" OR domain == "process":
    USE pattern from 03-runbook-completeness-audit.yaml
    - file_patterns and documents_to_review
    - mixed automated + manual verification
    - automatable: "partial"
    
ELSE (code/config/security):
    USE pattern from AUDIT-TEMPLATE.yaml (OAuth2 example)
    - code_patterns with regex
    - static analysis tooling
    - bash verification commands
    - CWE mappings for security
```

**Output**: Complete YAML audit file following the template structure

---

### Agent 3: SPECIALIST 🎯

**Role**: Audit methodology expert who ensures quality

**Responsibilities**:
- Verify the audit follows sound auditing principles
- Check that signals are specific and actionable (not vague)
- Ensure verification commands would actually work
- Validate severity classifications are appropriate
- Confirm the audit is complete enough to be useful
- Check for domain-appropriate patterns (no grep for organizational audits!)

**Review Checklist**:
```
□ IDENTITY: Hierarchical ID follows convention (category.subcategory.audit-slug)
□ PATTERN: Correct pattern selected for domain
□ SIGNALS: At least 2 critical, 2 high, 2 medium signals defined
□ EVIDENCE: Evidence patterns are specific, not generic
□ VERIFICATION: Closeout checklist has executable checks (or proper manual flags)
□ REMEDIATION: Each signal has actionable remediation guidance
□ KNOWLEDGE: External sources are authoritative and cacheable
□ PROFILES: Correct profile membership (quick/security/production/full)
□ RELATIONSHIPS: Related audits are properly cross-referenced
□ COMPLETENESS: All [REQUIRED] fields populated
```

**Output**: 
- APPROVED ✓ (with any minor suggestions)
- REVISION NEEDED ✗ (with specific issues to fix)

---

## EXECUTION WORKFLOW

For each audit in AUDIT-MENU.md:

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: RESEARCHER investigates the audit topic            │
│  - Read category overview from categories/{nn}-{slug}.md    │
│  - Research authoritative sources                           │
│  - Produce research brief                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: WRITER creates the audit file                      │
│  - Select appropriate pattern from examples                 │
│  - Transform research into YAML structure                   │
│  - Populate all required fields                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: SPECIALIST reviews the audit                       │
│  - Apply review checklist                                   │
│  - If APPROVED: Save file and proceed                       │
│  - If REVISION NEEDED: Return to WRITER with feedback       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Save approved audit file                           │
│  Path: audits/{nn}-{category}/{subcategory}/{audit}.yaml    │
│  Log completion                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## BATCH PROCESSING STRATEGY

Given ~2,200 audits, process in batches by category:

```
PHASE 1: Core Technical (Categories 1-12)
  └── ~800 audits, highest priority
  
PHASE 2: Infrastructure (Categories 13-16)
  └── ~200 audits
  
PHASE 3: Human & Experience (Categories 17-23)
  └── ~350 audits, DIFFERENT PATTERN - organizational focus
  
PHASE 4: Process & Governance (Categories 24-30)
  └── ~350 audits, mixed patterns
  
PHASE 5: Economics & Dependencies (Categories 31-33)
  └── ~150 audits
  
PHASE 6: Specialized Domains (Categories 34-43)
  └── ~350 audits, varied patterns
```

**Within each category**, process audits in subcategory order as listed in AUDIT-MENU.md.

---

## FILE NAMING AND PATHS

**Audit File Path Convention**:
```
audits/{nn}-{category-slug}/{subcategory-slug}/{audit-slug}.yaml
```

**Examples**:
```
audits/01-security-trust/authentication/oauth2-implementation.yaml
audits/20-human-organizational/knowledge-distribution/bus-factor.yaml
audits/27-documentation-knowledge/operational/runbook-completeness.yaml
```

**Hierarchical ID Convention** (inside the file):
```yaml
audit:
  id: "{category-slug}.{subcategory-slug}.{audit-slug}"
```

**Examples**:
```yaml
id: "security-trust.authentication.oauth2-implementation"
id: "human-organizational.knowledge-distribution.bus-factor"
id: "documentation-knowledge.operational.runbook-completeness"
```

---

## QUALITY GATES

Before saving any audit file, verify:

### Gate 1: Structure Validation
```yaml
# All these fields must be present and non-empty
audit:
  id: ✓
  name: ✓
  version: ✓
  category: ✓
  subcategory: ✓
  tier: ✓
  completeness: ✓

execution:
  automatable: ✓
  severity: ✓
  scope: ✓
  default_profiles: ✓

description:
  what: ✓
  why_it_matters: ✓

signals:
  critical: [at least 1]
  high: [at least 1]

closeout_checklist: [at least 2 items]
```

### Gate 2: Pattern Appropriateness
```
IF category in [17, 18, 20, 21, 22, 23]:  # Human/Experience
    VERIFY automatable in ["manual", "partial"]
    VERIFY discovery uses interviews or documents_to_review
    VERIFY closeout_checklist has manual verification items
    
IF category in [13, 14, 15, 16]:  # Infrastructure
    VERIFY discovery uses kubernetes_resources or metrics_queries
    VERIFY signals have quantitative thresholds
    
IF category == 1:  # Security
    VERIFY signals have CWE mappings where applicable
    VERIFY knowledge_sources includes OWASP or NIST
```

### Gate 3: Actionability Check
```
FOR each signal:
    VERIFY remediation is specific, not "fix this issue"
    VERIFY evidence_pattern OR evidence_indicators is defined
    
FOR each closeout_checklist item:
    IF verification != "manual":
        VERIFY command is syntactically valid bash
```

---

## ANTI-PATTERNS TO AVOID

❌ **DO NOT** use grep patterns for organizational audits:
```yaml
# WRONG
signals:
  critical:
    - evidence_pattern: "grep -r 'bus factor' docs/"  # Nonsense
```

❌ **DO NOT** claim everything is automatable:
```yaml
# WRONG for category 20 (Human & Organizational)
execution:
  automatable: "yes"  # Interviews cannot be automated
```

❌ **DO NOT** use vague signals:
```yaml
# WRONG
signals:
  critical:
    - signal: "Security is not good"  # Too vague
      remediation: "Make it better"   # Not actionable
```

❌ **DO NOT** copy OAuth2 patterns blindly:
```yaml
# WRONG for runbook audit
discovery:
  code_patterns:
    - pattern: "OAuth|OIDC"  # Irrelevant to runbooks
```

✅ **DO** adapt to the domain:
```yaml
# CORRECT for organizational audit
discovery:
  interviews:
    - role: "Engineering Manager"
      questions: ["..."]
      
# CORRECT for infrastructure audit
discovery:
  metrics_queries:
    - system: "Prometheus"
      query: "..."
      threshold: "> 0.8"
```

---

## PROGRESS TRACKING

Maintain a progress log:

```
AUDIT GENERATION PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Category 01: Security & Trust
  ├── authentication: 10/10 ✓
  ├── authorization: 0/10 [in progress]
  ├── cryptography: 0/10
  └── ...
  
Category 02: Performance & Efficiency
  └── [not started]

...

TOTALS:
  Completed: 45/2200 (2%)
  In Progress: 1
  Remaining: 2154
```

---

## STARTING POINT

Begin with this sequence:

1. **Read and internalize** the provided materials:
   - `schema/examples/README.md` (pattern selection)
   - `AUDIT-TEMPLATE-BLANK.yaml` (structure)
   - All three example audits (patterns)
   - `AUDIT-MENU.md` (what to generate)

2. **Start with Category 01: Security & Trust, Subcategory: Authentication**
   - First audit: `oauth2-implementation` (already have example)
   - Second audit: `session-management`
   - Continue through subcategory...

3. **After completing Category 01**, proceed to Category 02, and so on.

4. **When reaching Category 17-23** (Human & Experience), explicitly switch to organizational patterns.

---

## AGENT COMMUNICATION FORMAT

Use this format when cycling through agents:

```
═══════════════════════════════════════════════════════════════
🔍 RESEARCHER AGENT
───────────────────────────────────────────────────────────────
Audit: {category}.{subcategory}.{audit-name}
File: audits/{nn}-{category}/{subcategory}/{audit}.yaml

[Research brief here]

═══════════════════════════════════════════════════════════════
✍️ WRITER AGENT
───────────────────────────────────────────────────────────────
Pattern Selected: {organizational | infrastructure | documentation | code-security}
Based on: {rationale}

[YAML content here]

═══════════════════════════════════════════════════════════════
🎯 SPECIALIST AGENT
───────────────────────────────────────────────────────────────
Review Checklist:
□ Identity: {PASS/FAIL}
□ Pattern: {PASS/FAIL}
□ Signals: {PASS/FAIL}
□ Evidence: {PASS/FAIL}
□ Verification: {PASS/FAIL}
□ Remediation: {PASS/FAIL}
□ Knowledge: {PASS/FAIL}
□ Profiles: {PASS/FAIL}
□ Relationships: {PASS/FAIL}
□ Completeness: {PASS/FAIL}

Verdict: {APPROVED ✓ | REVISION NEEDED ✗}
Notes: {any feedback}

═══════════════════════════════════════════════════════════════
```

---

## FINAL INSTRUCTIONS

1. **Be thorough**: Each audit should be complete enough that an agent could execute it
2. **Be specific**: Signals and remediation must be actionable, not generic
3. **Be appropriate**: Match the pattern to the domain
4. **Be consistent**: Follow naming conventions exactly
5. **Be efficient**: Don't over-research common topics; use knowledge from similar audits

**Your goal is to produce ~2,200 high-quality, domain-appropriate audit files that can serve as authoritative knowledge grounding for AI-powered audit agents.**

Begin when ready. Start with Category 01, Subcategory: Authentication, Audit: session-management (since oauth2-implementation already exists as an example).

---

*Prompt Version: 1.0*
*Expected Output: ~2,200 YAML audit files*
*Estimated Time: Significant (batch over multiple sessions)*
