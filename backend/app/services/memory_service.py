from uuid import UUID

from app.db.models.memory import MemoryDB
from app.repositories.memory_repository import MemoryRepository
from app.schemas.memory import ExtractedMemory
from app.memory.policy import MemoryPolicy
from app.embeddings.base import EmbeddingProvider
from app.memory.vectorstore import MemoryVectorStore

import time
from app.observability import metrics

class MemoryService:

    def __init__(
        self,
        repository: MemoryRepository,
        policy: MemoryPolicy,
        embedding_provider: EmbeddingProvider,
        vector_store: MemoryVectorStore,
    ):
        self.repository = repository
        self.policy = policy
        self.embedding_provider = (
            embedding_provider
        )
        self.vector_store = vector_store

    # ==================================================
    # Save memory
    # ==================================================

    def save_memory(
        self,
        user_id: UUID,
        memory: ExtractedMemory,
    ) -> MemoryDB | None:

        # ------------------------------------------
        # 1. Policy gate
        # ------------------------------------------

        if not self.policy.should_store(
            memory
        ):
            return None

        content = memory.content.strip()

        if not content:
            return None

        # ------------------------------------------
        # 2. Simple deduplication
        # ------------------------------------------

        existing = (
            self.repository.find_by_content(
                user_id=user_id,
                content=content,
            )
        )

        if existing is not None:

            return existing

        # ------------------------------------------
        # 3. PostgreSQL source of truth
        # ------------------------------------------

        db_memory = MemoryDB(
            user_id=user_id,
            memory_type=(
                memory.memory_type.value
            ),
            content=content,
            importance=memory.importance,
        )

        saved = self.repository.create(
            db_memory
        )

        # ------------------------------------------
        # 4. Generate embedding
        # ------------------------------------------

        embedding = (
            self.embedding_provider.embed(
                [content]
            )[0]
        )

        # ------------------------------------------
        # 5. Store vector in Qdrant
        # ------------------------------------------

        self.vector_store.upsert(
            memory_id=saved.id,
            embedding=embedding,
            user_id=saved.user_id,
            memory_type=saved.memory_type,
            content=saved.content,
            importance=saved.importance,
        )

        metrics.memory_created.add(1)

        return saved

    # ==================================================
    # Get memory
    # ==================================================

    def get_memory(
        self,
        memory_id: UUID,
        user_id: UUID,
    ) -> MemoryDB | None:

        memory = self.repository.get(
            memory_id
        )

        if memory is None:
            return None

        if memory.user_id != user_id:
            return None

        return memory

    # ==================================================
    # List memories
    # ==================================================

    def list_memories(
        self,
        user_id: UUID,
    ) -> list[MemoryDB]:

        return self.repository.list_by_user(
            user_id
        )

    # ==================================================
    # Delete memory
    # ==================================================

    def delete_memory(
        self,
        memory_id: UUID,
        user_id: UUID,
    ) -> bool:

        memory = self.repository.get(
            memory_id
        )

        if memory is None:
            return False

        if memory.user_id != user_id:
            return False

        deleted = self.repository.delete(
            memory_id
        )

        if deleted:
            self.vector_store.delete(
                memory_id
            )

        return deleted