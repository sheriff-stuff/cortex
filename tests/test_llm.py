"""Tests for LLM provider dispatching and OpenAI-compatible client."""

from unittest.mock import MagicMock, patch

import pytest

from api.config import Config
from api.llm import (
    _openai_headers,
    check_llm,
    check_llm_model_available,
    check_openai,
    check_openai_model_available,
    query_llm,
    query_openai,
)


# --- Header construction ---


class TestOpenAIHeaders:
    def test_with_api_key(self):
        config = Config(llm_api_key="sk-test-123")
        headers = _openai_headers(config)
        assert headers["Authorization"] == "Bearer sk-test-123"
        assert headers["Content-Type"] == "application/json"

    def test_without_api_key(self):
        config = Config(llm_api_key="")
        headers = _openai_headers(config)
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"


# --- OpenAI checks ---


class TestCheckOpenAI:
    @patch("api.llm._client.get")
    def test_reachable(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        config = Config(llm_provider="openai", llm_base_url="http://test/v1")
        assert check_openai(config) is True
        mock_get.assert_called_once()
        assert "http://test/v1/models" in mock_get.call_args[0]

    @patch("api.llm._client.get")
    def test_404_treated_as_reachable(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        config = Config(llm_provider="openai")
        assert check_openai(config) is True

    @patch("api.llm._client.get")
    def test_405_treated_as_reachable(self, mock_get):
        mock_get.return_value = MagicMock(status_code=405)
        config = Config(llm_provider="openai")
        assert check_openai(config) is True

    @patch("api.llm._client.get")
    def test_unreachable(self, mock_get):
        from httpx import ConnectError
        mock_get.side_effect = ConnectError("refused", request=None)
        config = Config(llm_provider="openai")
        assert check_openai(config) is False


class TestCheckOpenAIModelAvailable:
    @patch("api.llm._client.get")
    def test_model_found(self, mock_get):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"data": [{"id": "gpt-4o"}, {"id": "gpt-3.5-turbo"}]}
        mock_get.return_value = resp
        config = Config(llm_provider="openai", llm_model="gpt-4o")
        assert check_openai_model_available(config) is True

    @patch("api.llm._client.get")
    def test_model_not_found(self, mock_get):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"data": [{"id": "gpt-3.5-turbo"}]}
        mock_get.return_value = resp
        config = Config(llm_provider="openai", llm_model="gpt-4o")
        assert check_openai_model_available(config) is False

    @patch("api.llm._client.get")
    def test_404_assumes_available(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        config = Config(llm_provider="openai", llm_model="gpt-4o")
        assert check_openai_model_available(config) is True


# --- OpenAI query ---


class TestQueryOpenAI:
    @patch("api.llm._client.post")
    def test_successful_query(self, mock_post):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {
            "choices": [{"message": {"content": "Hello world"}}],
        }
        resp.raise_for_status = MagicMock()
        mock_post.return_value = resp

        config = Config(
            llm_provider="openai",
            llm_model="gpt-4o",
            llm_base_url="http://test/v1",
            llm_api_key="sk-test",
        )
        result = query_openai("test prompt", config)
        assert result == "Hello world"

        # Verify request format
        call_kwargs = mock_post.call_args
        assert "http://test/v1/chat/completions" in call_kwargs[0]
        body = call_kwargs[1]["json"]
        assert body["model"] == "gpt-4o"
        assert body["messages"] == [{"role": "user", "content": "test prompt"}]
        assert body["temperature"] == 0.1

    @patch("api.llm._client.post")
    def test_unexpected_response_format(self, mock_post):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"unexpected": "format"}
        resp.raise_for_status = MagicMock()
        mock_post.return_value = resp

        config = Config(llm_provider="openai")
        with pytest.raises(ValueError, match="Unexpected response format"):
            query_openai("test", config)


# --- Dispatchers ---


class TestDispatchers:
    @patch("api.llm.check_ollama", return_value=True)
    def test_check_llm_ollama(self, mock_check):
        config = Config(llm_provider="ollama")
        assert check_llm(config) is True
        mock_check.assert_called_once_with(config)

    @patch("api.llm.check_openai", return_value=True)
    def test_check_llm_openai(self, mock_check):
        config = Config(llm_provider="openai")
        assert check_llm(config) is True
        mock_check.assert_called_once_with(config)

    @patch("api.llm.check_model_available", return_value=True)
    def test_check_model_ollama(self, mock_check):
        config = Config(llm_provider="ollama")
        assert check_llm_model_available(config) is True
        mock_check.assert_called_once_with(config)

    @patch("api.llm.check_openai_model_available", return_value=True)
    def test_check_model_openai(self, mock_check):
        config = Config(llm_provider="openai")
        assert check_llm_model_available(config) is True
        mock_check.assert_called_once_with(config)

    @patch("api.llm.query_ollama", return_value="ollama response")
    def test_query_llm_ollama(self, mock_query):
        config = Config(llm_provider="ollama")
        result = query_llm("prompt", config)
        assert result == "ollama response"
        mock_query.assert_called_once_with("prompt", config)

    @patch("api.llm.query_openai", return_value="openai response")
    def test_query_llm_openai(self, mock_query):
        config = Config(llm_provider="openai")
        result = query_llm("prompt", config)
        assert result == "openai response"
        mock_query.assert_called_once_with("prompt", config)

    def test_invalid_provider_raises(self):
        config = Config(llm_provider="invalid")
        with pytest.raises(ValueError, match="Unsupported llm_provider"):
            check_llm(config)
