#!/bin/bash
#
# Task 005: Material Scan
# Index existing project files (docs, configs, source code)
#
# Features:
#   - Comprehensive file type detection
#   - Key file identification (README, package.json, etc.)
#   - Project type/framework inference
#   - Sample file display per category
#   - Size and LOC awareness
#   - Records findings to context
#

task_005_material_scan() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local manifest_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/material-manifest.json"

    atomic_step "Material Scan"

    echo ""
    echo -e "${DIM}  Scanning project for existing materials...${NC}"
    echo ""

    # Initialize manifest
    cat > "$manifest_file" << EOF
{
  "scanned_at": "$(date -Iseconds)",
  "summary": {},
  "key_files": [],
  "project_indicators": [],
  "files": {}
}
EOF

    # Scan for key files first (pattern-matching known filenames, no LLM)
    _005_detect_key_files "$manifest_file"

    # Detect language/frameworks from key files (no type inference - left to Discovery)
    _005_detect_stack "$manifest_file"

    # Scan different categories
    _005_scan_documentation "$manifest_file"
    _005_scan_configuration "$manifest_file"
    _005_scan_source_code "$manifest_file"
    _005_scan_tests "$manifest_file"

    # Calculate totals
    _005_calculate_totals "$manifest_file"

    # Display summary
    _005_display_summary "$manifest_file"

    # Record to context
    _005_record_context "$manifest_file"

    atomic_success "Material manifest created"
    return 0
}

# Detect key project files
_005_detect_key_files() {
    local manifest_file="$1"
    local key_files=()

    echo -e "  ${CYAN}Key Files${NC}"

    # Documentation
    [[ -f "README.md" ]] && key_files+=("README.md") && echo -e "    ${GREEN}✓${NC} README.md"
    [[ -f "README" ]] && key_files+=("README") && echo -e "    ${GREEN}✓${NC} README"
    [[ -f "CHANGELOG.md" ]] && key_files+=("CHANGELOG.md") && echo -e "    ${GREEN}✓${NC} CHANGELOG.md"
    [[ -f "LICENSE" ]] && key_files+=("LICENSE") && echo -e "    ${GREEN}✓${NC} LICENSE"
    [[ -f "CONTRIBUTING.md" ]] && key_files+=("CONTRIBUTING.md") && echo -e "    ${GREEN}✓${NC} CONTRIBUTING.md"

    # Node.js / JavaScript
    [[ -f "package.json" ]] && key_files+=("package.json") && echo -e "    ${GREEN}✓${NC} package.json"
    [[ -f "tsconfig.json" ]] && key_files+=("tsconfig.json") && echo -e "    ${GREEN}✓${NC} tsconfig.json"
    [[ -f "vite.config.ts" ]] && key_files+=("vite.config.ts") && echo -e "    ${GREEN}✓${NC} vite.config.ts"
    [[ -f "next.config.js" ]] && key_files+=("next.config.js") && echo -e "    ${GREEN}✓${NC} next.config.js"

    # Python
    [[ -f "pyproject.toml" ]] && key_files+=("pyproject.toml") && echo -e "    ${GREEN}✓${NC} pyproject.toml"
    [[ -f "setup.py" ]] && key_files+=("setup.py") && echo -e "    ${GREEN}✓${NC} setup.py"
    [[ -f "requirements.txt" ]] && key_files+=("requirements.txt") && echo -e "    ${GREEN}✓${NC} requirements.txt"
    [[ -f "Pipfile" ]] && key_files+=("Pipfile") && echo -e "    ${GREEN}✓${NC} Pipfile"

    # Rust
    [[ -f "Cargo.toml" ]] && key_files+=("Cargo.toml") && echo -e "    ${GREEN}✓${NC} Cargo.toml"

    # Go
    [[ -f "go.mod" ]] && key_files+=("go.mod") && echo -e "    ${GREEN}✓${NC} go.mod"

    # Ruby
    [[ -f "Gemfile" ]] && key_files+=("Gemfile") && echo -e "    ${GREEN}✓${NC} Gemfile"

    # Java / Kotlin
    [[ -f "pom.xml" ]] && key_files+=("pom.xml") && echo -e "    ${GREEN}✓${NC} pom.xml"
    [[ -f "build.gradle" ]] && key_files+=("build.gradle") && echo -e "    ${GREEN}✓${NC} build.gradle"

    # Docker
    [[ -f "Dockerfile" ]] && key_files+=("Dockerfile") && echo -e "    ${GREEN}✓${NC} Dockerfile"
    [[ -f "docker-compose.yml" ]] && key_files+=("docker-compose.yml") && echo -e "    ${GREEN}✓${NC} docker-compose.yml"

    # CI/CD
    [[ -f ".github/workflows" ]] && key_files+=(".github/workflows") && echo -e "    ${GREEN}✓${NC} .github/workflows"
    [[ -f ".gitlab-ci.yml" ]] && key_files+=(".gitlab-ci.yml") && echo -e "    ${GREEN}✓${NC} .gitlab-ci.yml"

    # Makefile
    [[ -f "Makefile" ]] && key_files+=("Makefile") && echo -e "    ${GREEN}✓${NC} Makefile"

    if [[ ${#key_files[@]} -eq 0 ]]; then
        echo -e "    ${DIM}Greenfield project detected - no standard project files found.${NC}"
    fi

    # Update manifest
    local tmp=$(atomic_mktemp)
    printf '%s\n' "${key_files[@]}" | jq -R . | jq -s '.' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .key_files = input' - > "$tmp" && mv "$tmp" "$manifest_file"

    echo ""
}

# Detect language/frameworks from key files (no type inference - left to Discovery phase)
_005_detect_stack() {
    local manifest_file="$1"
    local languages=()
    local frameworks=()

    # Detect languages and frameworks by pattern matching known files
    if [[ -f "package.json" ]]; then
        if [[ -f "tsconfig.json" ]]; then
            languages+=("TypeScript")
        else
            languages+=("JavaScript")
        fi
        # Check for frameworks
        grep -q '"next"' package.json 2>/dev/null && frameworks+=("Next.js")
        grep -q '"react"' package.json 2>/dev/null && frameworks+=("React")
        grep -q '"vue"' package.json 2>/dev/null && frameworks+=("Vue")
        grep -q '"svelte"' package.json 2>/dev/null && frameworks+=("Svelte")
        grep -q '"express"' package.json 2>/dev/null && frameworks+=("Express")
        grep -q '"fastify"' package.json 2>/dev/null && frameworks+=("Fastify")
    fi

    if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]]; then
        languages+=("Python")
        [[ -f "manage.py" ]] && frameworks+=("Django")
        grep -qi 'flask' requirements.txt pyproject.toml 2>/dev/null && frameworks+=("Flask")
        grep -qi 'fastapi' requirements.txt pyproject.toml 2>/dev/null && frameworks+=("FastAPI")
    fi

    [[ -f "Cargo.toml" ]] && languages+=("Rust")
    [[ -f "go.mod" ]] && languages+=("Go")
    [[ -f "Gemfile" ]] && languages+=("Ruby") && grep -q 'rails' Gemfile 2>/dev/null && frameworks+=("Rails")
    [[ -f "pom.xml" ]] && languages+=("Java")
    [[ -f "build.gradle" ]] && languages+=("Java/Kotlin")

    # Update manifest with detected stack (not inferred type)
    local tmp=$(atomic_mktemp)
    local lang_json=$(printf '%s\n' "${languages[@]}" | jq -R . | jq -s '.' 2>/dev/null || echo '[]')
    local fw_json=$(printf '%s\n' "${frameworks[@]}" | jq -R . | jq -s '.' 2>/dev/null || echo '[]')
    jq --argjson langs "$lang_json" --argjson fws "$fw_json" \
        '.detected_stack = { "languages": $langs, "frameworks": $fws }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    # Display if anything detected
    if [[ ${#languages[@]} -gt 0 ]] || [[ ${#frameworks[@]} -gt 0 ]]; then
        echo -e "  ${CYAN}Detected Stack${NC}"
        [[ ${#languages[@]} -gt 0 ]] && echo -e "    Languages:  ${DIM}${languages[*]}${NC}"
        [[ ${#frameworks[@]} -gt 0 ]] && echo -e "    Frameworks: ${DIM}${frameworks[*]}${NC}"
        echo ""
    fi
}

# Scan documentation files
_005_scan_documentation() {
    local manifest_file="$1"

    local docs=$(find . -maxdepth 4 \( \
        -name "*.md" -o -name "*.rst" -o -name "*.txt" -o \
        -name "*.adoc" -o -name "*.org" \
    \) -type f 2>/dev/null | grep -v node_modules | grep -v .git | grep -v .outputs | grep -v __pycache__ | sort | head -50 || true)

    local count=$(echo "$docs" | grep -c . 2>/dev/null || echo 0)
    local sample=$(echo "$docs" | head -5)
    local loc=0

    if [[ $count -gt 0 ]]; then
        loc=$(echo "$docs" | head -20 | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    fi

    echo -e "  ${CYAN}Documentation${NC}  ${DIM}$count files${NC}"
    if [[ $count -gt 0 ]]; then
        echo "$sample" | while read -r f; do
            [[ -n "$f" ]] && echo -e "    ${DIM}$f${NC}"
        done
        [[ $count -gt 5 ]] && echo -e "    ${DIM}... and $((count - 5)) more${NC}"
    fi
    echo ""

    # Update manifest
    local tmp=$(atomic_mktemp)
    jq --argjson count "$count" --argjson loc "$loc" \
        '.summary.documentation = { "count": $count, "lines": $loc }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(atomic_mktemp)
    echo "$docs" | jq -R 'select(length > 0)' | jq -s '.' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .files.documentation = input' - > "$tmp" && mv "$tmp" "$manifest_file"
}

# Scan configuration files
_005_scan_configuration() {
    local manifest_file="$1"

    local configs=$(find . -maxdepth 3 \( \
        -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o \
        -name "*.toml" -o -name "*.ini" -o -name "*.env*" -o \
        -name ".*.rc" -o -name "*.config.js" -o -name "*.config.ts" \
    \) -type f 2>/dev/null | grep -v node_modules | grep -v .git | grep -v package-lock | grep -v yarn.lock | sort | head -30 || true)

    local count=$(echo "$configs" | grep -c . 2>/dev/null || echo 0)
    local sample=$(echo "$configs" | head -5)

    echo -e "  ${CYAN}Configuration${NC}  ${DIM}$count files${NC}"
    if [[ $count -gt 0 ]]; then
        echo "$sample" | while read -r f; do
            [[ -n "$f" ]] && echo -e "    ${DIM}$f${NC}"
        done
        [[ $count -gt 5 ]] && echo -e "    ${DIM}... and $((count - 5)) more${NC}"
    fi
    echo ""

    # Update manifest
    local tmp=$(atomic_mktemp)
    jq --argjson count "$count" '.summary.configuration = { "count": $count }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(atomic_mktemp)
    echo "$configs" | jq -R 'select(length > 0)' | jq -s '.' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .files.configuration = input' - > "$tmp" && mv "$tmp" "$manifest_file"
}

# Scan source code files
_005_scan_source_code() {
    local manifest_file="$1"

    local code=$(find . -maxdepth 5 \( \
        -name "*.py" -o -name "*.js" -o -name "*.ts" -o \
        -name "*.jsx" -o -name "*.tsx" -o -name "*.vue" -o \
        -name "*.go" -o -name "*.rs" -o -name "*.rb" -o \
        -name "*.java" -o -name "*.kt" -o -name "*.scala" -o \
        -name "*.c" -o -name "*.cpp" -o -name "*.h" -o \
        -name "*.php" -o -name "*.swift" -o -name "*.sh" -o \
        -name "*.sql" -o -name "*.graphql" \
    \) -type f 2>/dev/null | grep -v node_modules | grep -v .git | grep -v __pycache__ | grep -v dist | grep -v build | grep -v -E '\.min\.' | sort | head -100 || true)

    local count=$(echo "$code" | grep -c . 2>/dev/null || echo 0)
    local sample=$(echo "$code" | head -5)
    local loc=0

    if [[ $count -gt 0 ]]; then
        loc=$(echo "$code" | head -50 | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
    fi

    echo -e "  ${CYAN}Source Code${NC}    ${DIM}$count files (~$loc lines)${NC}"
    if [[ $count -gt 0 ]]; then
        echo "$sample" | while read -r f; do
            [[ -n "$f" ]] && echo -e "    ${DIM}$f${NC}"
        done
        [[ $count -gt 5 ]] && echo -e "    ${DIM}... and $((count - 5)) more${NC}"
    fi

    # Warn if file count is high - suggest external codebase strategy
    if [[ $count -gt 100 ]]; then
        echo ""
        echo -e "    ${YELLOW}Note:${NC} Large codebase detected ($count files)."
        echo -e "    ${DIM}Consider connecting to external codebases during development${NC}"
        echo -e "    ${DIM}rather than embedding all reference material upfront.${NC}"
    fi
    echo ""

    # Update manifest
    local tmp=$(atomic_mktemp)
    jq --argjson count "$count" --argjson loc "$loc" \
        '.summary.source_code = { "count": $count, "lines": $loc }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(atomic_mktemp)
    echo "$code" | jq -R 'select(length > 0)' | jq -s '.[0:50]' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .files.source_code = input' - > "$tmp" && mv "$tmp" "$manifest_file"
}

# Scan test files
_005_scan_tests() {
    local manifest_file="$1"

    local tests=$(find . -maxdepth 5 \( \
        -name "*_test.py" -o -name "test_*.py" -o \
        -name "*.test.js" -o -name "*.spec.js" -o \
        -name "*.test.ts" -o -name "*.spec.ts" -o \
        -name "*_test.go" -o -name "*_test.rs" \
    \) -type f 2>/dev/null | grep -v node_modules | grep -v .git | sort | head -30 || true)

    # Also check for test directories
    local test_dirs=$(find . -maxdepth 3 -type d \( -name "test" -o -name "tests" -o -name "__tests__" -o -name "spec" \) 2>/dev/null | grep -v node_modules | head -5 || true)

    local count=$(echo "$tests" | grep -c . 2>/dev/null || echo 0)
    local sample=$(echo "$tests" | head -3)

    echo -e "  ${CYAN}Tests${NC}          ${DIM}$count files${NC}"
    if [[ $count -gt 0 ]]; then
        echo "$sample" | while read -r f; do
            [[ -n "$f" ]] && echo -e "    ${DIM}$f${NC}"
        done
        [[ $count -gt 3 ]] && echo -e "    ${DIM}... and $((count - 3)) more${NC}"
    elif [[ -n "$test_dirs" ]]; then
        echo -e "    ${DIM}Test directories found: $(echo "$test_dirs" | tr '\n' ' ')${NC}"
    fi
    echo ""

    # Update manifest
    local tmp=$(atomic_mktemp)
    jq --argjson count "$count" '.summary.tests = { "count": $count }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(atomic_mktemp)
    echo "$tests" | jq -R 'select(length > 0)' | jq -s '.' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .files.tests = input' - > "$tmp" && mv "$tmp" "$manifest_file"
}

# Calculate totals
_005_calculate_totals() {
    local manifest_file="$1"

    local total_files=$(jq '[.summary.documentation.count, .summary.configuration.count, .summary.source_code.count, .summary.tests.count] | add // 0' "$manifest_file")
    local total_loc=$(jq '[.summary.documentation.lines, .summary.source_code.lines] | add // 0' "$manifest_file")

    local tmp=$(atomic_mktemp)
    jq --argjson files "$total_files" --argjson loc "$total_loc" \
        '.summary.total = { "files": $files, "lines": $loc }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"
}

# Display summary
_005_display_summary() {
    local manifest_file="$1"

    local total_files=$(jq '.summary.total.files // 0' "$manifest_file")
    local total_loc=$(jq '.summary.total.lines // 0' "$manifest_file")
    local key_count=$(jq '.key_files | length' "$manifest_file")

    echo -e "  ${DIM}────────────────────────────────────${NC}"
    echo -e "  ${BOLD}Total:${NC} $total_files files, ~$total_loc lines"
    echo -e "  ${BOLD}Key files:${NC} $key_count identified"
    echo ""
}

# Record findings to context
_005_record_context() {
    local manifest_file="$1"

    local total_files=$(jq '.summary.total.files // 0' "$manifest_file")
    local key_count=$(jq '.key_files | length' "$manifest_file")
    local languages=$(jq -r '.detected_stack.languages // [] | join(", ")' "$manifest_file")

    # Build context message
    local context_msg="Material scan: $total_files files, $key_count key files"
    [[ -n "$languages" ]] && context_msg+=", stack: $languages"

    atomic_context_decision "$context_msg" "discovery"

    # Register manifest as artifact
    atomic_context_artifact "material-manifest" "$manifest_file" "Project file inventory"
}
