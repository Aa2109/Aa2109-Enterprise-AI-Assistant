from app.vectorstore.qdrant_store import QdrantStore

class VectorStoreFactory:
    _store = None

    @staticmethod
    def get_store():
        if VectorStoreFactory._store is None:
            VectorStoreFactory._store = QdrantStore()

        return VectorStoreFactory._store