# Task: Categorize Project Materials

You are analyzing a list of files from a software project.
Categorize them into useful groups for a development pipeline.

## Instructions

1. Review the list of file paths provided via stdin
2. Categorize each file by its likely purpose
3. Output a JSON manifest

## Categories

- documentation: README, guides, docs
- configuration: package.json, tsconfig, etc
- specification: API specs, OpenAPI, schemas
- test: Test files, fixtures
- source: Source code files
- other: Anything else

## Output Format

Output valid JSON in this format:
```json
{
  "materials": [
    {"path": "file/path.md", "type": "md", "category": "documentation"},
    {"path": "package.json", "type": "json", "category": "configuration"}
  ],
  "summary": {
    "documentation": 5,
    "configuration": 3,
    "specification": 1,
    "test": 0,
    "source": 0,
    "other": 2
  }
}
```

## File List

(File list will be provided via stdin)
