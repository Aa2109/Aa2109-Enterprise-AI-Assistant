from fastapi import Depends

from app.db.session import get_db
from app.db.database import SessionLocal

from app.embeddings.factory import EmbeddingFactory

from app.memory.vectorstore import MemoryVectorStore
from app.memory.retriever import MemoryRetriever
from app.memory.extractor import MemoryExtractor

from app.memory.policy import MemoryPolicy

from app.repositories.memory_repository import MemoryRepository

from app.services.memory_service import MemoryService

from app.agents.nodes.memory_retriever import (
    MemoryRetrieverNode,
)
from app.agents.nodes.memory_extractor import (
    MemoryExtractorNode,
)

from app.dependencies.llm import get_llm


# =========================================================
# Repository
# =========================================================

def get_memory_repository(
    db=Depends(get_db),
):
    return MemoryRepository(
        session_factory=SessionLocal,
    )


# =========================================================
# Policy
# =========================================================

def get_memory_policy():

    return MemoryPolicy()


# =========================================================
# Vector Store
# =========================================================

def get_memory_vector_store():

    return MemoryVectorStore()


# =========================================================
# Memory Retriever
# =========================================================

def get_memory_retriever(
    vector_store=Depends(
        get_memory_vector_store
    ),
):

    embedding_provider = (
        EmbeddingFactory.get_provider()
    )

    return MemoryRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


# =========================================================
# Memory Retriever Node
# =========================================================

def get_memory_retriever_node(
    memory_retriever=Depends(
        get_memory_retriever
    ),
):

    return MemoryRetrieverNode(
        memory_retriever=memory_retriever,
    )


# =========================================================
# Memory Service
# =========================================================

def get_memory_service(
    repository=Depends(
        get_memory_repository
    ),
    policy=Depends(
        get_memory_policy
    ),
    vector_store=Depends(
        get_memory_vector_store
    ),
):

    embedding_provider = (
        EmbeddingFactory.get_provider()
    )

    return MemoryService(
        repository=repository,
        policy=policy,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )


# =========================================================
# Memory Extractor Node
# =========================================================

def get_memory_extractor_node(
    llm=Depends(get_llm),
    memory_service=Depends(
        get_memory_service
    ),
):

    extractor = MemoryExtractor(
        llm=llm
    )

    return MemoryExtractorNode(
        extractor=extractor,
        memory_service=memory_service,
    )