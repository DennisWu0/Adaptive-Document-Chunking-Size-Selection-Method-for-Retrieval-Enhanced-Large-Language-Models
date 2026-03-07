import os
os.environ["CHROMA_TELEMETRY"] = "False"

import chromadb
import os
from chromadb.config import Settings



CHUNK_SIZES = ["512", "256", "128"]

class ChromaDBClient:
    def __init__(self, embedding_functions, path=None):
        
        chroma_db_dir = os.environ.get("CHROMA_DB_DIR")
        self.client = chromadb.PersistentClient(
            path=chroma_db_dir,
            settings=Settings(anonymized_telemetry=False))
        
        # self.client = chromadb.HttpClient(host="localhost", port=8000)
        self.embedder = embedding_functions
        self.collections = {}
        for size in CHUNK_SIZES:
            search_ef = 100  # Default value
            if size == "256":
                search_ef = 200
            elif size == "128":
                search_ef = 400

            self.collections[size] = self.client.get_or_create_collection(
                name=f"{size}-sized_chunk",
                embedding_function=self.embedder,
                metadata={
                    "hnsw:space": "l2",
                    "hnsw:construction_ef": 100,
                    "hnsw:M": 16,
                    "hnsw:search_ef": search_ef
                })

    def get_collection(self, size: str):
        return self.collections[size]

    def close(self):
        pass


