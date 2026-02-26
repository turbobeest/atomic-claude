#!/usr/bin/env python3
"""
Skill catalog for atomic-claude's skill system.

Defines all 64 SDLC skills with full metadata. Used by:
- install-skills.sh (via CLI interface)
- ingestion scripts (via Python import)
- profile-based gating (allowed/blocked skill resolution)

Usage as module:
    from scripts.skills.skill_catalog import SKILL_CATALOG, get_skill, get_skills_for_phase

Usage as CLI:
    python3 scripts/skills/skill_catalog.py                    # dump full catalog as JSON
    python3 scripts/skills/skill_catalog.py --id format-code   # single skill
    python3 scripts/skills/skill_catalog.py --phase 5          # skills for phase 5
    python3 scripts/skills/skill_catalog.py --category security # skills by category
    python3 scripts/skills/skill_catalog.py --profile air-gapped # allowed/blocked split
    python3 scripts/skills/skill_catalog.py --stats            # summary statistics
"""

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Valid enum values (for validation)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = frozenset({
    "formatting", "validation", "extraction", "git-ops", "file-ops",
    "phase-checks", "doc-gen", "testing", "security", "architecture",
    "deployment", "monitoring", "data", "api", "performance",
    "accessibility",
})

VALID_SOURCES = frozenset({
    "anthropic-official", "playbooks", "awesome-claude-code",
    "community", "tactical-builtin",
})

VALID_RISK_LEVELS = frozenset({None, "None", "Low", "Medium", "High"})

# ---------------------------------------------------------------------------
# Profile definitions — what each profile allows
# ---------------------------------------------------------------------------

PROFILE_RULES: Dict[str, Dict] = {
    "air-gapped": {
        "allow_internet": False,
        "allow_saas": False,
        "max_risk": "Low",
    },
    "sensitive": {
        "allow_internet": True,
        "allow_saas": False,
        "max_risk": "Low",
    },
    "standard": {
        "allow_internet": True,
        "allow_saas": True,
        "max_risk": "Medium",
    },
    "unrestricted": {
        "allow_internet": True,
        "allow_saas": True,
        "max_risk": "High",
    },
}

_RISK_ORDER = {"None": 0, None: 0, "Low": 1, "Medium": 2, "High": 3}

# ---------------------------------------------------------------------------
# Catalog data — 64 skills
# ---------------------------------------------------------------------------

SKILL_CATALOG: List[Dict] = [
    # ==================================================================
    # TACTICAL BUILTINS (20 skills)
    # ==================================================================

    # -- Formatting (3) --
    {
        "id": "format-code",
        "name": "Format Code",
        "description": "Auto-format source code using language-appropriate formatters (black, prettier, gofmt, rustfmt). Runs the formatter and reports results without explanation.",
        "sdlc_phases": [5, 6],
        "category": "formatting",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "lint-check",
        "name": "Lint Check",
        "description": "Run language-specific linters (ruff, eslint, golangci-lint) and report findings. No explanation or fix suggestions, just raw lint output.",
        "sdlc_phases": [5, 6, 7],
        "category": "formatting",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "type-check",
        "name": "Type Check",
        "description": "Run static type checkers (mypy, tsc, pyright) and report type errors. Returns pass/fail with error locations.",
        "sdlc_phases": [5, 6, 7],
        "category": "formatting",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # -- Validation (4) --
    {
        "id": "validate-json",
        "name": "Validate JSON",
        "description": "Parse and validate JSON files. Reports syntax errors with line numbers and character positions.",
        "sdlc_phases": [0, 1, 2, 3, 4],
        "category": "validation",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "validate-yaml",
        "name": "Validate YAML",
        "description": "Parse and validate YAML files. Reports syntax errors and structural issues.",
        "sdlc_phases": [0, 1, 4, 8],
        "category": "validation",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "validate-openapi",
        "name": "Validate OpenAPI",
        "description": "Validate OpenAPI/Swagger specification files for schema compliance and completeness.",
        "sdlc_phases": [4, 5, 7],
        "category": "validation",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "validate-prd",
        "name": "Validate PRD",
        "description": "Quick completeness check on PRD documents. Verifies required sections, acceptance criteria, and traceability links exist.",
        "sdlc_phases": [2, 3],
        "category": "validation",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },

    # -- Extraction (3) --
    {
        "id": "extract-todos",
        "name": "Extract TODOs",
        "description": "Find TODO, FIXME, HACK, and NOTE comments across the codebase. Returns file paths, line numbers, and comment text.",
        "sdlc_phases": [1, 5, 6],
        "category": "extraction",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "extract-functions",
        "name": "Extract Functions",
        "description": "List function and method signatures from source files. Returns name, parameters, return type, and file location.",
        "sdlc_phases": [1, 4, 5],
        "category": "extraction",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "extract-imports",
        "name": "Extract Imports",
        "description": "List all import/require/include statements and map dependency usage across the codebase.",
        "sdlc_phases": [1, 5, 6],
        "category": "extraction",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # -- Git Operations (2) --
    {
        "id": "quick-status",
        "name": "Quick Status",
        "description": "Git status summary: current branch, staged/unstaged changes, recent commits, and remote tracking state.",
        "sdlc_phases": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "category": "git-ops",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "quick-diff",
        "name": "Quick Diff",
        "description": "Git diff summary with file-level change statistics. Supports comparing against any ref (HEAD~N, branch, tag).",
        "sdlc_phases": [5, 6, 7, 9],
        "category": "git-ops",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # -- File Operations (3) --
    {
        "id": "count-lines",
        "name": "Count Lines",
        "description": "Count lines of code by language using tokei/cloc. Reports per-language and total counts excluding blanks and comments.",
        "sdlc_phases": [1, 5, 7],
        "category": "file-ops",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "find-duplicates",
        "name": "Find Duplicates",
        "description": "Detect duplicate or near-duplicate code blocks across the codebase. Reports file pairs with similarity scores.",
        "sdlc_phases": [5, 6],
        "category": "file-ops",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "check-imports-unused",
        "name": "Check Unused Imports",
        "description": "Find unused import statements that can be safely removed. Supports Python, JavaScript, and TypeScript.",
        "sdlc_phases": [5, 6],
        "category": "file-ops",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # -- Phase Checks (3) --
    {
        "id": "check-phase-outputs",
        "name": "Check Phase Outputs",
        "description": "Verify that required output artifacts exist for a given phase. Checks file presence, non-empty content, and expected structure.",
        "sdlc_phases": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "category": "phase-checks",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "check-test-coverage",
        "name": "Check Test Coverage",
        "description": "Run test coverage analysis and report percentage by module. Highlights uncovered files and low-coverage areas.",
        "sdlc_phases": [5, 6, 7],
        "category": "phase-checks",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "phase-summary",
        "name": "Phase Summary",
        "description": "Display current pipeline phase progress: completed tasks, pending tasks, blockers, and time estimates.",
        "sdlc_phases": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "category": "phase-checks",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },

    # -- Doc Generation (2) --
    {
        "id": "generate-changelog",
        "name": "Generate Changelog",
        "description": "Auto-generate changelog entries from git commit history. Groups by type (feat, fix, refactor) with links to commits.",
        "sdlc_phases": [8, 9],
        "category": "doc-gen",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "generate-api-summary",
        "name": "Generate API Summary",
        "description": "Generate a concise API endpoint summary from OpenAPI specs or source code route definitions.",
        "sdlc_phases": [4, 5, 8],
        "category": "doc-gen",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # ==================================================================
    # COMMUNITY SKILLS — superpowers (6 skills)
    # ==================================================================
    {
        "id": "planning",
        "name": "Planning",
        "description": "Structured planning workflow: break down goals into milestones, define dependencies, estimate effort, and produce actionable plans.",
        "sdlc_phases": [0, 1, 2, 3],
        "category": "architecture",
        "source": "community",
        "source_url": "https://github.com/obra/superpowers",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "research",
        "name": "Research",
        "description": "Systematic research workflow: gather information from codebase, docs, and context to answer architectural and technical questions.",
        "sdlc_phases": [1, 2, 4],
        "category": "architecture",
        "source": "community",
        "source_url": "https://github.com/obra/superpowers",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "tdd",
        "name": "Test-Driven Development",
        "description": "RED-GREEN-REFACTOR workflow: write failing test first, implement minimal code to pass, then refactor. Enforces strict TDD discipline.",
        "sdlc_phases": [5, 6, 7],
        "category": "testing",
        "source": "community",
        "source_url": "https://github.com/obra/superpowers",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "debugging",
        "name": "Systematic Debugging",
        "description": "Structured debugging workflow: reproduce, isolate, hypothesize, verify, fix. Maintains a hypothesis log throughout the session.",
        "sdlc_phases": [5, 6, 7],
        "category": "testing",
        "source": "community",
        "source_url": "https://github.com/obra/superpowers",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "code-review-assistant",
        "name": "Code Review Assistant",
        "description": "Structured code review: check style, correctness, security, performance, and maintainability. Produces review comments with severity levels.",
        "sdlc_phases": [6],
        "category": "testing",
        "source": "community",
        "source_url": "https://github.com/obra/superpowers",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "performance-optimization",
        "name": "Performance Optimization",
        "description": "Profile and optimize code: identify bottlenecks, suggest algorithmic improvements, benchmark before/after. Focuses on measurable gains.",
        "sdlc_phases": [5, 6, 7],
        "category": "performance",
        "source": "community",
        "source_url": "https://github.com/obra/superpowers",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # ==================================================================
    # COMMUNITY SKILLS — trailofbits (6 skills)
    # ==================================================================
    {
        "id": "security-audit",
        "name": "Security Audit",
        "description": "Comprehensive security audit using Trail of Bits methodology: threat modeling, attack surface analysis, vulnerability identification with CVSS scoring.",
        "sdlc_phases": [1, 6, 7, 8],
        "category": "security",
        "source": "community",
        "source_url": "https://github.com/trailofbits/skills",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Read-only analysis, no code modification",
        "well_known": True,
        "official": False,
        "license": "Apache-2.0",
    },
    {
        "id": "dependency-scan",
        "name": "Dependency Scan",
        "description": "Scan project dependencies for known vulnerabilities using CVE databases. Reports severity, affected versions, and remediation paths.",
        "sdlc_phases": [1, 5, 7, 8],
        "category": "security",
        "source": "community",
        "source_url": "https://github.com/trailofbits/skills",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Fetches CVE data from public databases",
        "well_known": True,
        "official": False,
        "license": "Apache-2.0",
    },
    {
        "id": "secrets-detection",
        "name": "Secrets Detection",
        "description": "Scan codebase for leaked secrets: API keys, tokens, passwords, private keys. Uses pattern matching and entropy analysis.",
        "sdlc_phases": [5, 6, 7, 8],
        "category": "security",
        "source": "community",
        "source_url": "https://github.com/trailofbits/skills",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Read-only scanning, reports findings to stdout",
        "well_known": True,
        "official": False,
        "license": "Apache-2.0",
    },
    {
        "id": "fuzzing-harness",
        "name": "Fuzzing Harness",
        "description": "Generate fuzzing harnesses for target functions using AFL++, libFuzzer, or atheris. Creates seed corpus and runs initial fuzzing campaign.",
        "sdlc_phases": [5, 7],
        "category": "security",
        "source": "community",
        "source_url": "https://github.com/trailofbits/skills",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": True,
        "risk_level": "Medium",
        "risk_notes": "Generates and executes test harness code; review generated code before running",
        "well_known": True,
        "official": False,
        "license": "Apache-2.0",
    },
    {
        "id": "static-analysis",
        "name": "Static Analysis",
        "description": "Run Semgrep and CodeQL rules against the codebase. Produces SARIF reports with finding locations, severity, and remediation guidance.",
        "sdlc_phases": [5, 6, 7],
        "category": "security",
        "source": "community",
        "source_url": "https://github.com/trailofbits/skills",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Read-only analysis using local rule sets",
        "well_known": True,
        "official": False,
        "license": "Apache-2.0",
    },
    {
        "id": "supply-chain-audit",
        "name": "Supply Chain Audit",
        "description": "Audit software supply chain: verify package provenance, check for typosquatting, validate lock file integrity, review transitive dependencies.",
        "sdlc_phases": [1, 7, 8],
        "category": "security",
        "source": "community",
        "source_url": "https://github.com/trailofbits/skills",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Queries public package registries for provenance data",
        "well_known": True,
        "official": False,
        "license": "Apache-2.0",
    },

    # ==================================================================
    # EXTERNAL SKILLS — playbooks / awesome-claude-code (20 skills)
    # ==================================================================
    {
        "id": "react-best-practices",
        "name": "React Best Practices",
        "description": "Enforce React best practices: component composition, hooks usage, state management patterns, memo/callback optimization, and accessibility attributes.",
        "sdlc_phases": [4, 5, 6],
        "category": "architecture",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "nextjs-patterns",
        "name": "Next.js Patterns",
        "description": "Apply Next.js architectural patterns: App Router conventions, server components, data fetching strategies, middleware, and ISR/SSG configuration.",
        "sdlc_phases": [4, 5, 6],
        "category": "architecture",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "api-design",
        "name": "API Design",
        "description": "Design RESTful and GraphQL APIs following best practices: resource naming, versioning, pagination, error responses, and HATEOAS links.",
        "sdlc_phases": [2, 4, 5],
        "category": "api",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "database-optimization",
        "name": "Database Optimization",
        "description": "Optimize database queries and schema: index analysis, query plan review, N+1 detection, connection pooling configuration, and migration safety checks.",
        "sdlc_phases": [4, 5, 6],
        "category": "data",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "May suggest schema changes; review before applying migrations",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "docker-best-practices",
        "name": "Docker Best Practices",
        "description": "Audit and improve Dockerfiles: multi-stage builds, layer caching, security hardening, image size reduction, and healthcheck configuration.",
        "sdlc_phases": [5, 8],
        "category": "deployment",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Reviews Dockerfiles; does not build or push images",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "ci-cd-pipeline",
        "name": "CI/CD Pipeline",
        "description": "Generate and audit CI/CD configurations for GitHub Actions, GitLab CI, or CircleCI. Covers build, test, lint, security scan, and deploy stages.",
        "sdlc_phases": [5, 7, 8],
        "category": "deployment",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": True,
        "risk_level": "Medium",
        "risk_notes": "Generates workflow files that run in CI; review before committing",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "terraform-infrastructure",
        "name": "Terraform Infrastructure",
        "description": "Generate and review Terraform configurations: resource definitions, state management, module composition, and plan review before apply.",
        "sdlc_phases": [8],
        "category": "deployment",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": True,
        "risk_level": "High",
        "risk_notes": "Infrastructure as code affects cloud resources; always run plan before apply",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "kubernetes-deployment",
        "name": "Kubernetes Deployment",
        "description": "Generate and validate Kubernetes manifests: deployments, services, ingress, RBAC, resource limits, and readiness/liveness probes.",
        "sdlc_phases": [8, 9],
        "category": "deployment",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": True,
        "risk_level": "High",
        "risk_notes": "Kubernetes manifests affect live clusters; validate in staging first",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "monitoring-setup",
        "name": "Monitoring Setup",
        "description": "Configure monitoring and alerting: Prometheus metrics, Grafana dashboards, alert rules, SLO definitions, and on-call escalation policies.",
        "sdlc_phases": [8, 9],
        "category": "monitoring",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": True,
        "requires_saas": True,
        "saas_dependencies": ["prometheus", "grafana"],
        "security_scan_needed": False,
        "risk_level": "Medium",
        "risk_notes": "Connects to monitoring SaaS endpoints; credentials required",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "error-tracking",
        "name": "Error Tracking",
        "description": "Integrate error tracking services: Sentry SDK setup, source map upload, release tracking, alert configuration, and issue grouping rules.",
        "sdlc_phases": [5, 8],
        "category": "monitoring",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": True,
        "requires_saas": True,
        "saas_dependencies": ["sentry"],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Requires Sentry DSN; SDK sends error data to Sentry servers",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "accessibility-audit",
        "name": "Accessibility Audit",
        "description": "Audit web content for WCAG 2.1 compliance: color contrast, ARIA attributes, keyboard navigation, screen reader compatibility, and focus management.",
        "sdlc_phases": [5, 6, 7],
        "category": "accessibility",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "seo-optimization",
        "name": "SEO Optimization",
        "description": "Audit and improve SEO: meta tags, structured data (JSON-LD), sitemap generation, canonical URLs, Core Web Vitals, and social graph tags.",
        "sdlc_phases": [5, 6, 8],
        "category": "performance",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "graphql-schema",
        "name": "GraphQL Schema",
        "description": "Design and validate GraphQL schemas: type definitions, resolver patterns, N+1 prevention with DataLoader, pagination (cursor/offset), and schema stitching.",
        "sdlc_phases": [4, 5],
        "category": "api",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "rest-api-testing",
        "name": "REST API Testing",
        "description": "Generate API test suites: endpoint coverage, authentication flows, error scenarios, rate limiting validation, and contract testing with OpenAPI specs.",
        "sdlc_phases": [5, 7],
        "category": "testing",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "load-testing",
        "name": "Load Testing",
        "description": "Generate load test scripts for k6, Locust, or Artillery. Define scenarios, ramp-up profiles, and thresholds. Analyze results for bottlenecks.",
        "sdlc_phases": [7, 8],
        "category": "performance",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Medium",
        "risk_notes": "Load tests generate significant traffic; run against staging, never production",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "mobile-responsive",
        "name": "Mobile Responsive",
        "description": "Audit and fix responsive design: breakpoint coverage, touch target sizes, viewport meta, fluid typography, and container query usage.",
        "sdlc_phases": [5, 6],
        "category": "accessibility",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "internationalization",
        "name": "Internationalization",
        "description": "Audit and implement i18n: extract hardcoded strings, configure i18next/react-intl, handle plurals, RTL support, and locale-specific formatting.",
        "sdlc_phases": [4, 5],
        "category": "architecture",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "authentication-patterns",
        "name": "Authentication Patterns",
        "description": "Implement authentication flows: JWT/session management, OAuth2/OIDC integration, MFA setup, CSRF protection, and secure cookie configuration.",
        "sdlc_phases": [4, 5, 6],
        "category": "security",
        "source": "playbooks",
        "source_url": "https://github.com/anthropics/claude-code-playbooks",
        "requires_internet": True,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": True,
        "risk_level": "High",
        "risk_notes": "Authentication code is security-critical; always review generated auth logic",
        "well_known": True,
        "official": True,
        "license": "MIT",
    },
    {
        "id": "caching-strategies",
        "name": "Caching Strategies",
        "description": "Design and implement caching layers: Redis/Memcached setup, cache invalidation patterns, CDN configuration, HTTP cache headers, and stale-while-revalidate.",
        "sdlc_phases": [4, 5],
        "category": "performance",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Cache misconfiguration can serve stale data; test invalidation thoroughly",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "microservices-patterns",
        "name": "Microservices Patterns",
        "description": "Apply microservices patterns: service boundaries, API gateways, circuit breakers, saga orchestration, event sourcing, and distributed tracing.",
        "sdlc_phases": [2, 4, 5],
        "category": "architecture",
        "source": "awesome-claude-code",
        "source_url": "https://github.com/wonhyeongseo/awesome-claude-code",
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Architectural guidance; review service boundary decisions carefully",
        "well_known": True,
        "official": False,
        "license": "MIT",
    },

    # ==================================================================
    # CUSTOM / SYNTHESIZED SKILLS — atomic-claude-specific (12 skills)
    # ==================================================================
    {
        "id": "prd-authoring",
        "name": "PRD Authoring",
        "description": "Guide PRD creation: stakeholder identification, problem statement, user stories, acceptance criteria, technical constraints, and scope boundaries.",
        "sdlc_phases": [2],
        "category": "doc-gen",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "spec-writing",
        "name": "Spec Writing",
        "description": "Generate technical specifications from PRD requirements: data models, API contracts, sequence diagrams, and component interfaces.",
        "sdlc_phases": [3, 4],
        "category": "doc-gen",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "task-decomposition",
        "name": "Task Decomposition",
        "description": "Break down features into implementation tasks: estimate complexity, identify dependencies, assign phases, and create task graphs.",
        "sdlc_phases": [3],
        "category": "architecture",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "agent-orchestration",
        "name": "Agent Orchestration",
        "description": "Select and configure agents for task execution: match agent expertise to task requirements, resolve conflicts, and manage agent context.",
        "sdlc_phases": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "category": "architecture",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "memory-management",
        "name": "Memory Management",
        "description": "Manage pipeline memory: checkpoint creation, context compaction, memory recall optimization, and dual-write to file/graph stores.",
        "sdlc_phases": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "category": "data",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "graph-query-builder",
        "name": "Graph Query Builder",
        "description": "Build and execute FalkorDB Cypher queries: node/edge creation, traversal patterns, fulltext search, and result aggregation for the knowledge graph.",
        "sdlc_phases": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "category": "data",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Low",
        "risk_notes": "Write queries modify graph state; use read-only queries for exploration",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "audit-runner",
        "name": "Audit Runner",
        "description": "Execute audit categories from the 43-category audit framework: select categories, run checks, collect evidence, and produce scored reports.",
        "sdlc_phases": [6, 7, 8],
        "category": "phase-checks",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "release-checklist",
        "name": "Release Checklist",
        "description": "Generate and track release checklists: version bump, changelog, tag, artifact build, smoke tests, rollback plan, and stakeholder notification.",
        "sdlc_phases": [8, 9],
        "category": "deployment",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "rollback-procedures",
        "name": "Rollback Procedures",
        "description": "Generate rollback playbooks: database migration reversal, deployment rollback steps, feature flag toggles, and communication templates.",
        "sdlc_phases": [8, 9],
        "category": "deployment",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Medium",
        "risk_notes": "Rollback procedures affect production state; test in staging first",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "incident-response",
        "name": "Incident Response",
        "description": "Structured incident response: severity classification, runbook selection, communication templates, root cause analysis, and post-incident review.",
        "sdlc_phases": [9],
        "category": "monitoring",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "Medium",
        "risk_notes": "Incident response may trigger automated actions; review runbooks before activation",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "compliance-check",
        "name": "Compliance Check",
        "description": "Validate compliance against frameworks: SOC2 controls, GDPR data handling, HIPAA safeguards, PCI-DSS requirements, and license compatibility.",
        "sdlc_phases": [6, 7, 8],
        "category": "security",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
    {
        "id": "cost-estimation",
        "name": "Cost Estimation",
        "description": "Estimate infrastructure and API costs: compute sizing, LLM token budgets, storage projections, bandwidth estimates, and monthly/annual forecasts.",
        "sdlc_phases": [2, 4, 8],
        "category": "architecture",
        "source": "tactical-builtin",
        "source_url": None,
        "requires_internet": False,
        "requires_saas": False,
        "saas_dependencies": [],
        "security_scan_needed": False,
        "risk_level": "None",
        "risk_notes": "",
        "well_known": False,
        "official": False,
        "license": "MIT",
    },
]


# ---------------------------------------------------------------------------
# Validation (runs at import time to catch data errors early)
# ---------------------------------------------------------------------------

def _validate_catalog() -> None:
    """Validate catalog integrity at import time."""
    ids_seen: set = set()
    for i, skill in enumerate(SKILL_CATALOG):
        sid = skill.get("id")
        if not sid:
            raise ValueError(f"Skill at index {i} missing 'id'")
        if sid in ids_seen:
            raise ValueError(f"Duplicate skill id: {sid}")
        ids_seen.add(sid)

        if skill.get("category") not in VALID_CATEGORIES:
            raise ValueError(
                f"Skill {sid}: invalid category '{skill.get('category')}'. "
                f"Valid: {sorted(VALID_CATEGORIES)}"
            )
        if skill.get("source") not in VALID_SOURCES:
            raise ValueError(
                f"Skill {sid}: invalid source '{skill.get('source')}'. "
                f"Valid: {sorted(VALID_SOURCES)}"
            )
        rl = skill.get("risk_level")
        if rl not in VALID_RISK_LEVELS:
            raise ValueError(
                f"Skill {sid}: invalid risk_level '{rl}'. "
                f"Valid: {sorted(str(v) for v in VALID_RISK_LEVELS)}"
            )
        phases = skill.get("sdlc_phases", [])
        for p in phases:
            if not isinstance(p, int) or p < 0 or p > 9:
                raise ValueError(
                    f"Skill {sid}: invalid phase {p}. Must be 0-9."
                )

    if len(ids_seen) != 64:
        raise ValueError(
            f"Expected 64 skills, got {len(ids_seen)}: "
            f"check SKILL_CATALOG definition"
        )


_validate_catalog()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SKILL_INDEX: Dict[str, Dict] = {s["id"]: s for s in SKILL_CATALOG}


def get_skill(skill_id: str) -> Optional[Dict]:
    """
    Look up a single skill by its kebab-case id.

    Returns:
        Skill dict or None if not found.
    """
    return _SKILL_INDEX.get(skill_id)


def get_skills_for_phase(phase_num: int) -> List[Dict]:
    """
    Return all skills that apply to a given SDLC phase (0-9).

    Returns:
        List of skill dicts sorted by id.
    """
    return sorted(
        [s for s in SKILL_CATALOG if phase_num in s.get("sdlc_phases", [])],
        key=lambda s: s["id"],
    )


def get_skills_by_category(category: str) -> List[Dict]:
    """
    Return all skills in a given category.

    Returns:
        List of skill dicts sorted by id.
    """
    return sorted(
        [s for s in SKILL_CATALOG if s.get("category") == category],
        key=lambda s: s["id"],
    )


def get_skills_by_source(source: str) -> List[Dict]:
    """
    Return all skills from a given source.

    Returns:
        List of skill dicts sorted by id.
    """
    return sorted(
        [s for s in SKILL_CATALOG if s.get("source") == source],
        key=lambda s: s["id"],
    )


def get_skills_by_profile(profile_name: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Split the catalog into allowed and blocked skills based on a profile.

    Args:
        profile_name: One of air-gapped, sensitive, standard, unrestricted

    Returns:
        (allowed, blocked) — two lists of skill dicts.

    Raises:
        ValueError: If profile_name is not recognized.
    """
    if profile_name not in PROFILE_RULES:
        raise ValueError(
            f"Unknown profile: {profile_name}. "
            f"Available: {sorted(PROFILE_RULES.keys())}"
        )

    rules = PROFILE_RULES[profile_name]
    allow_internet = rules["allow_internet"]
    allow_saas = rules["allow_saas"]
    max_risk_val = _RISK_ORDER.get(rules["max_risk"], 0)

    allowed: List[Dict] = []
    blocked: List[Dict] = []

    for skill in SKILL_CATALOG:
        # Check internet gate
        if skill.get("requires_internet") and not allow_internet:
            blocked.append(skill)
            continue

        # Check SaaS gate
        if skill.get("requires_saas") and not allow_saas:
            blocked.append(skill)
            continue

        # Check risk gate
        skill_risk = _RISK_ORDER.get(skill.get("risk_level"), 0)
        if skill_risk > max_risk_val:
            blocked.append(skill)
            continue

        allowed.append(skill)

    return (
        sorted(allowed, key=lambda s: s["id"]),
        sorted(blocked, key=lambda s: s["id"]),
    )


def get_catalog_stats() -> Dict:
    """
    Return summary statistics for the catalog.

    Returns:
        Dict with counts by category, source, risk level, and phase.
    """
    by_category: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    by_risk: Dict[str, int] = {}
    by_phase: Dict[int, int] = {}
    internet_count = 0
    saas_count = 0

    for skill in SKILL_CATALOG:
        cat = skill.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

        src = skill.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

        risk = skill.get("risk_level") or "None"
        by_risk[risk] = by_risk.get(risk, 0) + 1

        for phase in skill.get("sdlc_phases", []):
            by_phase[phase] = by_phase.get(phase, 0) + 1

        if skill.get("requires_internet"):
            internet_count += 1
        if skill.get("requires_saas"):
            saas_count += 1

    return {
        "total_skills": len(SKILL_CATALOG),
        "by_category": dict(sorted(by_category.items())),
        "by_source": dict(sorted(by_source.items())),
        "by_risk_level": dict(sorted(by_risk.items())),
        "by_phase": dict(sorted(by_phase.items())),
        "requires_internet": internet_count,
        "requires_saas": saas_count,
    }


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def _cli() -> None:
    """CLI entry point: output catalog data as JSON."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Atomic Claude skill catalog — query and export skill metadata."
    )
    parser.add_argument(
        "--id", type=str, default=None,
        help="Return a single skill by id"
    )
    parser.add_argument(
        "--phase", type=int, default=None,
        help="Return skills for a given SDLC phase (0-9)"
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Return skills in a given category"
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Return skills from a given source"
    )
    parser.add_argument(
        "--profile", type=str, default=None,
        help="Split catalog by profile: air-gapped, sensitive, standard, unrestricted"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print catalog summary statistics"
    )
    parser.add_argument(
        "--ids-only", action="store_true",
        help="Output only skill ids (newline-separated) instead of full JSON"
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Output compact JSON (no indentation)"
    )

    args = parser.parse_args()
    indent = None if args.compact else 2

    # Exactly one query mode
    modes = [args.id, args.phase, args.category, args.source, args.profile, args.stats]
    active = sum(1 for m in modes if m is not None and m is not False)

    if active > 1:
        parser.error("Specify at most one of --id, --phase, --category, --source, --profile, --stats")

    if args.id:
        skill = get_skill(args.id)
        if skill is None:
            print(f"Skill not found: {args.id}", file=sys.stderr)
            sys.exit(1)
        if args.ids_only:
            print(skill["id"])
        else:
            print(json.dumps(skill, indent=indent))

    elif args.phase is not None:
        skills = get_skills_for_phase(args.phase)
        if args.ids_only:
            for s in skills:
                print(s["id"])
        else:
            print(json.dumps(skills, indent=indent))

    elif args.category:
        skills = get_skills_by_category(args.category)
        if args.ids_only:
            for s in skills:
                print(s["id"])
        else:
            print(json.dumps(skills, indent=indent))

    elif args.source:
        skills = get_skills_by_source(args.source)
        if args.ids_only:
            for s in skills:
                print(s["id"])
        else:
            print(json.dumps(skills, indent=indent))

    elif args.profile:
        try:
            allowed, blocked = get_skills_by_profile(args.profile)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        if args.ids_only:
            print("# allowed")
            for s in allowed:
                print(s["id"])
            print("# blocked")
            for s in blocked:
                print(s["id"])
        else:
            print(json.dumps({"allowed": allowed, "blocked": blocked}, indent=indent))

    elif args.stats:
        print(json.dumps(get_catalog_stats(), indent=indent))

    else:
        # Default: full catalog
        if args.ids_only:
            for s in SKILL_CATALOG:
                print(s["id"])
        else:
            print(json.dumps(SKILL_CATALOG, indent=indent))


if __name__ == "__main__":
    _cli()
