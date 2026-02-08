# Audits Repository Instructions

## Purpose

This repository contains the master audit dimension library - a comprehensive menu of all software development audits organized by category.

## Key Files

- `menu/index.json` - Master index of all audit dimensions
- `menu/categories/*.json` - Audit definitions by category
- `tasks/*/` - Phase-specific audit task definitions
- `profiles/*.json` - Pre-baked audit groupings

## When Working Here

1. **Adding new audits**: Add to appropriate `menu/categories/*.json` file
2. **Creating profiles**: Add to `profiles/` with clear naming
3. **Mapping to tasks**: Update `tasks/*/applicable-dimensions.json`

## Audit Definition Schema

```json
{
  "id": "SEC-001",
  "name": "Authentication mechanisms defined",
  "description": "Verify authentication requirements are specified",
  "category": "security",
  "severity": "critical",
  "scope": "prd|code|deployment",
  "automatable": "yes|partial|manual",
  "checklist": ["item1", "item2"],
  "evidence_required": ["artifact1", "artifact2"]
}
```

## Severity Levels

- `critical` - Blocks proceeding, must address
- `high` - Significant risk if ignored
- `medium` - Improves quality
- `low` - Nice to have

## Task Mapping

Each task in `tasks/` maps audit dimensions to a specific phase:
- `prd-audit` → Phase 4 (PRD Validation)
- `integration-audit` → Phase 7 (Integration)
- `deployment-audit` → Phase 8 (Deployment Prep)
