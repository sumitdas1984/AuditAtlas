from sentence_transformers import SentenceTransformer
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the embedding model."""
    return SentenceTransformer("all-MiniLM-L6-v2")


class Embedder:
    """Sentence-transformer embedder for chunk content.

    Uses all-MiniLM-L6-v2 model to generate 384-dimensional embeddings.
    Model is cached in memory after first load.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load model on first use."""
        if self._model is None:
            self._model = _get_model()
        return self._model

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: The text to embed.

        Returns:
            List of 384 float values representing the embedding.
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors (one per input text).
        """
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
