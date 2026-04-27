from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid

class VectorDB:
    def __init__(self, host, port, collection_name, vector_size=1024):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name

        if not self.client.collection_exists(collection_name):
            print(f"Создаём коллекцию {collection_name} с размером {vector_size}")

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                ),
            )

    def upsert(self, vectors, payloads):
        points = []
        for v, p in zip(vectors, payloads):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=v,
                    payload=p
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, vector, limit=5):
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit
        )
