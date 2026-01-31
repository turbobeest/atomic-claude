# AUDIT-INVENTORY.csv Schema Documentation

## Purpose

The AUDIT-INVENTORY.csv enables rapid downselection of relevant audits based on:
- **SDLC Phase**: Which phase(s) of software development is this audit applicable to?
- **Resource Constraints**: What resources (source code, runtime data, team input, etc.) are required?
- **Automation Level**: Can this be fully automated, or does it require human judgment?
- **Phase Restrictions**: Is this audit only valid pre-production, post-production, or any time?

## Column Definitions

### Identity Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `audit_id` | string | Full audit ID from YAML file | `security-trust.authentication.oauth2-implementation` |
| `file_path` | string | Relative path to YAML file | `audits/01-security-trust/authentication/oauth2-implementation.yaml` |
| `audit_name` | string | Human-readable name | `OAuth2/OIDC Implementation Audit` |
| `category` | string | Category directory name | `01-security-trust` |
| `category_number` | integer | Numeric category (1-43) | `1` |
| `subcategory` | string | Subcategory directory name | `authentication` |
| `tier` | enum | Audit complexity tier | `focused` / `expert` / `phd` |
| `status` | enum | Implementation status | `active` / `planned` |

### Status Column

| Value | Description |
|-------|-------------|
| `active` | YAML file exists and is fully defined (categories 1-20) |
| `planned` | Audit is defined in AUDIT-MENU.md but YAML not yet created (categories 21-43) |

**Usage**: Filter `status = 'active'` when you need audits with complete YAML definitions.

### SDLC Phase Applicability Columns

Each column indicates whether the audit is applicable during that SDLC phase.

| Column | Description |
|--------|-------------|
| `discovery` | Initial project discovery, understanding requirements |
| `prd` | Product Requirements Document phase |
| `task_decomposition` | Breaking work into tasks |
| `specification` | Technical specification writing |
| `tdd` | Test-Driven Development (writing tests first) |
| `implementation` | Active code writing |
| `testing` | Testing phase (unit, integration, e2e) |
| `integration` | System integration |
| `deployment` | Deployment to environments |
| `post_production` | Running in production |

**Values**: `yes` / `no`

### Resource Requirement Columns

| Column | Description |
|--------|-------------|
| `requires_source_code` | Needs access to source code |
| `requires_runtime_data` | Needs metrics, logs, or runtime observations |
| `requires_cost_data` | Needs billing/cost information |
| `requires_team_input` | Needs human interviews or surveys |
| `requires_production_access` | Needs access to production environment |

**Values**: `yes` / `no`

### Automation Level Columns (mutually exclusive)

| Column | Description |
|--------|-------------|
| `fully_automated` | Can be run entirely by tools/scripts |
| `semi_automated` | Tools can assist, but human review needed |
| `human_required` | Requires human judgment/expertise |

**Values**: `yes` / `no`
**Constraint**: Exactly one should be `yes`

### Phase Restriction Columns (mutually exclusive)

| Column | Description |
|--------|-------------|
| `pre_production_only` | Only valid before production deployment |
| `production_only` | Only valid in production |
| `any_phase` | Valid at any phase |

**Values**: `yes` / `no`
**Constraint**: Exactly one should be `yes`

### Optional Enhancement Columns

| Column | Type | Description |
|--------|------|-------------|
| `primary_phase` | enum | The SDLC phase where this audit is MOST valuable |
| `automation_tools` | string | Comma-separated list of tools that can automate |
| `dependencies` | string | Other audit IDs that should be run first |
| `tags` | string | Comma-separated tags for additional filtering |

## Usage Examples

### Filter for implementation phase with source code access

```bash
# Using csvq or similar
csvq "SELECT audit_id, audit_name FROM audit_inventory WHERE implementation = 'yes' AND requires_source_code = 'yes'"
```

### Filter for fully automated pre-production audits

```bash
csvq "SELECT audit_id FROM audit_inventory WHERE fully_automated = 'yes' AND pre_production_only = 'yes'"
```

### AI Agent Usage

When an AI agent receives constraints like:
- "We're in the implementation phase"
- "We have source code but no production access"
- "We need automated checks only"

The agent filters:
```
implementation = 'yes'
requires_source_code = 'yes'
requires_production_access = 'no'
fully_automated = 'yes'
```

## Mapping from Legacy audit_id to New Format

| Legacy Pattern | New Format | Example |
|---------------|------------|---------|
| `sec_auth_001` | `security-trust.authentication.{slug}` | `security-trust.authentication.oauth2-implementation` |
| `perf_latency_001` | `performance-efficiency.latency.{slug}` | `performance-efficiency.latency.end-to-end-latency` |
| `rel_fault_001` | `reliability-resilience.fault-tolerance.{slug}` | `reliability-resilience.fault-tolerance.single-point-of-failure` |

## Validation Rules

1. `audit_id` must exist in corresponding YAML file (for `status = 'active'`)
2. `file_path` must be a valid path relative to repository root (for `status = 'active'`)
3. `category_number` must be 1-43
4. `status` must be `active` or `planned`
5. Exactly one of `fully_automated`, `semi_automated`, `human_required` must be `yes`
6. Exactly one of `pre_production_only`, `production_only`, `any_phase` must be `yes`
7. At least one SDLC phase must be `yes`

## Current Statistics

| Metric | Value |
|--------|-------|
| Total Audits | 2,079 |
| Active (Categories 1-20) | 1,134 |
| Planned (Categories 21-43) | 945 |
| Categories | 43 |
| Columns | 29 |
