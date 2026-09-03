from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
)

from app.core.config import settings


class MemoryVectorStore:

    def __init__(self):

        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=30,
        )

        self.collection = (
            settings.QDRANT_MEMORY_COLLECTION
        )

        self.create_collection()

    def create_collection(self):

        collections = (
            self.client.get_collections()
        )

        names = {
            collection.name
            for collection in collections.collections
        }

        if self.collection in names:
          return

        distance_map = {
            "COSINE": Distance.COSINE,
            "DOT": Distance.DOT,
            "EUCLID": Distance.EUCLID,
        }

        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=settings.VECTOR_DIMENSION,
                distance=distance_map[
                    settings.VECTOR_DISTANCE.upper()
                ],
            ),
        )

    def upsert(
        self,
        memory_id,
        embedding,
        user_id,
        memory_type,
        content,
        importance,
    ):

        point = PointStruct(
            id=str(memory_id),
            vector=embedding,
            payload={
                "memory_id": str(memory_id),
                "user_id": str(user_id),
                "memory_type": memory_type,
                "content": content,
                "importance": float(importance),
            },
        )

        self.client.upsert(
            collection_name=self.collection,
            points=[point],
        )

    def search(
        self,
        vector,
        user_id,
        limit=5,
        score_threshold=None,
    ):

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(
                        value=str(user_id)
                    ),
                )
            ]
        )

        response = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        results = []

        for hit in response.points:

            if (
                score_threshold is not None
                and hit.score < score_threshold
            ):
                continue

            payload = hit.payload or {}

            results.append(
                {
                    "memory_id": payload.get(
                        "memory_id"
                    ),
                    "user_id": payload.get(
                        "user_id"
                    ),
                    "memory_type": payload.get(
                        "memory_type"
                    ),
                    "content": payload.get(
                        "content"
                    ),
                    "importance": float(
                        payload.get(
                            "importance",
                            0.5,
                        )
                    ),
                    "score": float(
                        hit.score
                    ),
                }
            )

        return results

    def delete(
        self,
        memory_id,
    ):

        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(
                points=[str(memory_id)]
            ),
        )