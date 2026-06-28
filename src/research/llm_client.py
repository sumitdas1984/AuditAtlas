"""LLM client abstraction for answer generation.

Provides:
- `LLMClient`: Protocol for any LLM backend (Anthropic, OpenAI, local, mock)
- `AnthropicClient`: Real implementation using the `anthropic` SDK
- `MockClient`: Deterministic client for tests; accepts pre-canned responses
  or a callable

The `anthropic` package is imported lazily so tests can run without it
installed; only `AnthropicClient.__init__` triggers the import.
"""

import logging
import os
from typing import Callable, Optional, Protocol, Union

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Minimal interface for an LLM client.

    Implementations must accept a system prompt, a user prompt, and an
    optional max_tokens limit, and return the LLM's text response.
    """

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str: ...


class AnthropicClient:
    """Anthropic Claude API client.

    Reads `ANTHROPIC_API_KEY` from the environment at construction time.
    Lazy-imports the `anthropic` package so tests don't need it.

    Args:
        model: The Claude model to use. Default: "claude-haiku-4-5".
        api_key: Optional override for the API key. If None, reads from env.
    """

    DEFAULT_MODEL = "claude-haiku-4-5"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
    ):
        self.model = model

        # Validate API key up-front so callers get a clear error even if
        # the `anthropic` package isn't installed.
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Either set the env var or "
                "pass api_key= to AnthropicClient()."
            )

        # Lazy-instantiate the SDK on first use, so construction is cheap
        # and tests that only check config don't need the package.
        self._client: Optional["anthropic.Anthropic"] = None  # type: ignore[name-defined]

    def _get_client(self):
        """Lazily build the Anthropic SDK client on first call."""
        if self._client is None:
            try:
                import anthropic  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "AnthropicClient requires the `anthropic` package. "
                    "Install with: pip install anthropic"
                ) from exc
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Send a prompt to Claude and return the response text."""
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
        )
        # response.content is a list of content blocks; for text responses
        # there's one block of type "text"
        if not response.content:
            return ""
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        )


# A response is either a pre-canned string, or a callable that takes
# (system, user, max_tokens) and returns a string. Useful for tests that
# need different responses per call.
MockResponse = Union[str, Callable[[str, str, int], str]]


class MockClient:
    """Deterministic LLM client for tests.

    Args:
        response: Either a string (returned for every call) or a callable
            that takes (system, user, max_tokens) and returns a string.
        raise_on_call: If set, calling complete() raises this exception
            instead of returning a response. Useful for error-path tests.

    Records every call in `self.calls` for test assertions:
        self.calls = [{"system": ..., "user": ..., "max_tokens": ...}, ...]
    """

    def __init__(
        self,
        response: MockResponse = "",
        raise_on_call: Optional[Exception] = None,
    ):
        self._response = response
        self._raise = raise_on_call
        self.calls: list[dict] = []

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Return the configured response (or raise)."""
        self.calls.append({
            "system": system,
            "user": user,
            "max_tokens": max_tokens,
        })
        if self._raise is not None:
            raise self._raise
        if callable(self._response):
            return self._response(system, user, max_tokens)
        return self._response


__all__ = ["LLMClient", "AnthropicClient", "MockClient"]
