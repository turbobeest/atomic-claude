#!/usr/bin/env bash
# Test script for document-guardian agent
# Tests guardian validation and context injection without running full PRD generation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load atomic libraries
source "$PROJECT_ROOT/lib/atomic.sh"
source "$PROJECT_ROOT/lib/provider.sh"

# Test configuration
TEST_OUTPUT_DIR="$PROJECT_ROOT/.outputs/test-guardian"
mkdir -p "$TEST_OUTPUT_DIR"

echo "=== Document Guardian Test Suite ==="
echo ""

# Test 1: Simple drift detection (tech stack change)
test_tech_stack_drift() {
    echo "Test 1: Tech stack drift detection"

    # Create mock Section 2 (defines tech stack)
    cat > "$TEST_OUTPUT_DIR/section-2.md" << 'EOF'
## 2. Technical Architecture

### 2.1 Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend | Node.js/Express | Event-driven, npm ecosystem |
| Frontend | React | Component-based UI |
| Database | PostgreSQL | ACID compliance, relational |
EOF

    # Create mock Section 3 (violates tech stack)
    cat > "$TEST_OUTPUT_DIR/section-3.md" << 'EOF'
## 3. Feature Requirements

#### FR-001: User Authentication

The system **SHALL** authenticate users via MySQL database...
EOF

    # Prepare guardian prompt
    cat > "$TEST_OUTPUT_DIR/guardian-prompt.md" << EOF
You are the document-guardian. Validate the completed section for drift.

# Completed Section
$(cat "$TEST_OUTPUT_DIR/section-3.md")

# Prior Sections
$(cat "$TEST_OUTPUT_DIR/section-2.md")

# Project Context
Tech stack: Node.js, React, PostgreSQL

# Validation Task
Check for tech stack drift, ID sequence issues, and cross-reference problems.

Output JSON format:
{
  "validation": {
    "status": "pass|warn|fail",
    "drift_detected": true|false,
    "issues": [...]
  },
  "context_injection": {
    "reminders": [...],
    "constraints": [...],
    "watch_for": [...]
  }
}
EOF

    # Invoke guardian with Ollama
    echo "  Invoking guardian with $test_model..."
    if ! atomic_invoke \
        "$TEST_OUTPUT_DIR/guardian-prompt.md" \
        "$TEST_OUTPUT_DIR/guardian-report-test1.json" \
        "Test 1: Tech stack drift" \
        --provider=ollama \
        --model="$test_model" \
        --format=json \
        --timeout=60; then
        echo "  ❌ FAILED: Guardian invocation failed"
        return 1
    fi

    # Validate output
    if [[ ! -f "$TEST_OUTPUT_DIR/guardian-report-test1.json" ]]; then
        echo "  ❌ FAILED: No output file generated"
        return 1
    fi

    # Extract JSON from markdown fences if present
    if grep -q '```json' "$TEST_OUTPUT_DIR/guardian-report-test1.json"; then
        sed -n '/```json/,/```/p' "$TEST_OUTPUT_DIR/guardian-report-test1.json" | sed '1d;$d' > "$TEST_OUTPUT_DIR/guardian-report-test1-clean.json"
        mv "$TEST_OUTPUT_DIR/guardian-report-test1-clean.json" "$TEST_OUTPUT_DIR/guardian-report-test1.json"
    fi

    # Check if drift was detected
    if jq -e '.validation.drift_detected == true' "$TEST_OUTPUT_DIR/guardian-report-test1.json" > /dev/null; then
        echo "  ✅ PASSED: Drift detected correctly (MySQL vs PostgreSQL)"
    else
        echo "  ❌ FAILED: Drift not detected"
        jq . "$TEST_OUTPUT_DIR/guardian-report-test1.json"
        return 1
    fi

    echo ""
}

# Test 2: ID sequence validation (gap detection)
test_id_sequence_gap() {
    echo "Test 2: ID sequence gap detection"

    cat > "$TEST_OUTPUT_DIR/section-3-gaps.md" << 'EOF'
## 3. Feature Requirements

#### FR-001: User Registration
The system **SHALL** allow users to register...

#### FR-002: User Login
The system **SHALL** authenticate users...

#### FR-005: Password Reset
The system **SHALL** provide password reset...
EOF

    cat > "$TEST_OUTPUT_DIR/guardian-prompt-test2.md" << EOF
You are the document-guardian. Validate ID sequences.

# Completed Section
$(cat "$TEST_OUTPUT_DIR/section-3-gaps.md")

# Validation Task
Check for ID sequence gaps (FR-001, FR-002, then FR-005 - missing FR-003, FR-004).

Output JSON with drift_detected: true if gaps found.
EOF

    echo "  Invoking guardian..."
    if ! atomic_invoke \
        "$TEST_OUTPUT_DIR/guardian-prompt-test2.md" \
        "$TEST_OUTPUT_DIR/guardian-report-test2.json" \
        "Test 2: ID gaps" \
        --provider=ollama \
        --model="$test_model" \
        --format=json \
        --timeout=60; then
        echo "  ❌ FAILED: Guardian invocation failed"
        return 1
    fi

    # Extract JSON from markdown fences if present
    if grep -q '```json' "$TEST_OUTPUT_DIR/guardian-report-test2.json"; then
        sed -n '/```json/,/```/p' "$TEST_OUTPUT_DIR/guardian-report-test2.json" | sed '1d;$d' > "$TEST_OUTPUT_DIR/guardian-report-test2-clean.json"
        mv "$TEST_OUTPUT_DIR/guardian-report-test2-clean.json" "$TEST_OUTPUT_DIR/guardian-report-test2.json"
    fi

    # Check for drift detection (flexible - either .validation.drift_detected or .drift_detected)
    if jq -e '.validation.drift_detected == true or .drift_detected == true' "$TEST_OUTPUT_DIR/guardian-report-test2.json" > /dev/null 2>&1; then
        echo "  ✅ PASSED: ID gap detected (FR-003, FR-004 missing)"
    else
        echo "  ❌ FAILED: ID gap not detected"
        jq . "$TEST_OUTPUT_DIR/guardian-report-test2.json"
        return 1
    fi

    echo ""
}

# Test 3: Cross-reference validation
test_cross_reference() {
    echo "Test 3: Cross-reference validation (broken reference)"

    cat > "$TEST_OUTPUT_DIR/section-3-xref.md" << 'EOF'
## 3. Feature Requirements

#### FR-001: Shopping Cart
The system **SHALL** maintain shopping cart state...

#### FR-002: Checkout
The system **SHALL** process checkout transactions...
EOF

    cat > "$TEST_OUTPUT_DIR/section-5-xref.md" << 'EOF'
## 5. Logical Dependency Chain

### Foundation Layer
1. FR-007: Payment Gateway (depends on external service)

### Core Layer
2. FR-001: Shopping Cart (depends on FR-007)
3. FR-002: Checkout (depends on FR-001, FR-007)
EOF

    cat > "$TEST_OUTPUT_DIR/guardian-prompt-test3.md" << EOF
You are the document-guardian. Validate cross-references.

# Completed Section
$(cat "$TEST_OUTPUT_DIR/section-5-xref.md")

# Prior Sections
$(cat "$TEST_OUTPUT_DIR/section-3-xref.md")

# Validation Task
Section 5 references FR-007 but it was never defined in Section 3.
This should be flagged as drift.

Output JSON with drift_detected: true if broken reference found.
EOF

    echo "  Invoking guardian..."
    if ! atomic_invoke \
        "$TEST_OUTPUT_DIR/guardian-prompt-test3.md" \
        "$TEST_OUTPUT_DIR/guardian-report-test3.json" \
        "Test 3: Broken xref" \
        --provider=ollama \
        --model="$test_model" \
        --format=json \
        --timeout=60; then
        echo "  ❌ FAILED: Guardian invocation failed"
        return 1
    fi

    # Extract JSON from markdown fences if present
    if grep -q '```json' "$TEST_OUTPUT_DIR/guardian-report-test3.json"; then
        sed -n '/```json/,/```/p' "$TEST_OUTPUT_DIR/guardian-report-test3.json" | sed '1d;$d' > "$TEST_OUTPUT_DIR/guardian-report-test3-clean.json"
        mv "$TEST_OUTPUT_DIR/guardian-report-test3-clean.json" "$TEST_OUTPUT_DIR/guardian-report-test3.json"
    fi

    # Check for drift detection (flexible structure)
    if jq -e '.validation.drift_detected == true or .drift_detected == true' "$TEST_OUTPUT_DIR/guardian-report-test3.json" > /dev/null 2>&1; then
        echo "  ✅ PASSED: Broken cross-reference detected (FR-007 undefined)"
    else
        echo "  ❌ FAILED: Broken reference not detected"
        jq . "$TEST_OUTPUT_DIR/guardian-report-test3.json"
        return 1
    fi

    echo ""
}

# Test 4: Context injection quality
test_context_injection() {
    echo "Test 4: Context injection payload"

    cat > "$TEST_OUTPUT_DIR/section-3-complete.md" << 'EOF'
## 3. Feature Requirements

#### FR-001: User Registration
The system **SHALL** allow users to register with email and password...

#### FR-002: Product Catalog
The system **SHALL** display products with PostgreSQL backend...
EOF

    cat > "$TEST_OUTPUT_DIR/guardian-prompt-test4.md" << EOF
You are the document-guardian. Generate context injection for Section 4.

# Completed Section
$(cat "$TEST_OUTPUT_DIR/section-3-complete.md")

# Next Section
Section 4: Non-Functional Requirements

# Task
Generate context_injection payload with:
- reminders: Tech stack (PostgreSQL), FR IDs defined (FR-001, FR-002)
- constraints: NFR IDs start at NFR-001
- watch_for: Common pitfalls

Output JSON.
EOF

    echo "  Invoking guardian..."
    if ! atomic_invoke \
        "$TEST_OUTPUT_DIR/guardian-prompt-test4.md" \
        "$TEST_OUTPUT_DIR/guardian-report-test4.json" \
        "Test 4: Context injection" \
        --provider=ollama \
        --model="$test_model" \
        --format=json \
        --timeout=60; then
        echo "  ❌ FAILED: Guardian invocation failed"
        return 1
    fi

    # Extract JSON from markdown fences if present
    if grep -q '```json' "$TEST_OUTPUT_DIR/guardian-report-test4.json"; then
        sed -n '/```json/,/```/p' "$TEST_OUTPUT_DIR/guardian-report-test4.json" | sed '1d;$d' > "$TEST_OUTPUT_DIR/guardian-report-test4-clean.json"
        mv "$TEST_OUTPUT_DIR/guardian-report-test4-clean.json" "$TEST_OUTPUT_DIR/guardian-report-test4.json"
    fi

    # Check if context_injection exists and has content
    if jq -e '.context_injection.reminders | length > 0' "$TEST_OUTPUT_DIR/guardian-report-test4.json" > /dev/null; then
        echo "  ✅ PASSED: Context injection payload generated"
        echo "  Sample reminders:"
        jq -r '.context_injection.reminders[]' "$TEST_OUTPUT_DIR/guardian-report-test4.json" | head -3 | sed 's/^/    /'
    else
        echo "  ❌ FAILED: No context injection payload"
        jq . "$TEST_OUTPUT_DIR/guardian-report-test4.json"
        return 1
    fi

    echo ""
}

# Run all tests
main() {
    local failed=0

    # Check if Ollama is available
    if ! command -v ollama &> /dev/null; then
        echo "❌ Ollama not found. Install with: brew install ollama"
        exit 1
    fi

    # Use devstral for testing (already available, good instruction-following)
    local test_model="devstral:latest"
    if ! ollama list | grep -q "devstral"; then
        echo "⚠️  devstral not found. Using nemotron_mini_4b instead..."
        test_model="nemotron_mini_4b:latest"
    fi

    echo "Using model: $test_model for guardian tests"
    echo ""

    test_tech_stack_drift || ((failed++))
    test_id_sequence_gap || ((failed++))
    test_cross_reference || ((failed++))
    test_context_injection || ((failed++))

    echo "=== Test Summary ==="
    if [[ $failed -eq 0 ]]; then
        echo "✅ All tests passed (4/4)"
        echo ""
        echo "Guardian is ready for integration into Task 205."
        return 0
    else
        echo "❌ $failed test(s) failed"
        echo ""
        echo "Review logs in: $TEST_OUTPUT_DIR"
        return 1
    fi
}

main "$@"
