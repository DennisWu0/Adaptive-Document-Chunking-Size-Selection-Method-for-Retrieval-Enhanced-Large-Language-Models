import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from dotenv import load_dotenv
from chromadb.utils import embedding_functions
from collections import Counter

from database.chromadb_manager import ChromaDBManager
from database.query_manager import QueryManager
# from select_chunks.selected_chunks import ChunkSelector
from select_chunks.test_new_v3 import ChunkProcessor
from chatbot.llm_ans import query_llm


# Load Google API Key
load_dotenv()
google_api_key = os.environ.get("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

# Initialize SentenceTransformerEmbeddingFunction once globally
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="nomic-ai/nomic-embed-text-v1",
    trust_remote_code=True
)

def process_query(query_text: str):
    print("Main function called")
    print(f"QUERY TEXT: {query_text}")

    # Initialize ChromaDB and Query Manager
    db_manager = ChromaDBManager(embedding_functions=embedding_fn)
    query_manager = QueryManager(chroma_client=db_manager.chroma_client)

    # Query documents from all collections
  
    retrieval_data = query_manager.query_from_all_collections(text=query_text)

    # Limit for each chunk size group
    chunk_limits = [9, 19, 39]
    target_lists = [[] for _ in chunk_limits]

    # Organize results by similarity score
    for chunk, target_list, limit in zip(retrieval_data, target_lists, chunk_limits):
        docs = chunk['documents'][0]
        dists = chunk['distances'][0]
        for doc, dist in list(zip(docs, dists))[:limit]:
            distance = query_manager.similarity_score([dist])
            target_list.append({'document': doc, 'distance': distance})

    # Helper functions to get LLM results from different chunk sizes
    def get_llm_results(chunk_index: int):
        docs = [item['document'] for item in target_lists[chunk_index]]
        return query_llm(relevant_chunks=docs, user_question=query_text)

    results_512 = get_llm_results(0)
    results_256 = get_llm_results(1)
    results_128 = get_llm_results(2)

    # Combine all results
    combined_result = query_manager.combine_query_results(retrieval_data=retrieval_data)
    # print(combined_result)
    # Select most relevant chunks
    try:
        # selector = ChunkSelector(combined_result, token_limit=5000)
        # selected_chunks = selector.process_chunks()
        # selector = ChunkProcessor(verbose=True)
        # selected_chunks = selector.main(combined_result, token_budget=5000)
        selector = ChunkProcessor(token_limit=5000)
        selected_chunks = selector.main(combined_result=combined_result)
        
        print(selected_chunks)
        # Count chunk_size occurrences
        chunk_sizes = [item['chunk_size'] for item in selected_chunks]
        counts = Counter(chunk_sizes)
        print(counts)
        total_chunk_size = sum(chunk_sizes)
        print(f"Total chunk size: {total_chunk_size}")
    except Exception as e:
        print(f"An error occurred: {e}")
        selected_chunks = []
    finally:
        db_manager.close()

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
    print(len(matched_results))

    relevant_chunks_dicts = sorted(
        [{'document': r['documents'], 'distance': r['distance']} for r in matched_results],
        key=lambda x: x['distance'],
        reverse=True
    )
    relevant_chunks = [r['documents'] for r in matched_results]
    # print(relevant_chunks)

    answers = query_llm(relevant_chunks=relevant_chunks, user_question=query_text)
    base_lines = [results_512, results_256, results_128]

    return answers, relevant_chunks_dicts, target_lists, base_lines

# if __name__ == '__main__':

#     def load_queries_from_json(filepath: str):
#         with open(filepath, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     read_json = load_queries_from_json("/home/dennis/workspace/adaptive_chunksize/dataset/natural_question.json")
#     queries = read_json["question"][:5]
#     for i in queries:
        
#     # queries = ["Why does Mrs. Hardcastle want Constance to marry her son?",
#     #     "Why did the couple visit medium Shaun San Dena in Pasadena in 1969?",
#     #     "After battling his desire for revenge, what does John do?",
#     #     "What gifts does Mulan accept from the Emperor?",
#     #     "What does the scientist suspect caused the outbreak?"]
  
#         answers, relevant_chunks_dicts, target_lists = process_query(query_text=i)
    
#         print("\nLLM ANSWER:")
#         print(answers)
#         print("====================================")
