# ATOMIC CLAUDE UI Style Guide

## Header Styles (High-Tech Theme)

All header functions are defined in `lib/atomic.sh`.

### H1: Matrix Dots (Light Blue)
**Usage:** Phase headers, major sections
**Color:** `\033[94m` (LIGHT_BLUE)
**Function:** `atomic_h1 "TITLE"`

```
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
  ⬢ PHASE 1: DISCOVERY
∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙∙
```

### H2: Light Trace (Light Grey)
**Usage:** Subsections, task headers, step labels
**Color:** `\033[90m` (LIGHT_GREY)
**Function:** `atomic_h2 "Title"`

```
─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  Agent Selection
```

### Entry Banner: Compact Tech (Light Blue)
**Usage:** Phase entry tasks (x01 tasks only)
**Color:** `\033[94m` (LIGHT_BLUE)
**Function:** `atomic_entry_banner "PHASE N: NAME" "task_num"`

```
══════════════════════════════════════════════════════════════════════
  ▶▶ PHASE 1: DISCOVERY ─────────────────────────────────────── [101]
══════════════════════════════════════════════════════════════════════
```

### Closeout Banner: Terminal Return (Light Grey)
**Usage:** Phase closeout tasks only
**Color:** `\033[90m` (LIGHT_GREY)
**Function:** `atomic_closeout_banner "Phase N Complete"`

```
                                                    ▪▪▪ CLOSEOUT ▪▪▪
```

## Task Type → Header Mapping

| Task Type | h1_header | h2_header | entry_banner | closeout_banner |
|-----------|-----------|-----------|--------------|-----------------|
| Entry (x01) | yes | no | yes | no |
| Agent Selection | no | yes | no | no |
| Phase Audit | no | yes | no | no |
| Closeout (last) | no | no | no | yes |
| All Others | no | yes | no | no |

## Color Reference

| Variable | ANSI Code | Usage |
|----------|-----------|-------|
| `LIGHT_BLUE` | `\033[94m` | H1 headers, entry banners |
| `LIGHT_GREY` | `\033[90m` | H2 headers, closeout banners |
| `GREEN` | `\033[0;32m` | Success messages |
| `RED` | `\033[0;31m` | Error messages |
| `YELLOW` | `\033[1;33m` | Warnings |
| `CYAN` | `\033[0;36m` | Step markers |
| `DIM` | `\033[2m` | Subdued text |
| `NC` | `\033[0m` | Reset/No color |

## Example Task Implementation

```bash
task_101_entry_validation() {
    # Entry task gets the full banner
    atomic_entry_banner "PHASE 1: DISCOVERY" "101"

    # Subsections use H2
    atomic_h2 "Validating Phase 0 Completion"

    # ... task logic ...

    atomic_success "Entry validation complete"
}

task_110_closeout() {
    atomic_h2 "Phase Closeout"

    # ... task logic ...

    atomic_closeout_banner "Phase 1 Complete"
}
```

## Deprecated Functions

| Old Function | Replacement |
|--------------|-------------|
| `atomic_header()` | `atomic_h1()` (aliased for compatibility) |
| `atomic_output_box()` | `atomic_h2()` + content |
