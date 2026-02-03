# LLM Preferences Configuration

Configure model providers, routing, and fallback behavior for ATOMIC CLAUDE.

## Quick Start

1. **Uncomment your available providers** (remove `#`)
2. **Rearrange models by preference** (top = first choice)
3. **Configure task routing** (which models for which tasks)

---

# PRIMARY PROVIDER CHAIN

First available provider wins. Rearrange to set priority.

```
# claude-code      # Claude Code subscription (if active)
# anthropic        # Anthropic API (ANTHROPIC_API_KEY required)
aws-bedrock        # AWS Bedrock (AWS credentials required)
# openai           # OpenAI API (OPENAI_API_KEY required)
# google           # Google Gemini (GOOGLE_API_KEY required)
# azure            # Azure OpenAI (AZURE_OPENAI_API_KEY required)
# openrouter       # OpenRouter (OPENROUTER_API_KEY required)
ollama             # Local Ollama (free, localhost:11434)
```

## API Credentials (.env file)

**IMPORTANT:** API keys and credentials are NOT stored in this file for security.

### Required: Create .env File

**Location:** `.env` (in project root, same directory as `main.sh`)

**Template:**
```bash
# ===== AWS Bedrock - OPTION 1: Profile-based (Corporate/SSO) =====
# RECOMMENDED for corporate/government with rotating credentials
AWS_PROFILE=bedrock-dev
AWS_REGION=us-gov-west-1
CLAUDE_CODE_USE_BEDROCK=1
ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'

# Before running: aws sso login --profile bedrock-dev

# ===== AWS Bedrock - OPTION 2: Static Keys (Personal) =====
# AWS_ACCESS_KEY_ID=your-access-key-here
# AWS_SECRET_ACCESS_KEY=your-secret-key-here
# AWS_REGION=us-gov-west-1
# CLAUDE_CODE_USE_BEDROCK=1
# ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'

# ===== Anthropic API =====
# ANTHROPIC_API_KEY=sk-ant-...

# ===== OpenAI =====
# OPENAI_API_KEY=sk-...

# ===== Google Gemini =====
# GOOGLE_API_KEY=...
```

**AWS SSO Workflow (Corporate/Government):**
```bash
# 1. Create .env with AWS_PROFILE
# 2. Authenticate before each session:
aws sso login --profile bedrock-dev

# 3. Verify authentication:
aws sts get-caller-identity --profile bedrock-dev

# 4. Run pipeline:
./main.sh run 0

# Note: SSO credentials expire (typically 8-12 hours)
# Re-authenticate when you see ExpiredToken errors
```

**Security:**
- `.env` file is automatically gitignored
- Never commit credentials to version control
- Store `.env` file securely

### Task 001 Validation

Task 001 (Setup Validation) checks for .env file and validates credentials before proceeding:
- ✓ Checks for .env file
- ✓ Validates AWS credentials (or AWS CLI config)
- ✓ Validates Anthropic API key
- ✓ Detects Ollama availability
- ✗ Fails if no providers are available

### Alternative: AWS CLI Configuration

Instead of .env, you can use AWS CLI configuration:
```bash
# Interactive setup
aws configure

# Or SSO
aws sso login --profile <profile>
```

Task 001 will detect `~/.aws/credentials` and accept it instead of .env.

### For E2E Testing

Create .env file in test-project directory before running:
```bash
cd /path/to/test-project
cat > .env << 'EOF'
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-gov-west-1
EOF

# Then run test
./ATOMIC-CLAUDE/test/test-e2e-phase0.sh
```

---

# MODEL PREFERENCES

## Cloud Models (Anthropic/Bedrock)

Uncomment your available models and rearrange by preference (top = first choice).

### Claude Series

```
us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0   # Bedrock USG Sonnet 4.5
# claude-opus-4-5-20251101                         # API - Opus 4.5
# claude-sonnet-4-5-20250929                       # API - Sonnet 4.5
# claude-haiku-4-5-20251101                        # API - Haiku 4.5
# us-gov.anthropic.claude-haiku-4-5-20251101-v1:0  # Bedrock USG Haiku 4.5
us-gov.anthropic.claude-3-haiku-20240307-v1:0      # Bedrock USG Haiku 3.0
```

### Notes on Bedrock Model IDs

- **US Gov Region:** `us-gov.anthropic.claude-*` - For government/classified environments
- **Standard Regions:** `anthropic.claude-*` - For commercial AWS accounts
- **Version Suffix:** `:0` or `:1` indicates Bedrock API version (use `:0` for latest)
- **Availability:** Not all models available in all regions - check AWS Bedrock console

### Other Provider Models

```
# ===== OpenAI =====
# gpt-4-turbo                                         # GPT-4 Turbo
# gpt-4o                                              # GPT-4 Omni

# ===== Google Gemini =====
# gemini-2.0-flash-exp                                # Gemini 2.0 Flash
```

## Local Models (Ollama)
## SEEK GUIDANCE USING LOCAL LLMS AHEAD OF WORKING ON ENTERPRISE/GOVT CODE 

Enable Ollama for cost-free bulk tasks:

```
OLLAMA_ENABLED: true
```

### Code-Specialized Models

Uncomment and rearrange by preference (top = first choice):

## SEEK GUIDANCE USING LOCAL LLMS AHEAD OF WORKING ON ENTERPRISE/GOVT CODE 

```
# Large Context - Architecture & Analysis
devstral:latest                    # 131K context - Mistral code specialist
granite-code:latest                # 128K context - IBM flagship
# qwen2.5-coder:32b                # 128K context - Alibaba code model

# Medium Context - General Coding
codestral:latest                   # 32K context - Mistral specialized 22B
phind-codellama:latest             # 16K context - Fine-tuned 34B
codellama:latest                   # 16K context - Meta flagship 7B
wizardcoder:latest                 # 16K context - Instruction-tuned 7B
starcoder2:latest                  # 16K context - Bigcode 3B
stable-code:latest                 # 16K context - StabilityAI 3B

# Compact - Fast Operations
codegemma:latest                   # 8K context - Google small code 9B
# deepseek-coder-v2:16b            # 16K context - DeepSeek 16B
```

### General Purpose Models
## SEEK GUIDANCE USING LOCAL LLMS AHEAD OF WORKING ON ENTERPRISE/GOVT CODE 

```
# Large Context - Complex Reasoning
# llama3.3:70b                     # 128K context - Meta flagship
llama3.2:3b                        # 128K context - Meta small
# llama3.2-vision:11b              # 128K context - Vision + text
gemma3:4b                          # 8K context - Google compact
gemma3:12b                         # 8K context - Google mid-size

# Specialized
nemotron_mini_4b:latest            # 4K context - NVIDIA 4.2B GP
# nemotron-3-nano:30b              # 4K context - NVIDIA 30B GP
# mistral:7b                       # 32K context - General purpose
# phi3:medium                      # 128K context - Microsoft 14B
```

---

# OLLAMA SERVERS
## SEEK GUIDANCE USING LOCAL LLMS AHEAD OF WORKING ON ENTERPRISE/GOVT CODE 

Configure Ollama instances (local or network):

Format: `name | host:port | model | max_context | description`

```
# Local Instance
local | localhost:11434 | devstral:latest | 131072 | Primary local server

# Remote Instances (optional)
# desktop | 192.168.1.100:11434 | qwen2.5-coder:32b | 128000 | RTX 5090 desktop
# server | 10.0.0.50:11434 | codellama:34b | 16384 | Lab server
```

**Failover:** `true`  # Try next server if primary unavailable
**Health Check:** `true`  # Verify connectivity before task assignment

---

# TASK ROUTING

Route different task types to different providers for cost optimization.

## Critical Tasks
**Provider:** `primary`
**Tasks:** PRD authoring, architecture decisions, human gates, approvals
**Recommended:** Cloud API models (highest quality)

```
# primary      # Use primary provider chain
# ollama       # Use local models (cost-free)
```

## Bulk Tasks
**Provider:** `ollama`
**Tasks:** Audit execution, code scanning, deep analysis (high token volume)
**Recommended:** Local models (unlimited usage)

```
primary      # Use primary provider chain
# ollama     # Use local models (recommended for cost savings)
```

## Quick Tasks
**Provider:** `primary`
**Tasks:** Validations, simple checks, status updates
**Recommended:** Fast models (Haiku, small local models)

```
# primary      # Use primary provider chain
# ollama       # Use local models
```

### Background Model Override
## SEEK GUIDANCE USING LOCAL LLMS AHEAD OF WORKING ON ENTERPRISE/GOVT CODE 
Use a smaller/faster model for background tasks:

```
# local | localhost:11434 | starcoder2:latest | 16384        # Bigcode 3B
# local | localhost:11434 | stable-code:latest | 16384       # StabilityAI 3B
# local | localhost:11434 | codegemma:latest | 8192          # Google 9B
# local | localhost:11434 | nemotron_mini_4b:latest | 4096   # NVIDIA 4.2B
# local | localhost:11434 | llama3.2:3b | 128000             # Meta 3B
# local | localhost:11434 | gemma3:4b | 8192                 # Google 4B
```

---

# PROVIDER CHAIN OVERRIDES

Override the global provider chain for specific task types.

## Global Chain (Default)
```
claude-code aws-bedrock anthropic ollama
```

## Critical Tasks Chain (Optional)
Leave blank to use global chain.
```
# aws-bedrock anthropic
```

## Bulk Tasks Chain (Optional)
Leave blank to use global chain.
```
# ollama aws-bedrock
```

## Quick Tasks Chain (Optional)
Leave blank to use global chain.
```
# claude-code aws-bedrock
```

---

# FALLBACK BEHAVIOR

## API → Ollama Fallback
If primary API fails (rate limit, outage), fall back to Ollama?

```
true         # Recommended if Ollama enabled
# false
```

## Ollama → API Fallback
If all Ollama servers fail, fall back to API?

```
true         # Recommended for reliability
# false
```

## Offline Mode
Force offline-only operation (no API calls)?

```
# true       # Air-gapped/offline only
false        # Normal operation
```

---

# CONTEXT GARDENER

Intelligent context compression during long conversations.

## Gardener Model
## SEEK GUIDANCE USING LOCAL LLMS AHEAD OF WORKING ON ENTERPRISE/GOVT CODE 
Which model handles context adjudication/compression?

```
infer                              # Auto-select fastest (RECOMMENDED)
# claude-haiku-4-5-20251101        # API Haiku
# mistral:7b                       # Local Mistral
# phi3:medium                      # Local Phi3
```

## Threshold Percent
Trigger adjudication at this % of context window:

```
75           # Default (recommended range: 70-80)
```

## Fallback Chain
Models to try if primary gardener fails:

```
#claude-haiku-4-5-20251101, 
#mistral:7b, 
#phi3:medium, 
llama3.2:3b
```

## Preserve Recent Exchanges
Keep last N message pairs after compression:

```
4            # Default (recommended range: 2-6)
```

## Preserve Opening
Keep opening messages for continuity:

```
true         # Recommended
# false
```

---

# MODEL SELECTION CRITERIA

*Future feature: Agent-specific model preferences*

Agents can request models based on capabilities:

- **Priorities:** `[math, reasoning, code, quality, speed]`
- **Minimum Tier:** `low | medium | high`
- **Profiles:** `default | interactive | batch | budget`

Currently specified in agent definitions (`agents/*/AGENT.md`).

---

## Notes

- **Comment format:** Use `#` at start of line to disable
- **Order matters:** Top-to-bottom = first-to-last preference
- **No quotes needed:** Write values directly
- **Spaces OK:** Use spaces for readability

## Examples

**Cost-Optimized Setup:**
```
Primary: aws-bedrock
Critical: primary (cloud API)
Bulk: ollama (local models)
Quick: ollama (small local models)
```

**Quality-First Setup:**
```
Primary: claude-code anthropic aws-bedrock
Critical: primary
Bulk: primary
Quick: primary
```

**Offline-Only Setup:**
```
Primary: ollama
Critical: ollama
Bulk: ollama
Quick: ollama
Offline Mode: true
```
