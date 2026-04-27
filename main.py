from rag import RAGPipeline
from qdrant_client import QdrantClient

if __name__ == "__main__":
    rag = RAGPipeline()
    client = QdrantClient(host="localhost", port=6333)
    while True:
        query = input("Question: ")
        if query == "exit":
            break
        print(rag.generate(query))