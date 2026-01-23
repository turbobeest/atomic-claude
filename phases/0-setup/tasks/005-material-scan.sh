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

    # Scan for key files first
    _005_detect_key_files "$manifest_file"

    # Infer project type
    _005_infer_project_type "$manifest_file" "$config_file"

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
        echo -e "    ${DIM}(none detected - greenfield project?)${NC}"
    fi

    # Update manifest
    local tmp=$(mktemp)
    printf '%s\n' "${key_files[@]}" | jq -R . | jq -s '.' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .key_files = input' - > "$tmp" && mv "$tmp" "$manifest_file"

    echo ""
}

# Infer project type from key files
_005_infer_project_type() {
    local manifest_file="$1"
    local config_file="$2"
    local indicators=()
    local inferred_type="unknown"
    local inferred_lang="unknown"

    # Detect language/framework
    if [[ -f "package.json" ]]; then
        inferred_lang="javascript"
        if [[ -f "tsconfig.json" ]]; then
            inferred_lang="typescript"
        fi
        # Check for frameworks
        if grep -q '"next"' package.json 2>/dev/null; then
            indicators+=("next.js")
            inferred_type="web-app"
        elif grep -q '"react"' package.json 2>/dev/null; then
            indicators+=("react")
            inferred_type="web-app"
        elif grep -q '"vue"' package.json 2>/dev/null; then
            indicators+=("vue")
            inferred_type="web-app"
        elif grep -q '"express"' package.json 2>/dev/null; then
            indicators+=("express")
            inferred_type="api"
        fi
    fi

    if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]]; then
        inferred_lang="python"
        if [[ -f "manage.py" ]]; then
            indicators+=("django")
            inferred_type="web-app"
        elif grep -q 'flask' requirements.txt 2>/dev/null || grep -q 'flask' pyproject.toml 2>/dev/null; then
            indicators+=("flask")
            inferred_type="api"
        elif grep -q 'fastapi' requirements.txt 2>/dev/null || grep -q 'fastapi' pyproject.toml 2>/dev/null; then
            indicators+=("fastapi")
            inferred_type="api"
        fi
    fi

    if [[ -f "Cargo.toml" ]]; then
        inferred_lang="rust"
        inferred_type="cli"
    fi

    if [[ -f "go.mod" ]]; then
        inferred_lang="go"
        inferred_type="cli"
    fi

    if [[ -f "Gemfile" ]]; then
        inferred_lang="ruby"
        if grep -q 'rails' Gemfile 2>/dev/null; then
            indicators+=("rails")
            inferred_type="web-app"
        fi
    fi

    # Update config with inferred type if not already set
    local current_type=$(jq -r '.project.type // "unknown"' "$config_file" 2>/dev/null)
    if [[ "$current_type" == "unknown" || "$current_type" == "null" ]]; then
        local tmp=$(mktemp)
        jq ".project.type = \"$inferred_type\" | .project.language = \"$inferred_lang\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
    fi

    # Update manifest
    local tmp=$(mktemp)
    jq --arg lang "$inferred_lang" --arg type "$inferred_type" \
        '.inferred = { "language": $lang, "type": $type }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    if [[ ${#indicators[@]} -gt 0 ]]; then
        echo -e "  ${CYAN}Project Type${NC}"
        echo -e "    Language:  ${BOLD}$inferred_lang${NC}"
        echo -e "    Type:      ${BOLD}$inferred_type${NC}"
        echo -e "    Framework: ${DIM}${indicators[*]}${NC}"
        echo ""

        local tmp=$(mktemp)
        printf '%s\n' "${indicators[@]}" | jq -R . | jq -s '.' | \
            jq --slurpfile m "$manifest_file" '$m[0] | .project_indicators = input' - > "$tmp" && mv "$tmp" "$manifest_file"
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
    local tmp=$(mktemp)
    jq --argjson count "$count" --argjson loc "$loc" \
        '.summary.documentation = { "count": $count, "lines": $loc }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(mktemp)
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
    local tmp=$(mktemp)
    jq --argjson count "$count" '.summary.configuration = { "count": $count }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(mktemp)
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
    echo ""

    # Update manifest
    local tmp=$(mktemp)
    jq --argjson count "$count" --argjson loc "$loc" \
        '.summary.source_code = { "count": $count, "lines": $loc }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(mktemp)
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
    local tmp=$(mktemp)
    jq --argjson count "$count" '.summary.tests = { "count": $count }' "$manifest_file" > "$tmp" && mv "$tmp" "$manifest_file"

    local tmp=$(mktemp)
    echo "$tests" | jq -R 'select(length > 0)' | jq -s '.' | \
        jq --slurpfile m "$manifest_file" '$m[0] | .files.tests = input' - > "$tmp" && mv "$tmp" "$manifest_file"
}

# Calculate totals
_005_calculate_totals() {
    local manifest_file="$1"

    local total_files=$(jq '[.summary.documentation.count, .summary.configuration.count, .summary.source_code.count, .summary.tests.count] | add // 0' "$manifest_file")
    local total_loc=$(jq '[.summary.documentation.lines, .summary.source_code.lines] | add // 0' "$manifest_file")

    local tmp=$(mktemp)
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
    local inferred_lang=$(jq -r '.inferred.language // "unknown"' "$manifest_file")
    local inferred_type=$(jq -r '.inferred.type // "unknown"' "$manifest_file")
    local key_count=$(jq '.key_files | length' "$manifest_file")

    # Build context message
    local context_msg="Material scan: $total_files files"
    [[ "$inferred_lang" != "unknown" ]] && context_msg+=", $inferred_lang"
    [[ "$inferred_type" != "unknown" ]] && context_msg+=" $inferred_type"
    context_msg+=", $key_count key files"

    atomic_context_decision "$context_msg" "discovery"

    # Register manifest as artifact
    atomic_context_artifact "material-manifest" "$manifest_file" "Project file inventory"
}
