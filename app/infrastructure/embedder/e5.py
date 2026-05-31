"""E5 multilingual embedding model wrapper.

Encapsulates the mandatory query:/passage: prefix requirements for the
intfloat/multilingual-e5-small model so they cannot be forgotten at call sites.
"""

from sentence_transformers import SentenceTransformer


class E5Embedder:
    """Embedding model that enforces e5 prefix conventions.

    - ``embed_query`` → prefixes each text with ``"query: "``
    - ``embed_documents`` → prefixes each text with ``"passage: "``

    Both methods set ``normalize_embeddings=True`` so cosine similarity can be
    computed directly via dot product on the returned vectors.
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self._model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string with the ``query:`` prefix."""
        result = self._model.encode(f"query: {text}", normalize_embeddings=True)
        return result.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document strings with the ``passage:`` prefix."""
        prefixed = [f"passage: {t}" for t in texts]
        result = self._model.encode(prefixed, normalize_embeddings=True)
        return result.tolist()
