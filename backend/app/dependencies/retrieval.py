from app.embeddings.factory import EmbeddingFactory
from app.vectorstore.factory import VectorStoreFactory
from app.services.retrieval_service import RetrievalService



def get_retrieval_service():

    embedding_provider = (
        EmbeddingFactory.get_provider()
    )


    vector_store = (
        VectorStoreFactory.get_store()
    )


    return RetrievalService(

        embedding_provider,

        vector_store,

    )