"""
Chromadb memory provider.
"""
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
        index_name = "chat311"

        self.collection = self.client.get_or_create_collection(
            name=self.index_name
        )

    def add(self, data):
        vector = get_ada_embedding(data)
        # no metadata here. We may wish to change that long term.
        self.collection.add(embeddings=[vector], documents=[])
        resp = self.index.upsert(
            [(str(self.vec_num), vector, {"raw_text": data})]
        )
        _text = f"Inserting data into memory at index: {self.vec_num}:\n data: {data}"
        self.vec_num += 1
        return _text

    def get(self, data):
        return self.get_relevant(data, 1)

    def clear(self):
        self.index.delete(deleteAll=True)
        return "Obliviated"

    def get_relevant(self, data, num_relevant=5):
        """
        Returns all the data in the memory that is relevant to the given data.
        :param data: The data to compare to.
        :param num_relevant: The number of relevant data to return. Defaults to 5
        """
        query_embedding = get_ada_embedding(data)
        results = self.index.query(
            query_embedding, top_k=num_relevant, include_metadata=True
        )
        sorted_results = sorted(results.matches, key=lambda x: x.score)
        return [str(item["metadata"]["raw_text"]) for item in sorted_results]

    def get_stats(self):
        return self.index.describe_index_stats()
