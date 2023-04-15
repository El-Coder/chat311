"""
Chromadb memory provider.
"""
from uuid import uuid4

import chromadb
from chromadb.config import Settings

from chat311.logger import logger
from chat311.memory.base import MemoryProviderSingleton, get_ada_embedding


class ChromaMemory(MemoryProviderSingleton):
    """
    Chroma memory provider.
    """

    def __init__(self, cfg):
        self.client = chromadb.Client(
            Settings(
                chroma_api_impl="rest",
                chroma_server_host="chroma",
                chroma_server_http_port="8000",
            )
        )
        dimension = 1536
        metric = "cosine"
        pod_type = "p1"
        self.index_name = str(uuid4())  # "chat311"

        self.embedding_function = lambda x: list(map(get_ada_embedding, x))

        # self.clear()
        self.collection = self.client.get_or_create_collection(
            name=self.index_name,
            embedding_function=self.embedding_function,
        )

    def add(self, data):
        # vector = get_ada_embedding(data)
        # no metadata here. We may wish to change that long term.
        self.collection.add(
            documents=[data], ids=[str(self.collection.count())]
        )
        _text = f"Inserting data into memory at index: {self.collection.count()}:\n data: {data}"
        return _text

    def get(self, data):
        return self.get_relevant(data, 1)

    def clear(self):
        self.client.delete_collection(name=self.index_name)
        return "Obliviated"

    def get_relevant(self, data, num_relevant=5):
        query_embedding = get_ada_embedding(data)
        if num_relevant > self.collection.count():
            num_relevant = self.collection.count()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=num_relevant,
            include=["embeddings", "documents", "metadatas"],
        )

        # Sort by distance increasing
        sorted_results = (
            results  # sorted(results.distances, key=lambda x: x)
        )
        res = []
        for row in sorted_results.get("documents"):
            for item in row:
                res.append(str(item))
        return res
        # return [str(item["metadata"]["raw_text"]) for item in sorted_results]

    def get_stats(self):
        return None
