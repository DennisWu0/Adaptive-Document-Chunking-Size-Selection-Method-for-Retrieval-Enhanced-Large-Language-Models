import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.chromadb_manager import ChromaDBManager
# from select_chunks.selected_chunks import ChunkSelector
from select_chunks.test_new_v3 import ChunkProcessor
# from select_chunks.bk import select_chunks
from chromadb.utils import embedding_functions

from database.query_manager import QueryManager
from dotenv import load_dotenv
import json
import csv


def main():
    print("main function called")
    # 1. Initialize ChromaDB client
    load_dotenv()
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    # google_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=google_api_key)
    # google_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    #      api_key=google_api_key,
    #      model_name="models/text-embedding-004")
    google_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="nomic-ai/nomic-embed-text-v1",
        trust_remote_code=True)
    # Define CSV file path
    csv_path = os.environ.get("EXP_MM_PATH")
    # class MockEmbeddingFunction:
    #     def __call__(self, input):
    #         return [[0.0] * 768 for _ in input]

    # google_ef = MockEmbeddingFunction()

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

    # def find_matching_documents(selected_chunks, combined_result):
    #     matched_results = []
    #     for item in selected_chunks:
    #         for i, metadata in enumerate(combined_result['metadatas'][0]):
    #             if (
    #                 item['chunk_level'] == metadata['chunk_level'] and
    #                 item['ori_doc_title'] == metadata['ori_doc_title'] and
    #                 item['paragraph'] == metadata['paragraph'] and
    #                 item['chunk_size'] == metadata['chunk_size']
    #             ):
    #                 matched_results.append({
    #                     'documents': combined_result['documents'][0][i],
    #                     'distances': combined_result['distances'][0][i],
    #                     'metadata': metadata
    #                 })
    #     return matched_results if matched_results else []

    db_manager = ChromaDBManager(embedding_functions=google_ef)

    # 2. Initialize QueryManager
    query_manager = QueryManager(chroma_client=db_manager.chroma_client)

    

    # 3. Query from all collections
    # json_path = "/home/dennis/project/dynamic_chunks/dataset/narrativeqa.json"
    load_dotenv()
    json_path = os.environ.get("JSON_DIR")
    with open(json_path, 'r') as f:
                data = json.load(f)

    query_texts = data.get('question')

    # Write header if file does not exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Article Count", "512", "256", "128"])  # Column headers

    # Process and store results
    with open(csv_path, 'a', newline='') as file:
        writer = csv.writer(file)
        sum_articles = []
        for index, query_text in enumerate(query_texts, start=1):
            try:
                retrieval_data = query_manager.query_from_all_collections(text=query_text)
                combined_result = query_manager.combine_query_results(retrieval_data=retrieval_data)
                
                # i want to know how many articles it consider?
                unique_articles = set(entry['ori_doc_title'] for entry in combined_result['metadatas'][0])
                article_count = len(unique_articles)

                # selector = ChunkSelector(combined_result, 5000)
                # selected_chunks = selector.process_chunks()
                selector = ChunkProcessor(token_limit=5000)
                selected_chunks = selector.main(combined_result=combined_result)
                
                # Count similarity score
                matched_documents = find_matching_documents(selected_chunks, combined_result)
                total_similarity = sum(r['distance'] for r in matched_documents) if matched_documents else 0

                # Count unique articles
                unique_articles = set(entry['ori_doc_title'] for entry in selected_chunks)
                article_count = len(unique_articles)

               
                # # Count total occurrences of each chunk size
                count_512 = sum(1 for entry in selected_chunks if entry['chunk_size'] == 512)
                count_256 = sum(1 for entry in selected_chunks if entry['chunk_size'] == 256)
                count_128 = sum(1 for entry in selected_chunks if entry['chunk_size'] == 128)

            except Exception as e:
                print(f"Error processing query {index}: {e}")
                import traceback
                traceback.print_exc() # Print full traceback for debugging
                article_count, count_512, count_256, count_128, total_similarity = 0, 0, 0, 0, 0  # Store 0 if an error occurs

            finally:
                # Ensure db_manager.close() is called even if an error occurs
                # but only if db_manager was successfully initialized
                if 'db_manager' in locals() and db_manager:
                    db_manager.close()

            print(f"Processed query {index}: Articles={article_count}, 512={count_512}, 256={count_256}, 128={count_128}")
            writer.writerow([article_count, count_512, count_256, count_128, total_similarity])
    #         except Exception as e:
    #              print(f"Error on query {index}: {e}")
    #         sum_articles.append(article_count)

    # print(sum(sum_articles)/len(sum_articles))


if __name__ == "__main__":
    import os
    os.environ["GRPC_WAIT_FOR_SHUTDOWN_TIMEOUT"] = "60"  # Increase timeout to 60 seconds
    main()
