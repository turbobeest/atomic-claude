# Audits Repository

A comprehensive, standalone audit dimension library for software development workflows.

## Overview

This repository provides a **master menu of audit dimensions** that can be used across any Claude Code session, ATOMIC-CLAUDE pipeline, or custom development workflow.

## Structure

```
audits/
├── menu/                    # Master audit menu - ALL possible dimensions
│   ├── categories/          # Audit dimensions by category
│   │   ├── requirements.json
│   │   ├── security.json
│   │   ├── performance.json
│   │   └── ...
│   └── index.json           # Master index of all audits
│
├── tasks/                   # Audit task definitions (phase-specific)
│   ├── prd-audit/           # PRD validation audits
│   ├── integration-audit/   # Integration testing audits
│   ├── deployment-audit/    # Deployment readiness audits
│   └── ...
│
├── profiles/                # Pre-baked audit groupings
│   ├── quick.json           # Minimal essential audits
│   ├── standard.json        # Balanced coverage
│   ├── comprehensive.json   # Full audit suite
│   └── ...
│
├── templates/               # Templates for custom audits
├── knowledge/               # Audit methodology documentation
└── ui/                      # Svelte admin interface (planned)
```

## Usage

### With ATOMIC-CLAUDE

The pipeline's audit tasks reference this repository to:
1. Present available audit dimensions
2. Allow profile selection or customization
3. Execute selected audits
4. Generate audit reports

### Standalone

Load audit definitions directly:
```bash
# Get all security audits
jq '.audits' menu/categories/security.json

# Get quick profile
jq '.' profiles/quick.json
```

### Web Interface (Planned)

A Svelte-based admin interface for:
- Browsing the audit menu
- Creating custom profiles
- Managing audit task mappings

## Audit Categories

| Category | Description | Audits |
|----------|-------------|--------|
| Requirements | Completeness, clarity, testability | 15 |
| Security | Auth, encryption, OWASP | 12 |
| Performance | Response time, throughput, scaling | 10 |
| Reliability | Fault tolerance, recovery | 8 |
| Integration | API contracts, data exchange | 10 |
| Compliance | GDPR, regulatory, privacy | 8 |
| Observability | Metrics, logging, tracing | 8 |
| Deployment | CI/CD, rollback, environments | 8 |
| Data | Models, validation, migration | 8 |
| User Experience | Accessibility, usability | 10 |
| ... | Additional categories | ... |

## Profiles

| Profile | Audits | Use Case |
|---------|--------|----------|
| `quick` | ~15 | Fast validation, MVP |
| `standard` | ~35 | Balanced coverage |
| `security-focused` | ~25 | Security-critical apps |
| `production-ready` | ~50 | Pre-release validation |
| `comprehensive` | ~100 | Full audit suite |

## Contributing

See `templates/` for creating new audit dimensions.

## Related

- [agents](../agents) - Agent definitions repository
- [dev-sys](../dev-sys) - Development pipeline system
- [ATOMIC-CLAUDE](../ATOMIC-CLAUDE) - Pipeline prototype
