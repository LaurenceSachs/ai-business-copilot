"""
Embedding service for generating vector embeddings from text.
"""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class EmbeddingService:
    """Service for generating text embeddings using sentence transformers."""

    def __init__(self):
        """Initialize the embedding model."""
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimension

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Replace empty strings with placeholder to avoid errors
        processed_texts = [text if text.strip() else " " for text in texts]

        embeddings = self.model.encode(processed_texts, convert_to_numpy=True, show_progress_bar=True)
        return embeddings.tolist()

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)


# Singleton instance
embedding_service = EmbeddingService()
