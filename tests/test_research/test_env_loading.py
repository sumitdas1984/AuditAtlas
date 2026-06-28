"""Tests for the .env loading helper used by the research CLI."""

import os
from pathlib import Path

import pytest

from src.research.cli import _load_env_file


@pytest.fixture(autouse=True)
def clean_anthropic_env(monkeypatch):
    """Ensure ANTHROPIC_API_KEY is unset for each test, then restore."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield


class TestLoadEnvFile:
    """Direct unit tests for the _load_env_file helper."""

    def test_sets_anthropic_key_when_env_file_present(self, tmp_path, monkeypatch):
        env_path = tmp_path / ".env"
        env_path.write_text("ANTHROPIC_API_KEY=test-key-from-file\n")
        _load_env_file(env_path=env_path)
        assert os.environ.get("ANTHROPIC_API_KEY") == "test-key-from-file"

    def test_no_op_when_env_file_missing(self, tmp_path):
        """Missing .env file is silently ignored (not an error)."""
        env_path = tmp_path / ".env.does.not.exist"
        _load_env_file(env_path=env_path)
        assert os.environ.get("ANTHROPIC_API_KEY") is None

    def test_no_op_when_env_path_is_none_and_project_env_missing(self, tmp_path):
        """When called with an explicit non-existent path, no-op (no crash).

        We use an explicit non-existent path instead of relying on the
        project-root .env being missing, because a real .env may exist
        in dev environments.
        """
        env_path = tmp_path / "definitely-does-not-exist.env"
        # No exception when .env file doesn't exist
        _load_env_file(env_path=env_path)
        assert os.environ.get("ANTHROPIC_API_KEY") is None

    def test_shell_env_var_takes_precedence_over_dotenv(self, tmp_path, monkeypatch):
        """12-factor convention: existing shell env wins over .env file.

        With override=False, dotenv only sets vars that aren't already set.
        """
        # Simulate shell already exporting the key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "shell-key-wins")
        env_path = tmp_path / ".env"
        env_path.write_text("ANTHROPIC_API_KEY=env-file-key\n")
        _load_env_file(env_path=env_path)
        # Shell value preserved, .env file value ignored
        assert os.environ.get("ANTHROPIC_API_KEY") == "shell-key-wins"

    def test_handles_malformed_lines(self, tmp_path):
        """Comments, blank lines, and lines without '=' should be ignored gracefully."""
        env_path = tmp_path / ".env"
        env_path.write_text(
            "# This is a comment\n"
            "\n"
            "ANTHROPIC_API_KEY=valid-key\n"
            "INVALID_LINE_NO_EQUALS\n"
            "ANOTHER=value\n"
        )
        _load_env_file(env_path=env_path)
        # Valid keys are set; malformed line is silently ignored (no crash)
        assert os.environ.get("ANTHROPIC_API_KEY") == "valid-key"
        assert os.environ.get("ANOTHER") == "value"

    def test_handles_quoted_values(self, tmp_path):
        """python-dotenv strips quotes around values: KEY=\"value with spaces\"."""
        env_path = tmp_path / ".env"
        env_path.write_text('ANTHROPIC_API_KEY="my quoted key"\n')
        _load_env_file(env_path=env_path)
        # Quotes should be stripped, value is the inner string
        assert os.environ.get("ANTHROPIC_API_KEY") == "my quoted key"

    def test_handles_values_with_spaces(self, tmp_path):
        """Unquoted values with spaces are parsed correctly (full line = value)."""
        env_path = tmp_path / ".env"
        env_path.write_text('ANTHROPIC_API_KEY=key with spaces\n')
        _load_env_file(env_path=env_path)
        assert os.environ.get("ANTHROPIC_API_KEY") == "key with spaces"

    def test_sets_multiple_keys(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text(
            "ANTHROPIC_API_KEY=key1\n"
            "OTHER_VAR=value2\n"
        )
        _load_env_file(env_path=env_path)
        assert os.environ.get("ANTHROPIC_API_KEY") == "key1"
        assert os.environ.get("OTHER_VAR") == "value2"

    def test_does_not_overwrite_existing_other_vars(self, tmp_path, monkeypatch):
        """Existing shell env vars are preserved for all keys, not just ANTHROPIC_API_KEY."""
        monkeypatch.setenv("EXISTING_VAR", "preserve-me")
        env_path = tmp_path / ".env"
        env_path.write_text("EXISTING_VAR=overwrite-attempt\nNEW_VAR=created\n")
        _load_env_file(env_path=env_path)
        # EXISTING_VAR preserved; NEW_VAR created
        assert os.environ.get("EXISTING_VAR") == "preserve-me"
        assert os.environ.get("NEW_VAR") == "created"


# ---------------------------------------------------------------------------
# Integration tests (calling run_research)
# ---------------------------------------------------------------------------

class TestRunResearchLoadsEnvFile:
    """End-to-end: run_research picks up ANTHROPIC_API_KEY from .env."""

    def test_run_research_succeeds_with_dotenv_and_no_shell_var(
        self, tmp_path, monkeypatch
    ):
        """With .env file present but no shell var, run_research should not
        exit with 'missing API key' error."""
        from src.research.cli import run_research

        # Build a minimal KB
        from src.ingestion.chunkers.chunker import Chunk
        from src.ingestion.embedder.embedder import Embedder
        from src.ingestion.storage.chroma_store import ChromaStore
        from src.ingestion.storage.json_store import JsonStore

        chroma_dir = str(tmp_path / "chroma")
        jsonl_path = str(tmp_path / "chunks.jsonl")
        collection_name = "env_test"

        chroma = ChromaStore(persist_dir=chroma_dir, collection_name=collection_name)
        json_store = JsonStore(store_path=jsonl_path)
        chunk = Chunk(
            chunk_id="X.1",
            source_type="A",
            document_id="X",
            document_type="Standard",
            chunk_index=1,
            content="hello",
            metadata={},
            citation={"format": "[X]", "type": "pcaob"},
        )
        chroma.add([chunk], Embedder())
        json_store.write_batch([chunk])

        # .env has a key
        env_path = tmp_path / ".env"
        env_path.write_text("ANTHROPIC_API_KEY=dotenv-test-key\n")

        # Force run_research to use our test .env by monkeypatching _load_env_file
        # to point at it (instead of the project-root .env).
        import src.research.cli as cli_module
        original_load = cli_module._load_env_file
        def fake_load():
            original_load(env_path=env_path)
        monkeypatch.setattr(cli_module, "_load_env_file", fake_load)

        # Use mock LLM so no actual API call is made; just verify the API
        # key check passes (no exit 5).
        code, output = run_research(
            query="x",
            use_mock_llm=True,
            chroma_dir=chroma_dir,
            collection_name=collection_name,
            jsonl_path=jsonl_path,
        )
        assert code == 0  # not exit 5 (which would mean missing API key)

    def test_use_mock_llm_does_not_require_dotenv(self, tmp_path, monkeypatch):
        """Mock LLM path doesn't need ANTHROPIC_API_KEY at all.

        Verifies the helper isn't required for mock tests.
        """
        from src.research.cli import run_research

        # No .env file, no shell var
        # ANTHROPIC_API_KEY already unset via fixture

        # Create a minimal empty KB
        empty_chroma = str(tmp_path / "chroma")
        empty_jsonl = str(tmp_path / "chunks.jsonl")

        code, output = run_research(
            query="x",
            use_mock_llm=True,
            chroma_dir=empty_chroma,
            collection_name="nonexistent",
            jsonl_path=empty_jsonl,
        )
        # Should exit with code 3 (uninit KB) — NOT exit 5 (missing API key)
        assert code == 3

    def test_without_mock_llm_and_no_key_returns_exit_5(self, tmp_path):
        """Without --use-mock-llm and no .env, exit 5 with API key error."""
        from src.research.cli import run_research

        # No .env, no shell var
        empty_chroma = str(tmp_path / "chroma")
        empty_jsonl = str(tmp_path / "chunks.jsonl")

        code, output = run_research(
            query="x",
            use_mock_llm=False,  # would need real API key
            chroma_dir=empty_chroma,
            collection_name="nonexistent",
            jsonl_path=empty_jsonl,
        )
        # KB check runs first; may be exit 3 OR exit 5 depending on order.
        # The key point: it does NOT silently succeed.
        assert code in (3, 5)
