from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

collection_name = "new_rag_collection"

info = client.get_collection(collection_name)

print("Коллекция:", collection_name)
print("Количество точек:", info.points_count)

points, _ = client.scroll(
    collection_name=collection_name,
    limit=3,
    with_payload=True,
    with_vectors=False
)

for i, p in enumerate(points):
    print(f"\n--- POINT {i+1} ---")
    print(p.payload["text"][:300])