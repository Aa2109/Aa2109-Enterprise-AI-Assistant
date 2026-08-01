# app/embeddings/factory.py

from app.core.config import settings
from app.embeddings.providers.openai_provider import (
    OpenAIEmbeddingProvider,
)
from app.embeddings.providers.sentence_transformer_provider import (
    SentenceTransformerProvider,
)

class EmbeddingFactory:

    @staticmethod
    def get_provider():

        if settings.EMBEDDING_PROVIDER == "local":
            return SentenceTransformerProvider()
         
        return OpenAIEmbeddingProvider()
