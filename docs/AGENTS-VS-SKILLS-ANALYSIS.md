# Agents vs. Skills - Critical Gap Analysis

**Date:** February 10, 2026
**Question:** Can PhD-level agents morph into Claude Code skills without losing sophistication?
**Answer:** **NO** - but we can create a hybrid approach.

---

## TL;DR - The Problem

**Agent format** (atomic-claude) has **10x more sophistication** than **Skills format** (Claude Code).

Converting agents → skills would **lose**:
- Cognitive modes (generative, critical, evaluative, informative)
- Ensemble roles (solo, panel_member, auditor, input_provider, decision_maker)
- Model fallbacks across providers (Bedrock → DeepSeek → Qwen → Ollama)
- Tool modes (audit = read-only, solution = read/write, research = web access)
- Escalation logic (when to delegate to specialized agents)
- Proactive triggers (auto-invoke based on file patterns)
- Audit metadata (quality scores, dimension ratings)

**This is unacceptable for PhD-level work.**

---

## Side-by-Side Comparison

### Agent Format (atomic-claude)

```yaml
---
name: python-pro
description: Python specialist for backend services...
model: opus
model_fallbacks:
  - us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0  # Bedrock
  - DeepSeek-V3                                        # API
  - Qwen2.5-Coder-32B                                  # API
  - llama3.3:70b                                       # Ollama
  - gemma3:27b                                         # Ollama
model_selection:
  priorities: [code_generation, code_debugging, quality]
  minimum_tier: medium
  profiles:
    default: code_generation      # Use code-optimized model
    review: code_review            # Use quality-focused model
    batch: budget                  # Use cost-effective model
tier: expert

# Tool access varies by operational mode
tools:
  audit: Read, Grep, Glob, Bash              # Read-only for audits
  solution: Read, Write, Edit, Grep, Glob, Bash  # Full access for implementation
  research: Read, Grep, Glob, Bash, WebSearch, WebFetch  # Web access for research
  default_mode: solution

# Cognitive modes - HOW the agent thinks
cognitive_modes:
  generative:
    mindset: "Implement using Pythonic patterns, type safety, security-first"
    output: "Implementation with tests, type hints, security validation"
  critical:
    mindset: "Audit for security vulnerabilities, type inconsistencies, anti-patterns"
    output: "Violation report: security issues, type safety gaps, idiom violations"
  evaluative:
    mindset: "Weigh implementation approaches against performance and security"
    output: "Recommendation with security tradeoffs and performance impact"
  informative:
    mindset: "Provide Python expertise on ecosystem, patterns, and security"
    output: "Options with security implications and performance characteristics"
  default: generative

# Ensemble roles - HOW the agent behaves in context
ensemble_roles:
  solo:
    behavior: "Thorough security analysis, comprehensive type hints, explicit error handling"
  panel_member:
    behavior: "Strong positions on Pythonic idioms, advocate type safety and security"
  auditor:
    behavior: "Skeptical of dynamic features, verify input validation, check security"
  input_provider:
    behavior: "Present framework options, explain security tradeoffs, defer decisions"
  decision_maker:
    behavior: "Choose frameworks, approve security patterns, justify tradeoffs"
  default: solo

# Escalation - WHEN to delegate
escalation:
  confidence_threshold: 0.6
  escalate_to: "security-auditor or architecture-reviewer"
  triggers:
    - "Security vulnerability requires specialized assessment"
    - "Performance requirements conflict with Pythonic simplicity"
    - "Novel async patterns without established precedent"

# MCP servers needed by this agent
mcp_servers:
  github:
    description: "Repository exploration and code examples"
  pypi:
    description: "Package queries and version information"
  mypy:
    description: "Type checking and analysis"

# Auto-invoke when these patterns detected
proactive_triggers:
  - "*.py"
  - "*requirements*.txt"
  - "*pyproject.toml*"
  - "*async*"
  - "*security*"

# Quality tracking
audit:
  date: 2026-01-24
  composite_score: 91
  grade: A
  dimensions:
    structural_completeness: 100
    tier_alignment: 90
    instruction_quality: 92
    vocabulary_calibration: 90
    knowledge_authority: 92
    # ... 10 dimensions total
---
```

### Skills Format (Claude Code)

```yaml
---
name: python-pro
description: Expert Python developer specializing in backend services...
model: opus
tools:
  - Read
  - Write
  - Edit
  - Bash
context: fork
disable-model-invocation: false
---
```

**That's it.** Skills have 6 frontmatter fields. Agents have 15+ sophisticated structures.

---

## What's Lost in Conversion

### 1. Multi-Provider Model Fallbacks ❌

**Agent:**
```yaml
model: opus
model_fallbacks:
  - us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0  # Bedrock (primary)
  - DeepSeek-V3                                        # API (fallback 1)
  - Qwen2.5-Coder-32B                                  # API (fallback 2)
  - llama3.3:70b                                       # Ollama (fallback 3)
```

**Skill:**
```yaml
model: opus  # That's all you get
```

**Impact:** If Bedrock is down, skill can't fall back to DeepSeek or Ollama automatically.

**Your Question:** "Can skills include model priorities across token/API/bedrock/ollama?"
**Answer:** **NO.** Skills only support single model selection. No fallback chain, no provider routing.

---

### 2. Cognitive Modes ❌

**Agent:** Changes behavior based on task type
```yaml
cognitive_modes:
  generative: "Implement with security-first design"
  critical: "Audit for vulnerabilities"
  evaluative: "Weigh tradeoffs"
  informative: "Explain options without deciding"
```

**Usage:**
```bash
# Invoke in audit mode
atomic_invoke "$agent" "$output" --mode=critical
# Agent becomes skeptical, looks for problems

# Invoke in implementation mode
atomic_invoke "$agent" "$output" --mode=generative
# Agent builds solutions, optimizes for clarity
```

**Skill:** No concept of cognitive modes. Always behaves the same way.

**Impact:** Can't switch between "implement" vs "audit" vs "advise" modes. One behavior only.

---

### 3. Tool Modes ❌

**Agent:** Different tool access based on operation
```yaml
tools:
  audit: Read, Grep, Glob, Bash     # Read-only - can't modify code
  solution: Read, Write, Edit, Bash  # Full access - can implement
  research: Read, Bash, WebSearch    # Web access - can research
```

**Skill:** Single tool list, no modes
```yaml
tools:
  - Read
  - Write
  - Edit
  - Bash
```

**Impact:** Can't restrict tools based on operation type. Audit mode could accidentally modify code.

---

### 4. Ensemble Roles ❌

**Agent:** Changes behavior based on collaboration context
```yaml
ensemble_roles:
  solo: "Thorough, comprehensive, explain everything"
  panel_member: "Strong opinions, advocate for best practices"
  auditor: "Skeptical, verify claims, challenge assumptions"
  input_provider: "Present options, defer decisions"
  decision_maker: "Make call, justify choice, own outcome"
```

**Usage:**
```bash
# In panel discussion
atomic_invoke_panel \
  "python-pro:panel_member" \
  "security-auditor:panel_member" \
  "architect:decision_maker"

# Solo work
atomic_invoke "python-pro" --role=solo
```

**Skill:** No concept of roles. Always behaves the same in all contexts.

**Impact:** Can't adapt behavior to collaboration context. No panel discussions, no decision-making hierarchies.

---

### 5. Escalation Logic ❌

**Agent:** Knows when to delegate
```yaml
escalation:
  confidence_threshold: 0.6
  escalate_to: "security-auditor or architecture-reviewer"
  triggers:
    - "Security vulnerability requires specialized assessment"
    - "Novel async patterns without established precedent"
```

**Skill:** No escalation concept. If stuck, just reports uncertainty.

**Impact:** Can't automatically delegate to specialized agents. User must manually decide when to invoke different skill.

---

### 6. Model Selection Profiles ❌

**Agent:** Different models for different tasks
```yaml
model_selection:
  profiles:
    default: code_generation      # DeepSeek-V3 (optimized for code)
    review: code_review            # Opus (quality-focused)
    batch: budget                  # llama3.3:70b (cost-effective)
```

**Usage:**
```bash
# Use code-optimized model
atomic_invoke "$agent" --profile=default

# Use quality-focused model for review
atomic_invoke "$agent" --profile=review

# Use budget model for bulk operations
atomic_invoke "$agent" --profile=batch
```

**Skill:** Single model. Can't switch profiles.

**Impact:** Can't optimize model selection for task type. Waste expensive model on simple tasks, or use cheap model on critical tasks.

---

### 7. Proactive Triggers ❌

**Agent:** Auto-invokes based on patterns
```yaml
proactive_triggers:
  - "*.py"             # Invoke when Python files detected
  - "*async*"          # Invoke when async patterns seen
  - "*security*"       # Invoke when security mentioned
```

**Skill:** Claude Code's auto-discovery is based on description matching only, not file patterns.

**Impact:** Less precise auto-invocation. Might not trigger on file patterns, only on text descriptions.

---

### 8. Audit Metadata ❌

**Agent:** Tracks quality over time
```yaml
audit:
  date: 2026-01-24
  composite_score: 91
  grade: A
  dimensions:
    structural_completeness: 100
    instruction_quality: 92
    knowledge_authority: 92
    # 10 dimensions total
```

**Skill:** No audit tracking. No quality scores.

**Impact:** Can't track agent evolution, can't validate quality, can't identify degradation.

---

## What Skills Gain Over Agents

Despite the losses, skills DO provide some advantages:

### 1. Native Claude Code Integration ✅

**Skills:**
- Auto-discovery by Claude Code
- Slash command invocation (`/python-pro "task"`)
- Context forking (isolated subagent)
- Tool restriction enforcement

**Agents:**
- Manual invocation via bash
- No slash commands
- No context forking
- Tool restriction in bash only

---

### 2. Context Forking ✅

**Skills:**
```yaml
context: fork  # Run in isolated subagent
```

**Agents:** No concept of context isolation. All work in main session.

**Benefit:** Skills can run without polluting main conversation. Cleaner context management.

---

### 3. Simpler Format ✅

**Skills:** 10 lines of frontmatter

**Agents:** 100+ lines of frontmatter

**Benefit:** Easier to create, modify, understand (but less sophisticated)

---

## The Hybrid Solution

**Don't choose.** Use both.

### Proposed Structure

```
.claude/skills/
└── python-pro/
    ├── SKILL.md              # Claude Code native (simple)
    ├── agent.md              # Full agent definition (authoritative)
    ├── config.yaml           # Model priorities, tool modes, etc.
    ├── templates/
    │   ├── fastapi.py
    │   └── pytest.py
    └── examples/
        └── async-example.py
```

### How It Works

1. **SKILL.md** - Claude Code discovers and invokes
2. **agent.md** - Authoritative source with full sophistication
3. **config.yaml** - Model fallbacks, profiles, cognitive modes
4. **Wrapper in atomic.sh** - Reads agent.md, invokes with proper configuration

### Invocation Layer

```bash
# Enhanced atomic_invoke_skill function
atomic_invoke_skill() {
    local skill_name="$1"
    local task="$2"
    local output="$3"

    # Load agent.md for sophisticated configuration
    local agent_file=".claude/skills/$skill_name/agent.md"
    local config_file=".claude/skills/$skill_name/config.yaml"

    # Parse model fallbacks from agent.md
    local model_chain=$(parse_model_fallbacks "$agent_file")

    # Parse cognitive mode from task context
    local cognitive_mode=$(detect_cognitive_mode "$task")

    # Parse tool mode from cognitive mode
    local tool_mode=$(get_tool_mode "$agent_file" "$cognitive_mode")

    # Resolve best model with fallback chain
    local resolved_model=$(resolve_model_with_fallbacks "$model_chain")

    # Build prompt with cognitive mode context
    local enhanced_prompt=$(build_prompt_with_mode "$task" "$cognitive_mode" "$agent_file")

    # Invoke with full agent sophistication
    atomic_invoke "$enhanced_prompt" "$output" "$skill_name" \
        --model="$resolved_model" \
        --tools="$tool_mode"
}
```

### Example Usage

```bash
# User invokes via slash command
/python-pro "Implement async FastAPI endpoint"

# Claude Code loads SKILL.md (simple format)
# Our wrapper reads agent.md (sophisticated format)
# Wrapper:
#   - Detects "implement" → generative cognitive mode
#   - Generative mode → solution tool mode (Read, Write, Edit, Bash)
#   - Resolves model: opus → fallback to DeepSeek-V3 if unavailable
#   - Invokes with enhanced context

# Result: PhD-level agent sophistication + Claude Code native features
```

---

## Implementation Plan

### Phase 1: Archive Current Agents ✅

```bash
# Create archive
cd /Users/jamesterbeest/dev/atomic-claude2
cp -r agents agents.archive.$(date +%Y%m%d)
tar -czf agents-archive-$(date +%Y%m%d).tar.gz agents/

# Verify
ls -lh agents-archive-*.tar.gz
```

### Phase 2: Create Hybrid Structure

```bash
# For each agent, create skill directory
for agent in agents/expert-agents/**/**.md; do
    skill_name=$(basename "$agent" .md)
    mkdir -p ".claude/skills/$skill_name"

    # Copy agent as authoritative source
    cp "$agent" ".claude/skills/$skill_name/agent.md"

    # Generate SKILL.md (simplified for Claude Code)
    ./scripts/generate-skill-from-agent.sh "$agent" \
        > ".claude/skills/$skill_name/SKILL.md"

    # Extract config.yaml (model priorities, etc.)
    ./scripts/extract-agent-config.sh "$agent" \
        > ".claude/skills/$skill_name/config.yaml"
done
```

### Phase 3: Create Wrapper Functions

Add to `lib/atomic.sh`:

```bash
# Parse model fallbacks from agent.md
parse_model_fallbacks() {
    local agent_file="$1"
    # Extract model_fallbacks section
    # Return: "opus,DeepSeek-V3,llama3.3:70b"
}

# Detect cognitive mode from task description
detect_cognitive_mode() {
    local task="$1"
    if [[ "$task" =~ audit|review|check ]]; then
        echo "critical"
    elif [[ "$task" =~ implement|build|create ]]; then
        echo "generative"
    elif [[ "$task" =~ compare|evaluate|weigh ]]; then
        echo "evaluative"
    else
        echo "informative"
    fi
}

# Get tool mode for cognitive mode
get_tool_mode() {
    local agent_file="$1"
    local cognitive_mode="$2"
    # Parse tools section from agent.md
    # Return tool list for given mode
}

# Resolve model with fallback chain
resolve_model_with_fallbacks() {
    local model_chain="$1"
    # Try each model in order
    # Return first available
}

# Enhanced skill invocation
atomic_invoke_skill() {
    # (implementation from above)
}
```

### Phase 4: Test Hybrid Approach

```bash
# Test python-pro skill with agent sophistication
atomic_invoke_skill "python-pro" \
    "Implement async FastAPI endpoint with type hints" \
    "output.py"

# Verify:
# - Used generative cognitive mode
# - Used solution tool mode (Write enabled)
# - Tried opus → fell back to DeepSeek-V3
# - Output has type hints, async patterns, security validation
```

### Phase 5: Convert All 221 Agents

```bash
# Batch conversion script
./scripts/convert-all-agents-to-hybrid.sh

# Verify
ls -la .claude/skills/ | wc -l  # Should be 221+
```

---

## Comparison: Pure Skills vs Hybrid

| Capability | Pure Skills | Hybrid (Skills + Agents) |
|------------|-------------|--------------------------|
| **Claude Code Integration** | ✅ Native | ✅ Native (via SKILL.md) |
| **Slash Commands** | ✅ `/skill-name` | ✅ `/skill-name` |
| **Auto-Discovery** | ✅ Description-based | ✅ Description + file patterns |
| **Context Forking** | ✅ `context: fork` | ✅ `context: fork` |
| **Cognitive Modes** | ❌ None | ✅ generative, critical, evaluative, informative |
| **Ensemble Roles** | ❌ None | ✅ solo, panel_member, auditor, decision_maker |
| **Tool Modes** | ❌ Single list | ✅ audit, solution, research |
| **Model Fallbacks** | ❌ Single model | ✅ Bedrock → API → Ollama chain |
| **Model Profiles** | ❌ None | ✅ code_generation, code_review, batch |
| **Escalation Logic** | ❌ None | ✅ Confidence-based delegation |
| **Proactive Triggers** | ✅ Limited | ✅ File patterns + description |
| **Audit Metadata** | ❌ None | ✅ 10-dimension quality tracking |
| **MCP Server Specs** | ❌ Global only | ✅ Per-agent requirements |
| **PhD-Level Sophistication** | ❌ Basic | ✅ Full |

---

## Gaps That Emerge Without Formal Agents

If we used **pure skills** (no agent.md):

### 1. Loss of Multi-Provider Intelligence
- Can't automatically fall back from Bedrock → DeepSeek → Ollama
- Single point of failure
- Can't optimize model selection for task type

### 2. Loss of Behavioral Flexibility
- Agent acts the same in all contexts (implement, audit, advise)
- Can't adapt to collaboration (solo vs panel vs decision-maker)
- No role-based behavior

### 3. Loss of Quality Tracking
- No audit scores
- Can't measure agent degradation over time
- Can't validate improvements

### 4. Loss of Operational Intelligence
- Can't restrict tools based on operation (audit shouldn't write files)
- No escalation to specialized agents
- No confidence thresholds

### 5. Loss of Domain Knowledge Structure
- Agents embed authoritative knowledge sources in frontmatter
- Skills only have markdown references (not structured)
- Harder to validate knowledge authority

---

## Gaps That Emerge Without Skills

If we kept **pure agents** (no SKILL.md):

### 1. Loss of Native Claude Code Integration
- No auto-discovery
- No slash commands
- No context forking
- Manual bash invocation only

### 2. Loss of Tool Restriction Enforcement
- Tools restricted by bash logic only
- Not enforced by Claude Code
- Less secure

### 3. Loss of Context Isolation
- All work in main session
- Context pollution
- Harder to manage token limits

---

## Recommendation

**Use the hybrid approach:**

1. ✅ **Archive current agents** (backup)
2. ✅ **Keep agent.md as authoritative** (PhD-level sophistication)
3. ✅ **Generate SKILL.md from agent.md** (Claude Code integration)
4. ✅ **Create wrapper functions** (bridge agent sophistication → skill invocation)
5. ✅ **Extract config.yaml** (model priorities, tool modes, cognitive modes)

**Result:** Best of both worlds.
- Claude Code native features (auto-discovery, slash commands, context forking)
- Agent sophistication (cognitive modes, ensemble roles, model fallbacks, escalation)
- PhD-level quality maintained
- Multi-provider intelligence preserved

---

## Next Steps

1. **Archive agents:**
   ```bash
   cp -r agents agents.archive.$(date +%Y%m%d)
   tar -czf agents-archive-$(date +%Y%m%d).tar.gz agents/
   ```

2. **Create conversion scripts:**
   - `scripts/generate-skill-from-agent.sh` - Extract simplified SKILL.md
   - `scripts/extract-agent-config.sh` - Extract model priorities, tool modes
   - `scripts/convert-all-agents-to-hybrid.sh` - Batch conversion

3. **Implement wrapper functions in `lib/atomic.sh`:**
   - `atomic_invoke_skill()` - Enhanced invocation
   - `parse_model_fallbacks()` - Extract model chain
   - `detect_cognitive_mode()` - Infer mode from task
   - `resolve_model_with_fallbacks()` - Multi-provider routing

4. **Test with 5 pilot agents:**
   - python-pro (already started)
   - openapi-expert (already started)
   - security-auditor
   - test-automator
   - database-optimizer

5. **Validate hybrid approach:**
   - Does auto-discovery work?
   - Do cognitive modes engage correctly?
   - Do model fallbacks work?
   - Is PhD-level quality maintained?

6. **Full conversion (if pilot succeeds):**
   - Convert all 221 agents
   - Maintain agent.md as source of truth
   - Generate SKILL.md automatically
   - Update documentation

---

*Analysis completed February 10, 2026*
*Conclusion: Hybrid approach required to maintain PhD-level sophistication*
