import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from dotenv import load_dotenv
from chromadb.utils import embedding_functions

from database.chromadb_manager import ChromaDBManager
from database.query_manager import QueryManager
# from select_chunks.selected_chunks import ChunkSelector
from select_chunks.test_new_v3 import ChunkProcessor
import json

from experiment_gt_rd.mongdb import MongoDBClient
from dotenv import load_dotenv

from datetime import datetime, timezone
from bson import ObjectId
import requests


def process_query(query_text: str):
    print("Main function called")
    print(f"Query text: {query_text}")

    # Load Google API Key
    load_dotenv()
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    #  model_name="models/gemini-embedding-exp-03-07"

    # embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=google_api_key
    # embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    # model_name= "sentence-transformers/all-mpnet-base-v2")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="nomic-ai/nomic-embed-text-v1",
        trust_remote_code=True)
    # Initialize ChromaDB and Query Manager
    db_manager = ChromaDBManager(embedding_functions=embedding_fn)
    query_manager = QueryManager(chroma_client=db_manager.chroma_client)

    # Query documents from all collections
    # Format of retrieval_data including =['documents','metadatas','distances']
    retrieval_data = query_manager.query_from_all_collections(text=query_text)
    
    #   <=====================================>
    # Limit for each chunk size group
    # Based on the n_results_map = {'512': 100, '256': 200, '128': 400} it will fetch the the corresponded data
    # and store in a list of [ [], [], []]
    chunk_limits = [9, 19, 39]
    target_lists = [[] for _ in chunk_limits]

    # Organize results by similarity score
    for chunk, target_list, limit in zip(retrieval_data, target_lists, chunk_limits):
        docs = chunk['documents'][0]
        dists = chunk['distances'][0]
        for doc, dist in list(zip(docs, dists))[:limit]:
            distance = query_manager.similarity_score([dist])
            target_list.append({'document': doc, 'distance': distance})
    # print(target_lists)
    # print(len(target_lists))
    #  <=====================================>

    # # Helper functions to get LLM results from different chunk sizes
    # def get_llm_results(chunk_index: int):
    #     docs = [item['document'] for item in target_lists[chunk_index]]
    #     return query_llm(relevant_chunks=docs, user_question=query_text)

    # results_512 = get_llm_results(0)
    # results_256 = get_llm_results(1)
    # results_128 = get_llm_results(2)

    # Combine all results
    # Format:         
    # combined_result = {
        #     'ids': [[sorted_ids]],
        #     'embeddings': None,
        #     'documents': [[sorted_documents]],
        #     'metadatas': [[sorted_metadatas]],
        #     'distances': [[similarity_scores]]
        #     # 'distances': [[sorted_distances]]
        # }

    combined_result = query_manager.combine_query_results(retrieval_data=retrieval_data)

    # Select most relevant chunks
    try:
        selector = ChunkProcessor(token_limit=5000)
        selected_chunks = selector.main(combined_result=combined_result)
        # selector = ChunkProcessor(verbose=True)
        # selected_chunks = selector.main(combined_result, token_budget=5000)
        # print(selected_chunks)
        # print(len(selected_chunks))
    except Exception as e:
        print(f"An error occurred: {e}")
        selected_chunks = []
    finally:
        db_manager.close()

    # Match selected chunks back to full documents
    def find_matching_documents(selected_chunks, combined_result):
    # Build lookup dict for fast O(1) matching
        metadata_lookup = {}
        for i, metadata in enumerate(combined_result['metadatas'][0]):
            key = (metadata['chunk_level'], metadata['chunk_size'], metadata['ori_doc_title'], metadata['paragraph'])
            if key not in metadata_lookup:  # keep first occurrence only
                metadata_lookup[key] = {
                    'documents': combined_result['documents'][0][i],
                    'distance': combined_result['distances'][0][i],
                    'metadata': metadata
                }

        # Find matches using direct lookup
        matched_results = []
        for item in selected_chunks:
            key = (item['chunk_level'], item['chunk_size'], item['ori_doc_title'], item['paragraph'])
            if key in metadata_lookup:
                matched_results.append(metadata_lookup[key])
        
        return sorted(matched_results, key=lambda x: x['distance'], reverse=True)


    matched_results = find_matching_documents(selected_chunks, combined_result)
    # print(matched_results)
    # print(len(matched_results))
    # Actually relevant_chunks_dicts as the same with matched_results but a little adjust to fit with the interface
    # relevant_chunks_dicts = sorted(
    #     [{'document': r['documents'], 'distance': r['distance']} for r in matched_results],
    #     key=lambda x: x['distance'],
    #     reverse=True
    # )
    # print(len(relevant_chunks_dicts))
        
    seen = set()
    relevant_chunks_dicts = []
    for r in matched_results:
        key = (r['metadata']['chunk_level'],r['metadata']['chunk_size'], r['metadata']['ori_doc_title'], r['metadata']['paragraph'])
        if key not in seen:
            seen.add(key)
            relevant_chunks_dicts.append({'document': r['documents'], 'distance': r['distance']})

    relevant_chunks_dicts = sorted(relevant_chunks_dicts, key=lambda x: x['distance'], reverse=True)
    # print(relevant_chunks_dicts)
    # print(len(relevant_chunks_dicts))
    return relevant_chunks_dicts, target_lists


if __name__ == '__main__':


    def load_queries_from_json(filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    # read_json = load_queries_from_json("/home/dennis/workspace/adaptive_chunksize/dataset/narrativeqa.json")
    # queries = read_json["question"][:100]
    # for i in queries:
    #     relevant_chunks_dicts, target_lists = process_query(query_text=i)

    # def build_document(question, grounded_answer, chunks):
    #     """Helper to build a MongoDB document."""
    #     return {
    #         "_id": ObjectId(),
    #         "question": question,
    #         "grounded_answer": grounded_answer,
    #         "retrieved_chunks": [
    #             {"document": chunk["document"], "distance": chunk["distance"]}
    #             for chunk in chunks
    #         ],
    #         "created_at": datetime.now(timezone.utc)
        # }
    def build_document(question, grounded_answer, chunks): 
        """Helper to build a MongoDB document.""" 
        return { 
            "_id": ObjectId(), 
            "question": question, 
            "grounded_answer": grounded_answer, 
            "retrieved_chunks": [ 
                {"document": chunk["document"], 
                 "distance": chunk["distance"]} for chunk in chunks ], 
            "created_at": datetime.now(timezone.utc) 
            }
         
    def send_telegram_message(message: str):
        token = "8013643521:AAEncrdXp-Xii93zSaFpr4UlN1LIQXPo64I"
        chat_id = "1744072683"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        try:
            response = requests.post(url, data=payload)
            if response.status_code != 200:
                print("Failed to send Telegram message:", response.text)
        except Exception as e:
            print("Error sending Telegram message:", e)

    # Config
    MONGO_URI = "mongodb://localhost:27017/"
    COLLECTION_NAMES = ["512", "256", "128"]
    COLLECTION_NAMES_MY_METHOD = "our_method"
    # Test na and tri first cause the root problems from these two databases
    # MONGO_DB_NAMES = ["narrativeqa_mongo", "natural_question_mongo", "quac_mongo", "triviaqa_mongo"]
    MONGO_DB_NAMES = "quac_mongo" # need to change
    read_json = load_queries_from_json("/home/dennis/workspace/adaptive_chunksize/dataset/quac.json")
    # Load data
    queries = read_json["question"][:300]
    answers = read_json["answer"][:300]
    # Init Mongo client once
    mongo = MongoDBClient(uri=MONGO_URI, db_name=MONGO_DB_NAMES)

    for idx, query in enumerate(queries):
        relevant_chunks_dicts, target_lists = process_query(query_text=query)
        grounded_answer = answers[idx]

        # Save for "our method"
        mongo.insert_one(
            collection_name=COLLECTION_NAMES_MY_METHOD,
            document=build_document(query, grounded_answer, relevant_chunks_dicts)
        )


        for size_index, target_list in enumerate(target_lists):
            mongo.insert_one(
                collection_name=COLLECTION_NAMES[size_index],
                document=build_document(query, grounded_answer, target_list)
            )
    send_telegram_message("Done")