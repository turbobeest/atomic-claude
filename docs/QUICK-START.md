# ATOMIC CLAUDE Quick Start

Documentation-first setup. Configure everything up front, then run Phase 0.

## Prerequisites

- Git repository
- API credentials (AWS Bedrock, Anthropic API, or Ollama)

## Setup Steps

### 1. Create .env File (Required)

**Location:** `.env` must be in the same directory as `main.sh`

Copy the template and fill in your credentials:

```bash
# If using the orchestrator directly
cp .env.template .env

# If you have ATOMIC-CLAUDE as a subdirectory
cp ATOMIC-CLAUDE/.env.template ATOMIC-CLAUDE/.env
```

Edit `.env` with your credentials:

**Option 1: AWS Profile (Recommended for Corporate/SSO)**
```bash
# For corporate/government with rotating credentials
AWS_PROFILE=bedrock-dev
AWS_REGION=us-gov-west-1
CLAUDE_CODE_USE_BEDROCK=1
ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'
```

**Before running pipeline, authenticate:**
```bash
aws sso login --profile bedrock-dev
# Or for assumed roles:
# aws sts assume-role --role-arn ... --profile bedrock-dev
```

**Option 2: Static Credentials (Personal/Development)**
```bash
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-gov-west-1
CLAUDE_CODE_USE_BEDROCK=1
ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'
```

**Option 3: Anthropic API**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Option 4: Ollama (Local, Free)**
```bash
# No .env needed - just run: ollama serve
```

**Security:** `.env` is gitignored by default. Never commit credentials.

### 2. Configure LLM Preferences

Edit `initialization/llm-preferences.md`:

1. **Uncomment your providers** (remove `#`):
   ```markdown
   aws-bedrock        # AWS Bedrock (active)
   # anthropic        # Anthropic API
   ollama             # Local Ollama (active)
   ```

2. **Rearrange models by preference** (top = first choice):
   ```markdown
   us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0   # Primary
   # claude-opus-4-5-20251101                         # Fallback
   ```

3. **Configure task routing**:
   - Critical tasks → Cloud API (highest quality)
   - Bulk tasks → Ollama (cost-free)
   - Quick tasks → Fast models

### 3. Customize setup.md

Edit `initialization/setup.md`:

- **Project Info**: Name, description, type
- **Repository**: Git strategy, commit format
- **Sandbox**: Network mode, security settings
- **Pipeline**: Phases to run, human gates
- **Constraints**: Tech stack, compliance

Use special values:
- `infer` - Let Claude extract from your docs
- `default` - Use recommended settings
- `detect` - Auto-detect from environment

### 4. Run Phase 0

```bash
./main.sh run 0
```

Task 001 will validate:
- ✓ `.env` file exists with credentials
- ✓ `setup.md` is customized
- ✓ `llm-preferences.md` is configured
- ✓ At least one provider is available

Then Phase 0 continues automatically through:
- Task 002: Config extraction
- Task 003: Config review
- Task 004: Credential loading (auto-detects from .env)
- Task 005-009: Environment setup

## E2E Testing

For automated testing:

```bash
# Create .env in ATOMIC-CLAUDE directory (same location as main.sh)
cd /path/to/test-project
cat > ATOMIC-CLAUDE/.env << 'EOF'
AWS_PROFILE=bedrock-dev
AWS_REGION=us-gov-west-1
CLAUDE_CODE_USE_BEDROCK=1
ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'
EOF

# Authenticate with AWS SSO
aws sso login --profile bedrock-dev

# Run E2E test
./ATOMIC-CLAUDE/test/test-e2e-phase0.sh
```

## Troubleshooting

### "No .env file found"

**Solution:** Create `.env` file in project root with credentials (see Step 1)

### "No API credentials found"

**Solution:**
1. Check `.env` file has correct variable names (AWS_ACCESS_KEY_ID, etc.)
2. Or configure AWS CLI: `aws configure`
3. Or ensure Ollama is running: `curl http://localhost:11434/api/tags`

### "Bedrock unavailable, falling back to Ollama"

**Solution:** AWS credentials not loaded
1. Verify `.env` has AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
2. Restart Phase 0: `./main.sh run 0`

### "Setup file not customized"

**Solution:** Edit `initialization/setup.md` and replace `infer` values with project details

### "Profile not authenticated" (AWS SSO)

**Solution:** Temporary credentials expired
```bash
# Re-authenticate with SSO
aws sso login --profile bedrock-dev

# Verify authentication
aws sts get-caller-identity --profile bedrock-dev

# Then continue pipeline
./main.sh run 0
```

### "ExpiredToken" or "InvalidClientTokenId" (AWS)

**Solution:** AWS credentials expired (common with SSO/assumed roles)
1. Re-authenticate: `aws sso login --profile bedrock-dev`
2. Or refresh assumed role credentials
3. Restart the failed phase

## Advanced

### Multiple Environments

Use different .env files:

```bash
# Development
ln -sf .env.dev .env

# Production
ln -sf .env.prod .env
```

### AWS Profiles

Specify AWS profile in .env:

```bash
AWS_PROFILE=my-profile
AWS_REGION=us-gov-west-1
```

### Offline Mode

Use only Ollama (no API calls):

1. In `llm-preferences.md`:
   ```markdown
   ollama             # Only provider
   Offline Mode: true
   ```

2. No .env file needed
3. Ensure Ollama running: `ollama serve`

## Next Steps

After Phase 0 completes:

```bash
# Run Phase 1 (Discovery)
./main.sh run 1

# Or run all phases
./main.sh run all
```

## Documentation

- **LLM Configuration**: `docs/LLM-PREFERENCES-GUIDE.md`
- **Setup Reference**: `initialization/setup.md` (inline docs)
- **API Credentials**: `.env.template` (template with comments)
