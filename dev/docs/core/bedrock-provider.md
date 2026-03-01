# AWS Bedrock Provider

The Bedrock provider implements the `BaseLLMProvider` interface for accessing Claude models via AWS Bedrock.

## Overview

**Module:** `core/llm/bedrock.py`
**Class:** `BedrockProvider`
**Provider Name:** `aws-bedrock`

## Features

- Claude models via AWS Bedrock
- Request/response format translation (AWS ↔ Anthropic)
- Regional endpoint support
- IAM authentication (AWS credentials)
- Streaming support
- Automatic retry with exponential backoff
- Model availability checking

## Installation

```bash
pip install boto3
```

## Configuration

### Environment Variables

```bash
# AWS credentials (boto3 will also check ~/.aws/credentials)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"

# Or use AWS profile
export AWS_PROFILE="your-profile"
```

### Config Dictionary

```python
config = {
    "aws_region": "us-east-1",                     # AWS region
    "aws_access_key_id": "your-key",               # Optional
    "aws_secret_access_key": "your-secret",        # Optional
    "aws_profile": "your-profile",                 # Optional
    "default_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "timeout": 300,                                # Request timeout
    "max_retries": 3,                              # Max retry attempts
}

provider = BedrockProvider(config=config)
```

## Supported Models

### Bedrock Claude Models

- `anthropic.claude-3-opus-20240229-v1:0` - Most capable
- `anthropic.claude-3-5-sonnet-20241022-v2:0` - Latest Sonnet (default)
- `anthropic.claude-3-5-sonnet-20240620-v1:0` - Previous Sonnet
- `anthropic.claude-3-sonnet-20240229-v1:0` - Original Claude 3 Sonnet
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast, lowest cost
- `anthropic.claude-v2:1` - Claude 2 (legacy)
- `anthropic.claude-v2` - Claude 2 (legacy)

### Tier Names (Abstract)

You can use tier names instead of full model IDs:

- `opus` → `anthropic.claude-3-opus-20240229-v1:0`
- `sonnet` → `anthropic.claude-3-5-sonnet-20241022-v2:0`
- `haiku` → `anthropic.claude-3-haiku-20240307-v1:0`

### Regional Availability

Not all models are available in all regions. Check Bedrock console for your region.

**Common regions:**
- `us-east-1` - Most models available
- `us-west-2` - Most models available
- `eu-west-1` - Limited availability
- `ap-southeast-1` - Limited availability

## Usage Examples

### Basic Invocation

```python
from core.llm.bedrock import BedrockProvider

provider = BedrockProvider(config={
    "aws_region": "us-east-1"
})

response = provider.invoke(
    prompt="Explain quantum computing in simple terms.",
    system_prompt="You are a helpful science teacher.",
    model="sonnet",
    max_tokens=500,
    temperature=0.7
)

print(response.content)
print(f"Used {response.usage.total_tokens} tokens")
```

### With AWS Profile

```python
provider = BedrockProvider(config={
    "aws_profile": "production",
    "aws_region": "us-west-2"
})

response = provider.invoke(prompt="Test")
```

### Streaming

```python
provider = BedrockProvider()

stream = provider.stream(
    prompt="Write a haiku about programming.",
    model="haiku",
    max_tokens=100
)

for chunk in stream:
    print(chunk, end="", flush=True)
```

### Model Validation

```python
provider = BedrockProvider()

# Check if model is supported
if provider.validate_model("opus"):
    print("Opus is supported")

# Get supported models
models = provider.get_supported_models()
print(f"Available models: {len(models)}")
```

### Token Counting

```python
provider = BedrockProvider()

text = "This is a test prompt for token counting."
token_count = provider.get_token_count(text)

print(f"Estimated tokens: {token_count}")
# Note: Bedrock doesn't provide a token counting API,
# so this uses approximation (4 chars per token)
```

### Health Check

```python
provider = BedrockProvider()

status = provider.health_check()

if status == HealthStatus.HEALTHY:
    print("Bedrock is healthy")
elif status == HealthStatus.DEGRADED:
    print("Bedrock is degraded")
else:
    print("Bedrock is unavailable")
```

## Error Handling

The provider maps AWS/boto3 exceptions to standard LLM errors:

### AuthenticationError

```python
try:
    response = provider.invoke(prompt="Test")
except AuthenticationError as e:
    print(f"AWS access denied: {e}")
    # Check IAM permissions for Bedrock
```

### RateLimitError (Throttling)

```python
try:
    response = provider.invoke(prompt="Test")
except RateLimitError as e:
    print(f"AWS throttling: {e}")
    # Provider will automatically retry with exponential backoff
```

### TimeoutError

```python
try:
    response = provider.invoke(prompt="Test", timeout=10)
except TimeoutError as e:
    print(f"Request timed out: {e}")
```

### APIError

```python
try:
    response = provider.invoke(prompt="Test")
except APIError as e:
    print(f"Bedrock error: {e}")
    print(f"Error code: {e.error_code}")
    print(f"Retryable: {e.retryable}")
```

### ModelNotFoundError

```python
try:
    response = provider.invoke(prompt="Test", model="invalid-model")
except ModelNotFoundError as e:
    print(f"Model not found: {e}")
    # Check model is available in your region
```

## IAM Permissions

Your AWS IAM role/user needs these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude*"
        }
    ]
}
```

## Response Format

The `LLMResponse` object contains:

```python
response = provider.invoke(prompt="Test")

# Content
print(response.content)  # Generated text

# Model info
print(response.model)     # "anthropic.claude-3-5-sonnet-20241022-v2:0"
print(response.provider)  # "aws-bedrock"

# Usage statistics
print(response.usage.input_tokens)   # Input token count
print(response.usage.output_tokens)  # Output token count
print(response.usage.total_tokens)   # Total tokens

# Metadata
print(response.finish_reason)  # "end_turn", "max_tokens", etc.
print(response.latency_ms)     # Request latency in milliseconds
print(response.timestamp)      # Response timestamp
print(response.metadata)       # Additional metadata (id, type, role)
```

## Advanced Configuration

### Custom Timeout

```python
# Per-request timeout
response = provider.invoke(
    prompt="Long analysis task...",
    timeout=600  # 10 minutes
)
```

### Custom Retry Behavior

```python
config = {
    "max_retries": 5,  # More retries for throttling
}

provider = BedrockProvider(config=config)
```

### Multiple Regions

```python
# Create providers for different regions
us_provider = BedrockProvider(config={"aws_region": "us-east-1"})
eu_provider = BedrockProvider(config={"aws_region": "eu-west-1"})

# Use based on data residency requirements
response = us_provider.invoke(prompt="Test")
```

### Additional API Parameters

```python
# Pass any additional Bedrock API parameters
response = provider.invoke(
    prompt="Test",
    top_p=0.9,
    top_k=50,
    stop_sequences=["END"],
)
```

## Performance Considerations

### Latency

- Typical invoke latency: 1-5 seconds (depends on model and region)
- Streaming first token: < 1 second
- Error handling overhead: < 10ms
- Regional latency: Choose region closest to your application

### Token Limits

| Model | Max Input Tokens | Max Output Tokens |
|-------|-----------------|-------------------|
| Opus  | 200,000         | 4,096             |
| Sonnet| 200,000         | 4,096             |
| Haiku | 200,000         | 4,096             |

### Cost Optimization

1. Use `haiku` for simple tasks (lowest cost)
2. Use `sonnet` for balanced performance (default)
3. Use `opus` only for complex reasoning
4. Set appropriate `max_tokens` to avoid waste
5. Monitor Bedrock costs in AWS Cost Explorer
6. Use On-Demand pricing vs Provisioned Throughput based on usage patterns

## Bedrock vs Direct Anthropic API

### Advantages of Bedrock

- **IAM Integration:** Use AWS IAM roles and policies
- **VPC Support:** Run within AWS VPC for security
- **CloudWatch Integration:** Automatic logging and metrics
- **Enterprise Features:** AWS support contracts apply
- **Compliance:** May help with regulatory requirements (HIPAA, etc.)
- **Single Bill:** Combined with other AWS services

### Disadvantages of Bedrock

- **Regional Limitations:** Not all models in all regions
- **Latency:** Slight additional latency vs direct API
- **Version Lag:** New models may arrive later than direct API
- **No Prompt Caching:** Bedrock doesn't support prompt caching
- **Cost:** Bedrock pricing may differ from direct API

## Testing

### Unit Tests

```bash
# Run Bedrock provider unit tests
pytest tests/unit/test_bedrock_provider.py -v
```

### Integration Tests

```bash
# Run with real Bedrock (requires AWS credentials)
RUN_LLM_TESTS=1 pytest tests/integration/test_providers_integration.py::TestBedrockIntegration -v
```

### Mocking for Tests

```python
from unittest.mock import Mock, patch
import json

with patch("core.llm.bedrock.boto3.Session") as mock_session_class:
    mock_session = Mock()
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    mock_session_class.return_value = mock_session

    # Mock response
    mock_response_body = {
        "content": [{"type": "text", "text": "Test response"}],
        "usage": {"input_tokens": 10, "output_tokens": 20},
        "stop_reason": "end_turn"
    }
    mock_response = {"body": Mock()}
    mock_response["body"].read.return_value = json.dumps(mock_response_body).encode()
    mock_client.invoke_model.return_value = mock_response

    # Test your code
    provider = BedrockProvider()
    response = provider.invoke(prompt="Test")
```

## Troubleshooting

### Access Denied

```
AuthenticationError: AWS Bedrock access denied
```

**Solution:**
1. Check IAM permissions (see IAM Permissions section)
2. Verify AWS credentials are configured
3. Check Bedrock is enabled in your AWS account
4. Verify model is available in your region

### Model Not Ready

```
ModelNotFoundError: AWS Bedrock model not ready
```

**Solution:**
1. Check model availability in Bedrock console
2. Request access to model in AWS console
3. Verify region supports the model
4. Wait for model to be provisioned (can take a few minutes)

### Throttling

```
RateLimitError: AWS Bedrock throttling
```

**Solution:**
1. Increase `max_retries` in config (automatic backoff)
2. Request quota increase in AWS Service Quotas
3. Consider Provisioned Throughput for high volume
4. Implement client-side rate limiting

### Connection Issues

```
APIError: AWS Bedrock connection error
```

**Solution:**
1. Check network connectivity to AWS
2. Verify security group / VPC settings
3. Check AWS service status page
4. Try different region if available

### Invalid Region

```
APIError: Could not connect to the endpoint URL
```

**Solution:**
1. Verify region is correct (e.g., "us-east-1" not "us-east-1a")
2. Check Bedrock is available in that region
3. Use `aws bedrock list-foundation-models` to verify

## Reference

- **AWS Bedrock Docs:** https://docs.aws.amazon.com/bedrock/
- **Boto3 Docs:** https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **Base Implementation:** `/Users/jamesterbeest/dev/atomic-claude/lib/provider.sh` lines 200-600

## See Also

- [Base Provider Interface](base-provider.md)
- [Anthropic Provider](anthropic-provider.md)
- [Provider Router](provider-router.md)
