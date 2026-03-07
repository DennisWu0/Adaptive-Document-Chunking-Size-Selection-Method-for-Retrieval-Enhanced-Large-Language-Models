# from .chromadb_client import ChromaDBClient
# from .data_ingestion_manager import DataIngestionManager
# from .query_manager import QueryManager
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from chromadb_client import ChromaDBClient
from data_ingestion_manager import DataIngestionManager
from query_manager import QueryManager


class ChromaDBManager:
    def __init__(self, embedding_functions):
        self.chroma_client = ChromaDBClient(embedding_functions)
        self.data_ingestion_manager = DataIngestionManager(self.chroma_client)
        self.query_manager = QueryManager(self.chroma_client)

    def add_to_collection(self, size: str, records: list):
        self.data_ingestion_manager.add_to_collection(size, records)

    def update_document(self, doc_id: str, text: str, metadata: dict = None):
        self.data_ingestion_manager.update_document(doc_id, text, metadata)

    def delete_document(self, doc_id: str):
        self.data_ingestion_manager.delete_document(doc_id)

    def query_collections(self, size: str, text: str, n_results: int):
        return self.query_manager.query_collections(size, text, n_results)
    
    def query_from_all_collections(self, text: str, n_results: int):
        return self.query_manager.query_from_all_collections(text, n_results)
        
    def combine_query_results(self, retrieval_data):
        return self.query_manager.combine_query_results(retrieval_data)
    

    def close(self):
        try:
            self.chroma_client.close()
        except Exception as e:
            print(f"An error occurred while closing ChromaDB client: {e}")

