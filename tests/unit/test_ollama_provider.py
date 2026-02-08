#!/usr/bin/env python3
"""
Unit Tests for Ollama LLM Provider

Tests all Ollama provider functionality with mocked HTTP calls.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import BytesIO

from core.llm.ollama import (
    OllamaProvider,
    ProviderUnavailableException,
)
from core.llm.base import (
    HealthStatus,
    TimeoutError,
    APIError,
    ModelNotFoundError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def ollama_provider():
    """Create an Ollama provider instance."""
    return OllamaProvider({
        "host": "http://localhost:11434",
        "default_model": "llama2",
        "timeout": 600,
        "auto_pull": False,  # Disable auto-pull for most tests
    })


@pytest.fixture
def mock_response_data():
    """Sample Ollama API response."""
    return {
        "model": "llama2",
        "response": "This is a test response from Ollama.",
        "done": True,
        "done_reason": "stop",
        "context": [1, 2, 3, 4, 5],
        "total_duration": 5000000000,
        "load_duration": 1000000000,
        "prompt_eval_count": 10,
        "eval_count": 8,
    }


@pytest.fixture
def mock_models_response():
    """Sample models list response."""
    return {
        "models": [
            {"name": "llama2", "size": 3825819519},
            {"name": "mistral", "size": 4109865159},
            {"name": "codellama", "size": 3825819519},
        ]
    }


# ============================================================================
# Test Initialization
# ============================================================================

def test_ollama_provider_init_default():
    """Test Ollama provider initialization with defaults."""
    provider = OllamaProvider()
    assert provider.provider_name == "ollama"
    assert provider.host == "http://localhost:11434"
    assert provider.default_model == "llama2"
    assert provider.default_timeout == 600


def test_ollama_provider_init_custom():
    """Test Ollama provider initialization with custom config."""
    config = {
        "host": "http://192.168.1.100:11434",
        "default_model": "mistral",
        "timeout": 900,
        "auto_pull": True,
    }
    provider = OllamaProvider(config)
    assert provider.host == "http://192.168.1.100:11434"
    assert provider.default_model == "mistral"
    assert provider.default_timeout == 900
    assert provider.auto_pull is True


def test_ollama_provider_strips_trailing_slash():
    """Test that trailing slash is removed from host URL."""
    provider = OllamaProvider({"host": "http://localhost:11434/"})
    assert provider.host == "http://localhost:11434"


# ============================================================================
# Test invoke()
# ============================================================================

def test_invoke_success(ollama_provider, mock_response_data):
    """Test successful invocation."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = ollama_provider.invoke("Test prompt")

        assert response.content == "This is a test response from Ollama."
        assert response.model == "llama2"
        assert response.provider == "ollama"
        assert response.usage.input_tokens > 0
        assert response.usage.output_tokens > 0
        assert response.finish_reason == "stop"
        assert response.latency_ms is not None


def test_invoke_with_system_prompt(ollama_provider, mock_response_data):
    """Test invocation with system prompt."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = ollama_provider.invoke(
            "User prompt",
            system_prompt="You are a helpful assistant"
        )

        # Verify the combined prompt was sent
        call_args = mock_urlopen.call_args
        request_data = json.loads(call_args[0][0].data.decode('utf-8'))
        assert "<system>You are a helpful assistant</system>" in request_data["prompt"]
        assert "User prompt" in request_data["prompt"]


def test_invoke_with_custom_model(ollama_provider, mock_response_data):
    """Test invocation with custom model."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = ollama_provider.invoke("Test", model="mistral")

        # Verify model parameter
        call_args = mock_urlopen.call_args
        request_data = json.loads(call_args[0][0].data.decode('utf-8'))
        assert request_data["model"] == "mistral"


def test_invoke_with_parameters(ollama_provider, mock_response_data):
    """Test invocation with temperature and max_tokens."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = ollama_provider.invoke(
            "Test",
            temperature=0.7,
            max_tokens=2048,
            num_ctx=4096,
            top_p=0.9,
        )

        # Verify parameters
        call_args = mock_urlopen.call_args
        request_data = json.loads(call_args[0][0].data.decode('utf-8'))
        assert request_data["options"]["temperature"] == 0.7
        assert request_data["options"]["num_predict"] == 2048
        assert request_data["options"]["num_ctx"] == 4096
        assert request_data["options"]["top_p"] == 0.9


def test_invoke_connection_refused(ollama_provider):
    """Test invocation when Ollama service is not running."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("Connection refused")

        with pytest.raises(APIError):
            ollama_provider.invoke("Test")


def test_invoke_timeout(ollama_provider):
    """Test invocation timeout."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = TimeoutError("Request timed out")

        with pytest.raises(TimeoutError):
            ollama_provider.invoke("Test", timeout=5)


def test_invoke_model_not_found(ollama_provider):
    """Test invocation with non-existent model."""
    error_response = {"error": "model 'nonexistent' not found"}

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(error_response).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(ModelNotFoundError):
            ollama_provider.invoke("Test", model="nonexistent")


def test_invoke_model_not_found_auto_pull(mock_response_data):
    """Test invocation with auto-pull enabled."""
    provider = OllamaProvider({"auto_pull": True})
    error_response = {"error": "model 'newmodel' not found"}

    with patch('urllib.request.urlopen') as mock_urlopen:
        # First call returns error, second call (after pull) succeeds
        mock_error = MagicMock()
        mock_error.read.return_value = json.dumps(error_response).encode('utf-8')

        mock_success = MagicMock()
        mock_success.read.return_value = json.dumps(mock_response_data).encode('utf-8')

        mock_urlopen.return_value.__enter__.side_effect = [mock_error, mock_success]

        with patch.object(provider, 'pull_model', return_value=True):
            response = provider.invoke("Test", model="newmodel")
            assert response.content == "This is a test response from Ollama."


# ============================================================================
# Test stream()
# ============================================================================

def test_stream_success(ollama_provider):
    """Test streaming response."""
    stream_responses = [
        {"response": "Hello", "done": False},
        {"response": " world", "done": False},
        {"response": "!", "done": True},
    ]

    with patch('urllib.request.urlopen') as mock_urlopen:
        # Mock streaming response
        mock_response = MagicMock()
        mock_response.__iter__ = Mock(return_value=iter([
            json.dumps(resp).encode('utf-8') + b'\n' for resp in stream_responses
        ]))
        mock_urlopen.return_value.__enter__.return_value = mock_response

        chunks = list(ollama_provider.stream("Test prompt"))

        assert chunks == ["Hello", " world", "!"]


def test_stream_with_system_prompt(ollama_provider):
    """Test streaming with system prompt."""
    stream_responses = [{"response": "OK", "done": True}]

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.__iter__ = Mock(return_value=iter([
            json.dumps(resp).encode('utf-8') + b'\n' for resp in stream_responses
        ]))
        mock_urlopen.return_value.__enter__.return_value = mock_response

        chunks = list(ollama_provider.stream(
            "User prompt",
            system_prompt="System"
        ))

        # Verify combined prompt
        call_args = mock_urlopen.call_args
        request_data = json.loads(call_args[0][0].data.decode('utf-8'))
        assert "<system>System</system>" in request_data["prompt"]


def test_stream_connection_error(ollama_provider):
    """Test streaming when service unavailable."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with pytest.raises(ProviderUnavailableException):
            list(ollama_provider.stream("Test"))


# ============================================================================
# Test validate_model()
# ============================================================================

def test_validate_model_exists(ollama_provider, mock_models_response):
    """Test model validation for existing model."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_models_response).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        assert ollama_provider.validate_model("llama2") is True
        assert ollama_provider.validate_model("mistral") is True


def test_validate_model_not_exists(ollama_provider, mock_models_response):
    """Test model validation for non-existent model."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_models_response).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        assert ollama_provider.validate_model("nonexistent") is False


# ============================================================================
# Test get_token_count()
# ============================================================================

def test_get_token_count(ollama_provider):
    """Test token counting."""
    text = "This is a test sentence with multiple words"
    count = ollama_provider.get_token_count(text)
    # Should be approximately 0.75 * word_count
    word_count = len(text.split())
    expected = int(word_count * 0.75)
    assert count == expected


def test_get_token_count_empty(ollama_provider):
    """Test token counting for empty string."""
    assert ollama_provider.get_token_count("") == 0


# ============================================================================
# Test health_check()
# ============================================================================

def test_health_check_healthy(ollama_provider, mock_models_response):
    """Test health check when service is healthy."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_models_response).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        status = ollama_provider.health_check()
        assert status == HealthStatus.HEALTHY


def test_health_check_degraded(ollama_provider):
    """Test health check when service is up but no models."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"models": []}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        status = ollama_provider.health_check()
        assert status == HealthStatus.DEGRADED


def test_health_check_unavailable(ollama_provider):
    """Test health check when service is unavailable."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        status = ollama_provider.health_check()
        assert status == HealthStatus.UNAVAILABLE


# ============================================================================
# Test pull_model()
# ============================================================================

def test_pull_model_success(ollama_provider):
    """Test successful model pull."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"status": "success"}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = ollama_provider.pull_model("llama2")
        assert result is True


def test_pull_model_failure(ollama_provider):
    """Test failed model pull."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("Network error")

        result = ollama_provider.pull_model("llama2")
        assert result is False


# ============================================================================
# Test list_models()
# ============================================================================

def test_list_models_success(ollama_provider, mock_models_response):
    """Test listing models."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_models_response).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        models = ollama_provider.list_models()
        assert models == ["llama2", "mistral", "codellama"]


def test_list_models_error(ollama_provider):
    """Test listing models when service unavailable."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("Connection error")

        models = ollama_provider.list_models()
        assert models == []


# ============================================================================
# Test get_supported_models()
# ============================================================================

def test_get_supported_models(ollama_provider, mock_models_response):
    """Test getting supported models."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_models_response).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        models = ollama_provider.get_supported_models()
        assert models == ["llama2", "mistral", "codellama"]


# ============================================================================
# Test get_default_model()
# ============================================================================

def test_get_default_model(ollama_provider):
    """Test getting default model."""
    assert ollama_provider.get_default_model() == "llama2"


def test_get_default_model_from_config():
    """Test getting default model from config."""
    provider = OllamaProvider({"default_model": "mistral"})
    assert provider.get_default_model() == "mistral"


# ============================================================================
# Test __repr__()
# ============================================================================

def test_repr(ollama_provider):
    """Test string representation."""
    repr_str = repr(ollama_provider)
    assert "OllamaProvider" in repr_str
    assert "localhost:11434" in repr_str
    assert "llama2" in repr_str
