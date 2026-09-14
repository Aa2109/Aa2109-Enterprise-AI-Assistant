from sentence_transformers import SentenceTransformer
from app.embeddings.base import EmbeddingProvider

class SentenceTransformerProvider(EmbeddingProvider):
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()