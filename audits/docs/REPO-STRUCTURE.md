# Audit Taxonomy Repository Structure

> Recommended directory layout for housing ~2,200 audit files with supporting infrastructure

---

## Top-Level Structure

```
audit-taxonomy/
│
├── README.md                           # Repo overview, quick start
├── AUDIT-MENU.md                       # Master index of all audits (~75KB)
├── CONTRIBUTING.md                     # How to add/modify audits
├── CHANGELOG.md                        # Version history
├── LICENSE                             # License file
│
├── schema/                             # Template definitions and examples
├── categories/                         # Category overview documents (43)
├── audits/                             # Individual audit files (~2,200)
├── industry-overlays/                  # Modular industry extensions
├── bundles/                            # Pre-composed audit profiles
├── knowledge-cache/                    # Offline knowledge sources
├── tooling/                            # Scripts, rules, utilities
├── validation/                         # JSON schemas, linting
└── docs/                               # Extended documentation
```

---

## Detailed Structure

```
audit-taxonomy/
│
│── README.md
│── AUDIT-MENU.md
│── CONTRIBUTING.md
│── CHANGELOG.md
│── LICENSE
│
├── schema/
│   ├── AUDIT-TEMPLATE.yaml             # Full template with OAuth2 example
│   ├── AUDIT-TEMPLATE-BLANK.yaml       # Blank slate for generation
│   ├── AUDIT-TEMPLATE-DESIGN.md        # Design philosophy doc
│   │
│   └── examples/
│       ├── README.md                   # Pattern selection guide
│       ├── 01-bus-factor-audit.yaml    # Organizational/qualitative pattern
│       ├── 02-container-resource-limits-audit.yaml  # Infrastructure/metrics
│       └── 03-runbook-completeness-audit.yaml       # Process/documentation
│
├── categories/
│   │   # Core Technical (1-12)
│   ├── 01-security-trust.md
│   ├── 02-performance-efficiency.md
│   ├── 03-reliability-resilience.md
│   ├── 04-scalability-capacity.md
│   ├── 05-observability-instrumentation.md
│   ├── 06-code-quality-craftsmanship.md
│   ├── 07-architecture-design.md
│   ├── 08-data-state-management.md
│   ├── 09-api-integration.md
│   ├── 10-messaging-event-systems.md
│   ├── 11-time-scheduling.md
│   ├── 12-versioning-lifecycle.md
│   │
│   │   # Infrastructure (13-16)
│   ├── 13-compute-orchestration.md
│   ├── 14-network-infrastructure.md
│   ├── 15-storage-infrastructure.md
│   ├── 16-infrastructure-as-code.md
│   │
│   │   # Human & Experience (17-23)
│   ├── 17-usability-interaction-design.md
│   ├── 18-accessibility-inclusion.md
│   ├── 19-seo-web-discoverability.md
│   ├── 20-human-organizational.md
│   ├── 21-responsible-design.md
│   ├── 22-gamification-behavioral-design.md
│   ├── 23-emotional-design-trust.md
│   │
│   │   # Process & Governance (24-30)
│   ├── 24-compliance-governance.md
│   ├── 25-operational-excellence.md
│   ├── 26-testing-quality-assurance.md
│   ├── 27-documentation-knowledge.md
│   ├── 28-requirements-specification-quality.md
│   ├── 29-risk-management.md
│   ├── 30-configuration-management.md
│   │
│   │   # Economics & Dependencies (31-33)
│   ├── 31-cost-economics.md
│   ├── 32-dependency-supply-chain.md
│   ├── 33-legacy-migration.md
│   │
│   │   # Specialized Domains (34-43)
│   ├── 34-business-logic-domain.md
│   ├── 35-developer-experience.md
│   ├── 36-internationalization-localization.md
│   ├── 37-machine-learning-ai.md
│   ├── 38-sensors-physical-systems.md
│   ├── 39-real-time-embedded.md
│   ├── 40-signal-processing-data-acquisition.md
│   ├── 41-blockchain-distributed-ledger.md
│   ├── 42-quantum-computing.md
│   └── 43-metaverse-immersive.md
│
├── audits/
│   │   # Mirrored structure: category/subcategory/audit.yaml
│   │
│   ├── 01-security-trust/
│   │   ├── authentication/
│   │   │   ├── oauth2-implementation.yaml
│   │   │   ├── session-management.yaml
│   │   │   ├── mfa-implementation.yaml
│   │   │   ├── password-policy.yaml
│   │   │   ├── api-key-management.yaml
│   │   │   ├── sso-federated-identity.yaml
│   │   │   └── ...
│   │   ├── authorization/
│   │   │   ├── rbac-implementation.yaml
│   │   │   ├── abac-implementation.yaml
│   │   │   ├── permission-boundary.yaml
│   │   │   └── ...
│   │   ├── cryptography/
│   │   │   ├── encryption-at-rest.yaml
│   │   │   ├── encryption-in-transit.yaml
│   │   │   ├── key-management.yaml
│   │   │   └── ...
│   │   ├── input-validation/
│   │   ├── secrets-management/
│   │   ├── network-security/
│   │   ├── application-security/
│   │   ├── data-protection/
│   │   ├── threat-modeling/
│   │   └── security-operations/
│   │
│   ├── 02-performance-efficiency/
│   │   ├── latency/
│   │   ├── throughput/
│   │   ├── resource-utilization/
│   │   ├── database-performance/
│   │   ├── caching/
│   │   ├── algorithmic-efficiency/
│   │   ├── concurrency-parallelism/
│   │   ├── frontend-performance/
│   │   ├── network-efficiency/
│   │   └── profiling-benchmarking/
│   │
│   ├── 03-reliability-resilience/
│   │   ├── fault-tolerance/
│   │   ├── disaster-recovery/
│   │   ├── data-consistency/
│   │   ├── error-handling/
│   │   ├── chaos-engineering/
│   │   ├── high-availability/
│   │   └── data-durability/
│   │
│   │   # ... (categories 04-12 follow same pattern)
│   │
│   ├── 13-compute-orchestration/
│   │   ├── container-configuration/
│   │   │   ├── resource-limits.yaml
│   │   │   ├── image-security.yaml
│   │   │   ├── pod-security.yaml
│   │   │   └── ...
│   │   ├── kubernetes-workloads/
│   │   ├── serverless/
│   │   └── vm-management/
│   │
│   │   # ... (categories 14-19 follow same pattern)
│   │
│   ├── 20-human-organizational/
│   │   ├── knowledge-distribution/
│   │   │   ├── bus-factor.yaml
│   │   │   ├── documentation-coverage.yaml
│   │   │   └── ...
│   │   ├── ownership/
│   │   ├── cognitive-load/
│   │   └── team-health/
│   │
│   │   # ... (categories 21-26 follow same pattern)
│   │
│   ├── 27-documentation-knowledge/
│   │   ├── operational/
│   │   │   ├── runbook-completeness.yaml
│   │   │   ├── architecture-docs.yaml
│   │   │   └── ...
│   │   ├── api-documentation/
│   │   ├── developer-guides/
│   │   └── decision-records/
│   │
│   │   # ... (remaining categories follow same pattern)
│   │
│   └── 43-metaverse-immersive/
│       ├── spatial-computing/
│       ├── presence-immersion/
│       ├── motion-sickness/
│       └── 3d-asset-integrity/
│
├── industry-overlays/
│   │   # Each overlay extends core categories with industry-specific audits
│   │
│   ├── README.md                       # How overlays work
│   ├── overlay-template.yaml           # Template for new overlays
│   │
│   ├── defense-intelligence/
│   │   ├── overlay.yaml                # Metadata, standards, certifications
│   │   ├── security-extensions.yaml    # Extends 01-security-trust
│   │   ├── compliance-extensions.yaml  # Extends 24-compliance-governance
│   │   └── data-extensions.yaml        # Extends 08-data-state-management
│   │
│   ├── healthcare/
│   │   ├── overlay.yaml
│   │   ├── hipaa-security.yaml
│   │   ├── hipaa-privacy.yaml
│   │   ├── phi-handling.yaml
│   │   └── clinical-data.yaml
│   │
│   ├── finance-banking/
│   │   ├── overlay.yaml
│   │   ├── pci-dss.yaml
│   │   ├── sox-compliance.yaml
│   │   ├── trade-surveillance.yaml
│   │   └── regulatory-reporting.yaml
│   │
│   ├── automotive/
│   │   ├── overlay.yaml
│   │   └── iso-26262.yaml
│   │
│   ├── aviation-aerospace/
│   │   ├── overlay.yaml
│   │   └── do-178c.yaml
│   │
│   ├── energy-utilities/
│   ├── pharmaceuticals/
│   ├── education/
│   ├── government/
│   ├── retail-ecommerce/
│   ├── media-entertainment/
│   ├── telecommunications/
│   ├── manufacturing/
│   ├── agriculture-food/
│   ├── legal/
│   ├── insurance/
│   ├── real-estate/
│   └── logistics-supply-chain/
│
├── bundles/
│   │   # Pre-composed audit sets for common scenarios
│   │
│   ├── README.md                       # How bundles work
│   ├── bundle-template.yaml            # Template for new bundles
│   │
│   │   # Standard profiles (from dev-sys pattern)
│   ├── profiles/
│   │   ├── quick.yaml                  # ~15 essential audits, 15 min
│   │   ├── security.yaml               # ~40 security-focused audits
│   │   ├── production.yaml             # ~60 production readiness audits
│   │   └── full.yaml                   # All applicable audits
│   │
│   │   # Domain-specific bundles
│   ├── domains/
│   │   ├── authentication-security.yaml
│   │   ├── api-health.yaml
│   │   ├── data-integrity.yaml
│   │   ├── kubernetes-hardening.yaml
│   │   ├── observability-maturity.yaml
│   │   └── ml-ops.yaml
│   │
│   │   # Compliance-driven bundles
│   ├── compliance/
│   │   ├── soc2-type2.yaml
│   │   ├── iso27001.yaml
│   │   ├── pci-dss-v4.yaml
│   │   ├── hipaa.yaml
│   │   ├── gdpr.yaml
│   │   └── fedramp-moderate.yaml
│   │
│   │   # Lifecycle bundles
│   └── lifecycle/
│       ├── pre-production.yaml
│       ├── post-incident.yaml
│       ├── quarterly-review.yaml
│       └── pre-acquisition.yaml
│
├── knowledge-cache/
│   │   # Pre-downloaded knowledge for offline execution
│   │
│   ├── README.md                       # Cache management instructions
│   ├── manifest.yaml                   # Index of all cached items
│   ├── refresh.sh                      # Script to update cache
│   │
│   ├── specifications/
│   │   ├── rfc/
│   │   │   ├── rfc6749-oauth2.html
│   │   │   ├── rfc7636-pkce.html
│   │   │   └── ...
│   │   ├── w3c/
│   │   │   ├── wcag-2.1.html
│   │   │   └── ...
│   │   ├── ietf/
│   │   ├── iso/                        # Summaries only (copyrighted)
│   │   └── nist/
│   │       ├── 800-53-r5.pdf
│   │       └── ...
│   │
│   ├── guides/
│   │   ├── owasp/
│   │   │   ├── asvs-4.0.html
│   │   │   ├── cheatsheets/
│   │   │   └── top-10-2021.html
│   │   ├── cis/
│   │   │   ├── kubernetes-benchmark.pdf
│   │   │   └── ...
│   │   └── cloud/
│   │       ├── aws-well-architected.html
│   │       ├── gcp-best-practices.html
│   │       └── azure-security-baseline.html
│   │
│   ├── vulnerabilities/
│   │   ├── nvd-mirror/                 # National Vulnerability Database
│   │   └── cwe-list.xml
│   │
│   └── tools/
│       ├── semgrep-rules-offline.tar.gz
│       └── pip-packages/               # Offline Python packages
│
├── tooling/
│   │   # Scripts, rules, and utilities used by audits
│   │
│   ├── README.md
│   │
│   ├── semgrep-rules/
│   │   ├── security/
│   │   │   ├── oauth-misconfig.yaml
│   │   │   ├── jwt-vulnerabilities.yaml
│   │   │   └── ...
│   │   ├── performance/
│   │   └── quality/
│   │
│   ├── scripts/
│   │   ├── python/
│   │   │   ├── requirements.txt
│   │   │   ├── runbook_analyzer.py
│   │   │   ├── bus_factor_calculator.py
│   │   │   └── ...
│   │   ├── bash/
│   │   │   ├── k8s-resource-checker.sh
│   │   │   ├── git-contributor-analysis.sh
│   │   │   └── ...
│   │   └── common/
│   │       └── output-formatter.py
│   │
│   ├── queries/
│   │   ├── prometheus/
│   │   │   ├── resource-utilization.promql
│   │   │   └── ...
│   │   ├── sql/
│   │   └── datadog/
│   │
│   └── templates/
│       ├── finding-report.md
│       ├── executive-summary.md
│       └── remediation-plan.md
│
├── validation/
│   │   # Schema validation and linting
│   │
│   ├── audit-schema.json              # JSON Schema for audit files
│   ├── bundle-schema.json             # JSON Schema for bundles
│   ├── overlay-schema.json            # JSON Schema for overlays
│   │
│   ├── lint-audit.py                  # Lint individual audit files
│   ├── validate-all.sh                # Validate entire repo
│   │
│   └── tests/
│       ├── test_audit_schema.py
│       └── test_bundle_integrity.py
│
└── docs/
    │   # Extended documentation
    │
    ├── getting-started.md
    ├── architecture.md                 # How the taxonomy is designed
    ├── agent-integration.md            # How orchestrators consume this
    ├── offline-usage.md                # Air-gapped deployment guide
    │
    ├── guides/
    │   ├── writing-audits.md           # How to write good audits
    │   ├── creating-bundles.md
    │   ├── adding-overlays.md
    │   └── contributing-tooling.md
    │
    └── adr/                            # Architecture Decision Records
        ├── 001-yaml-over-json.md
        ├── 002-hierarchical-ids.md
        ├── 003-offline-first.md
        └── ...
```

---

## Naming Conventions

### Audit Files
```
{nn}-{category-slug}/
  {subcategory-slug}/
    {audit-slug}.yaml

Example: 01-security-trust/authentication/oauth2-implementation.yaml
```

### Hierarchical IDs (inside files)
```yaml
id: "{category-slug}.{subcategory-slug}.{audit-slug}"

Example: "security-trust.authentication.oauth2-implementation"
```

### Bundle Files
```
{scope}-{purpose}.yaml

Examples:
  - profiles/quick.yaml
  - compliance/soc2-type2.yaml
  - domains/authentication-security.yaml
```

### Overlay Files
```
{industry}/
  overlay.yaml              # Metadata
  {category}-extensions.yaml  # Extensions per category

Example: healthcare/security-extensions.yaml
```

---

## File Counts (Estimated)

| Directory | Files | Notes |
|-----------|-------|-------|
| `/schema` | ~8 | Templates + examples |
| `/categories` | 43 | One per category |
| `/audits` | ~2,200 | Individual audit files |
| `/industry-overlays` | ~50-100 | ~3-5 per industry × 18 industries |
| `/bundles` | ~25 | Profiles + domains + compliance + lifecycle |
| `/knowledge-cache` | ~200-500 | Cached external sources |
| `/tooling` | ~50-100 | Scripts, rules, queries |
| `/validation` | ~10 | Schemas + tests |
| `/docs` | ~15 | Guides + ADRs |

**Total: ~2,500-3,000 files**

---

## Key Design Decisions

### 1. Category Numbers as Prefixes
```
01-security-trust/
02-performance-efficiency/
```
Enables natural sorting and quick identification.

### 2. Flat Subcategory Depth
```
audits/01-security-trust/authentication/oauth2-implementation.yaml
```
Only 3 levels deep. Avoids deeply nested structures.

### 3. Separate Overlays from Core
Industry-specific content lives in `/industry-overlays`, not mixed into `/audits`. Keeps core taxonomy clean.

### 4. Bundles Reference by ID
```yaml
# bundles/profiles/security.yaml
audits:
  - security-trust.authentication.oauth2-implementation
  - security-trust.authentication.session-management
```
Bundles reference audits by hierarchical ID, not file path.

### 5. Knowledge Cache is Optional
The repo works without `/knowledge-cache`. Agents can fetch sources on-demand. Cache enables offline execution.

### 6. Validation Separate from Content
JSON schemas and linting tools live in `/validation`, not scattered throughout.

---

## Git Considerations

### .gitignore
```
# Ignore generated files
.audit-results/
*.pyc
__pycache__/
node_modules/

# Large cache files (may be LFS or separate)
knowledge-cache/specifications/**/*.pdf
knowledge-cache/vulnerabilities/nvd-mirror/
```

### Git LFS (Large File Storage)
Consider LFS for:
- PDF specifications in `/knowledge-cache`
- NVD mirror data
- Large tool packages

### Branch Strategy
```
main              # Stable, validated
develop           # Integration branch
feature/*         # New audits, categories
hotfix/*          # Urgent fixes
release/v*        # Release branches
```

---

## Quick Start Commands

```bash
# Clone repo
git clone https://github.com/org/audit-taxonomy.git
cd audit-taxonomy

# Validate all audit files
./validation/validate-all.sh

# Run a specific audit (orchestrator integration)
./orchestrator run --audit security-trust.authentication.oauth2-implementation

# Run a profile
./orchestrator run --profile security

# Prepare offline bundle
./knowledge-cache/refresh.sh --audit-ids security-trust.*

# Add new audit
cp schema/AUDIT-TEMPLATE-BLANK.yaml audits/01-security-trust/authentication/new-audit.yaml
# Edit, then validate
./validation/lint-audit.py audits/01-security-trust/authentication/new-audit.yaml
```

---

*Last Updated: January 2025*
