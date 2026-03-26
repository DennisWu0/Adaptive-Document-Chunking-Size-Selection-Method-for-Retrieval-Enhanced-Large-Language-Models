from pymongo import MongoClient, errors
from typing import Any, Dict, List, Optional


class MongoDBClient:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            # Trigger connection to check if MongoDB is reachable
            self.client.server_info()
        except errors.ServerSelectionTimeoutError as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")

    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> str:
        collection = self.db[collection_name]
        result = collection.insert_one(document)
        return str(result.inserted_id)

    def find(self, collection_name: str, filter: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        collection = self.db[collection_name]
        return list(collection.find(filter))

    def find_one(self, collection_name: str, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        collection = self.db[collection_name]
        return collection.find_one(filter)

    def update_one(self, collection_name: str, filter: Dict[str, Any], update: Dict[str, Any]) -> int:
        collection = self.db[collection_name]
        result = collection.update_one(filter, {"$set": update})
        return result.modified_count

    def delete_one(self, collection_name: str, filter: Dict[str, Any]) -> int:
        collection = self.db[collection_name]
        result = collection.delete_one(filter)
        return result.deleted_count

    def create_index(self, collection_name: str, field: str, unique: bool = False) -> str:
        collection = self.db[collection_name]
        return collection.create_index([(field, 1)], unique=unique)

    def close(self):
        if self.client:
            self.client.close()



