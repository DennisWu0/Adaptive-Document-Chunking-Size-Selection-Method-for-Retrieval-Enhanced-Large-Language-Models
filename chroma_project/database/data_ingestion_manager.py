import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.data_processing.sqlite_db import SQLiteDB

class DataIngestionManager:
    # transform the format of it like this one
    """Keys in data_by_sheet: dict_keys(['512', '256', '128'])

    Structure of data for key '512':
    {'id': <class 'str'>, 'document': <class 'str'>, 'metadata': <class 'dict'>}

    Structure of data for key '256':
    {'id': <class 'str'>, 'document': <class 'str'>, 'metadata': <class 'dict'>}

    Structure of data for key '128':
    {'id': <class 'str'>, 'document': <class 'str'>, 'metadata': <class 'dict'>}"""
    
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client


    # add a method to fetch data from sql db   
    def get_data_from_sql(self,db_path):
        # Connect to the SQLite database
        db = SQLiteDB(db_path)
        db.connect()
        cursor = db.conn.cursor()

        data_from_sql = {}
        chunk_sizes = [512, 256, 128]

        for chunk_size in chunk_sizes:
            data_name = f"chunks_{chunk_size}"
            cursor.execute(f"SELECT * FROM {data_name}")
            data = cursor.fetchall()
            
            data_list = []
            for row in data:
                data_list.append({
                    'id': row[0],
                    'document': row[1],
                    'metadata': {
                        'ori_doc_title': row[2],
                        'paragraph': row[3],
                        'chunk_size': row[4],
                        'chunk_level': row[5]
                    }
                })
            data_from_sql[str(chunk_size)] = data_list

        # Close the connection
        db.close()

        return data_from_sql

    # most use this method to add data from the sqlite database to the collection
    def add_to_collection(self, size: str, records: list):
        collection = self.chroma_client.get_collection(size)
        ids = [record["id"] for record in records]
        documents = [record["document"] for record in records]
        metadatas = [record["metadata"] for record in records]
        batch_size = 3000  # Or any other appropriate batch size
        for i in range(0, len(records), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            collection.add(
                ids=batch_ids,
                documents=batch_documents,
                metadatas=batch_metadatas
            )


    # beside, we need this oen to add into 3 collections[ for size, records in data_by_sheet.items():
#     chroma_manager.add_to_collection(size, records)]

    def update_document(self, doc_id: str, text: str, metadata: dict = None):
        # Assuming you have a way to access the collection here, e.g., through a default size or a lookup
        # You might need to adjust this based on how you want to handle updates across different chunk sizes
        # For simplicity, let's assume you have a default chunk size
        default_size = "512"  # Or any other default size
        collection = self.chroma_client.get_collection(default_size)
        collection.update(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}]
        )

    def delete_document(self, doc_id: str):
        # Similar to update_document, you might need to adjust this based on how you want to handle deletions
        # Let's assume you have a default chunk size for simplicity
        default_size = "512"  # Or any other default size
        collection = self.chroma_client.get_collection(default_size)
        collection.delete(ids=[doc_id])
