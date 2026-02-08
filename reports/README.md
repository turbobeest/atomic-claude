# Reports Directory

This directory is for **analysis and scratch work ONLY**.

## Purpose

- Temporary analysis files
- Diagnostic outputs
- Scratch notes
- Investigation artifacts

## Rules

⚠️ **NOTHING permanent goes here**

All permanent artifacts must go in their proper locations:
- Prompts → `.outputs/{phase}/prompts/`
- Outputs → `.outputs/{phase}/outputs/`
- Specs → `.claude/specs/`
- Generated code → `../src/`
- Generated tests → `../tests/`
- Generated docs → `../docs/`

## Cleanup

This directory can be cleared at any time without affecting the pipeline.

```bash
# Safe to run anytime
rm -rf reports/*
git checkout reports/README.md
```
