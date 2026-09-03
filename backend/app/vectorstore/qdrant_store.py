from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    FieldCondition,
    Filter,
    MatchValue,
)
from app.core.config import settings
from app.vectorstore.base import VectorStore
from qdrant_client.models import PointIdsList


# Constructor
class QdrantStore(VectorStore):

    def __init__(self):

        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )

        self.collection = settings.QDRANT_COLLECTION

        self.create_collection()

# Automatic collection creation
    def create_collection(self):

        collections = self.client.get_collections()

        names = {
            c.name
            for c in collections.collections
        }

        if self.collection in names:
            return

        DISTANCE_MAP = {
            "COSINE": Distance.COSINE,
            "DOT": Distance.DOT,
            "EUCLID": Distance.EUCLID,
            }
        
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=settings.VECTOR_DIMENSION,
                # distance=Distance.COSINE,
                distance=DISTANCE_MAP[
                   settings.VECTOR_DISTANCE.upper()
                ]
            ),
        )

    # Upsert
    def upsert(self, vectors: list[dict]):
      points = []

      for vector in vectors:

        points.append(

            PointStruct(
                id=str(vector["chunk_id"]),
                vector=vector["embedding"],
                payload={
                    "document_id": str(vector["document_id"]),
                    "chunk_id": str(vector["chunk_id"]),
                    "owner_id": str(vector["owner_id"]),
                    "chunk_index": vector["chunk_index"],
                    "content": vector["content"],
                    
                },
            )
        )
        

      self.client.upsert(
        collection_name=self.collection,
        points=points,
      )

    # Search
    def search(
        self,
        vector: list[float],
        limit: int = 5,
        owner_id=None,
        document_id=None,
        score_threshold=None,
    ) -> list[dict]:

        conditions = []

        if owner_id is not None:
            conditions.append(
                FieldCondition(
                    key="owner_id",
                    match=MatchValue(
                        value=str(owner_id)
                    ),
                )
            )

        if document_id is not None:
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(
                        value=str(document_id)
                    ),
                )
            )

        query_filter = None

        if conditions:
            query_filter = Filter(
                must=conditions
            )

        response = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        hits = response.points

        results = []

        for hit in hits:

            if (
                score_threshold is not None
                and hit.score < score_threshold
            ):
                continue

            payload = hit.payload or {}

            results.append(
                {
                    "chunk_id": payload["chunk_id"],
                    "document_id": payload["document_id"],
                    "chunk_index": payload["chunk_index"],
                    "content": payload["content"],
                    "score": float(hit.score),
                }
            )

        return results

# Delete
    def delete(
    self,
    ids,
    ):
        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(
                points=[str(i) for i in ids]
            ),
        )

