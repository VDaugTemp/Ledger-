# lib/model_provider/sparse_embeddings.py
"""BM42 sparse embeddings via FastEmbed — wrapped to keep fastembed out of agent.py."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastembed import SparseTextEmbedding as _SparseTextEmbedding


class ModelProviderSparseEmbeddings:
    """Wraps fastembed BM42 sparse embedding model.

    Lazy-loads the FastEmbed model on first use (~22 MB download to ~/.cache/fastembed).
    """

    DEFAULT_MODEL = "Qdrant/bm42-all-minilm-l6-v2-attentions"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self._model_name = model
        self._model: _SparseTextEmbedding | None = None

    def _get_model(self) -> _SparseTextEmbedding:
        if self._model is None:
            from fastembed import SparseTextEmbedding
            self._model = SparseTextEmbedding(self._model_name)
        return self._model

    def embed_query(self, text: str) -> tuple[list[int], list[float]]:
        """Embed a single string.

        Returns (indices, values) as plain Python lists, ready for
        qdrant_client.models.SparseVector(indices=..., values=...).

        fastembed.SparseTextEmbedding.embed() returns a generator of SparseEmbedding
        objects whose .indices and .values are numpy arrays — .tolist() is required.
        """
        model = self._get_model()
        result = next(model.embed([text]))
        return result.indices.tolist(), result.values.tolist()

    def embed_documents(self, texts: list[str]) -> list[tuple[list[int], list[float]]]:
        """Batch embed a list of strings.

        Returns a list of (indices, values) tuples. Used by the ingest pipeline
        to embed full batches efficiently without calling embed_query in a loop.
        """
        model = self._get_model()
        return [
            (result.indices.tolist(), result.values.tolist())
            for result in model.embed(texts)
        ]
