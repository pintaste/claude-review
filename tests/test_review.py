"""Tests for review.py core logic."""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure review.py is importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from review import build_prompt, chunk_diff, format_comment, review_diff


class TestChunkDiff(unittest.TestCase):
    def test_chunk_diff_single_file(self):
        """A diff with one file and no size overflow stays as one chunk."""
        diff = "diff --git a/foo.py b/foo.py\n+added line\n"
        chunks = chunk_diff(diff)
        assert len(chunks) == 1
        assert chunks[0] == diff

    def test_chunk_diff_splits_at_boundary(self):
        """A diff that exceeds max_chars is split at the next diff --git boundary."""
        # Build a first file block larger than max_chars
        big_block = "diff --git a/big.py b/big.py\n" + "x" * 12001 + "\n"
        second_block = "diff --git a/small.py b/small.py\n+tiny\n"
        diff = big_block + second_block

        chunks = chunk_diff(diff, max_chars=12000)
        assert len(chunks) == 2
        assert "big.py" in chunks[0]
        assert "small.py" in chunks[1]

    def test_chunk_diff_empty(self):
        """Empty string returns an empty list (actual behavior)."""
        chunks = chunk_diff("")
        assert chunks == []

    def test_chunk_diff_below_threshold_not_split(self):
        """Multiple files that stay under max_chars are not split."""
        block1 = "diff --git a/a.py b/a.py\n+line\n"
        block2 = "diff --git a/b.py b/b.py\n+line\n"
        diff = block1 + block2
        chunks = chunk_diff(diff, max_chars=12000)
        assert len(chunks) == 1


class TestBuildPrompt(unittest.TestCase):
    def test_build_prompt_returns_tuple(self):
        """build_prompt returns a (system, user) tuple."""
        result = build_prompt("some diff", "security")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_build_prompt_contains_diff(self):
        """The user prompt contains the diff chunk."""
        diff_chunk = "diff --git a/x.py b/x.py\n+hello\n"
        _system, user = build_prompt(diff_chunk, "all")
        assert diff_chunk in user

    def test_build_prompt_contains_focus(self):
        """The user prompt contains the focus value when not 'all'."""
        _system, user = build_prompt("some diff", "security,performance")
        assert "security" in user
        assert "performance" in user

    def test_build_prompt_focus_all_uses_default_areas(self):
        """Focus='all' results in a generic review instruction, not a literal 'all'."""
        _system, user = build_prompt("some diff", "all")
        assert "correctness" in user or "security" in user

    def test_build_prompt_system_prompt_is_nonempty(self):
        """System prompt is a non-empty string."""
        system, _user = build_prompt("diff", "all")
        assert isinstance(system, str) and len(system) > 0


class TestFormatComment(unittest.TestCase):
    def test_format_comment_has_header(self):
        """Result starts with the expected markdown header."""
        result = format_comment("looks good", "all")
        assert result.startswith("## Claude Code Review")

    def test_format_comment_has_footer(self):
        """Result contains the claude-review attribution link."""
        result = format_comment("looks good", "all")
        assert "claude-review" in result
        assert "pintaste/claude-review" in result

    def test_format_comment_includes_text(self):
        """The review_text appears in the formatted comment."""
        review_text = "This is the review body."
        result = format_comment(review_text, "security")
        assert review_text in result

    def test_format_comment_includes_focus(self):
        """The focus label appears in the footer line."""
        result = format_comment("ok", "security,performance")
        assert "security,performance" in result


class TestReviewDiff(unittest.TestCase):
    def _make_client(self, response_text="LGTM"):
        """Return a mock Anthropic client that returns response_text."""
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response_text)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        return mock_client

    def test_review_diff_calls_messages_create(self):
        """review_diff calls client.messages.create at least once."""
        client = self._make_client()
        diff = "diff --git a/x.py b/x.py\n+hello\n"
        review_diff(diff, "all", 1024, client)
        assert client.messages.create.called

    def test_review_diff_single_chunk_returns_response(self):
        """Single-chunk diff returns the mock response text directly."""
        client = self._make_client("Looks great!")
        diff = "diff --git a/x.py b/x.py\n+hello\n"
        result = review_diff(diff, "all", 1024, client)
        assert "Looks great!" in result

    def test_review_diff_multi_chunk_joined_with_separator(self):
        """Multiple chunks are joined with the --- separator."""
        # Two chunks: first triggers split boundary
        big_block = "diff --git a/big.py b/big.py\n" + "x" * 12001 + "\n"
        small_block = "diff --git a/small.py b/small.py\n+small\n"
        diff = big_block + small_block

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text=f"response_{call_count}")]
            return mock_msg

        client = MagicMock()
        client.messages.create.side_effect = side_effect

        result = review_diff(diff, "all", 1024, client)
        assert client.messages.create.call_count == 2
        assert "---" in result
        assert "response_1" in result
        assert "response_2" in result

    def test_review_diff_passes_model_and_max_tokens(self):
        """review_diff passes model and max_tokens to messages.create."""
        client = self._make_client()
        diff = "diff --git a/x.py b/x.py\n+hello\n"
        review_diff(diff, "all", 512, client)
        call_kwargs = client.messages.create.call_args
        assert call_kwargs.kwargs.get("max_tokens") == 512
        assert "claude" in call_kwargs.kwargs.get("model", "")


if __name__ == "__main__":
    unittest.main()
