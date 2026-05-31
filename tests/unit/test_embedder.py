"""Unit tests for E5Embedder — SentenceTransformer is mocked, no real model loaded."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestE5Embedder:
    """Tests for E5Embedder prefix injection and normalize_embeddings flag."""

    def _make_embedder(self, mock_model):
        """Build an E5Embedder with a patched SentenceTransformer."""
        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            from app.infrastructure.embedder.e5 import E5Embedder

            return E5Embedder("intfloat/multilingual-e5-small")

    def test_embed_query_prepends_query_prefix(self):
        from app.infrastructure.embedder.e5 import E5Embedder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])

        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            embedder = E5Embedder("test-model")

        embedder.embed_query("hello world")

        call_args = mock_model.encode.call_args
        assert call_args[0][0] == "query: hello world"

    def test_embed_query_passes_normalize_true(self):
        from app.infrastructure.embedder.e5 import E5Embedder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])

        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            embedder = E5Embedder("test-model")

        embedder.embed_query("hello")

        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs.get("normalize_embeddings") is True

    def test_embed_documents_prepends_passage_prefix(self):
        from app.infrastructure.embedder.e5 import E5Embedder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])

        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            embedder = E5Embedder("test-model")

        embedder.embed_documents(["doc a", "doc b"])

        call_args = mock_model.encode.call_args
        prefixed = call_args[0][0]
        assert prefixed == ["passage: doc a", "passage: doc b"]

    def test_embed_documents_passes_normalize_true(self):
        from app.infrastructure.embedder.e5 import E5Embedder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])

        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            embedder = E5Embedder("test-model")

        embedder.embed_documents(["text"])

        call_kwargs = mock_model.encode.call_args[1]
        assert call_kwargs.get("normalize_embeddings") is True

    def test_embed_query_returns_list_of_floats(self):
        from app.infrastructure.embedder.e5 import E5Embedder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])

        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            embedder = E5Embedder("test-model")

        result = embedder.embed_query("test")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_embed_documents_returns_list_of_lists(self):
        from app.infrastructure.embedder.e5 import E5Embedder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])

        with patch("app.infrastructure.embedder.e5.SentenceTransformer", return_value=mock_model):
            embedder = E5Embedder("test-model")

        result = embedder.embed_documents(["a", "b"])
        assert isinstance(result, list)
        assert all(isinstance(row, list) for row in result)
        assert all(isinstance(v, float) for row in result for v in row)
