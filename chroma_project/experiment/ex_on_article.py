import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.chromadb_manager import ChromaDBManager
# from select_chunks.selected_chunks import ChunkSelector
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
    # google_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    #      api_key=google_api_key,
    #      model_name="models/text-embedding-004")
    google_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="nomic-ai/nomic-embed-text-v1",
        trust_remote_code=True)

    # google_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    # model_name="sentence-transformers/paraphrase-mpnet-base-v2")

    # Define CSV file path
    
    csv_path = os.environ.get("EXP_SMC_PATH")

    db_manager = ChromaDBManager(embedding_functions=google_ef)

    # 2. Initialize QueryManager
    query_manager = QueryManager(chroma_client=db_manager.chroma_client)
    
    # 3. Query from all collections
    load_dotenv()
    json_path = os.environ.get("JSON_DIR")
    # json_path = "/home/dennis/project/dynamic_chunks/dataset/narrativeqa.json"
    
    with open(json_path, 'r') as f:
                data = json.load(f)

    query_texts = data.get('question')

    # Define chunk sizes and corresponding n_results
    chunk_sizes = ['128', '256', '512']
    row_define = ['128', 'ss_128', '256', 'ss_256', '512','ss_512']

    n_results_map = {'128': 39, '256': 19, '512': 9}

    # Write header if file does not exist
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(row_define)  # Header only contains chunk sizes

    # Process and store results
    with open(csv_path, 'a', newline='') as file:
        writer = csv.writer(file)
        for index, query_text in enumerate(query_texts, start=1):
            row = []
            for size in chunk_sizes:
                query_result = query_manager.query_collections(size=size, text=query_text, n_results=n_results_map[size])
                # count similarity score
                distance = query_result["distances"][0]
                # transform to ss
                ss = query_manager.similarity_score(distance)
                ss_sum = sum(ss)
                metadata_list = query_result["metadatas"][0]
                unique_articles = set(entry['ori_doc_title'] for entry in metadata_list)
                article_count = len(unique_articles)
                row.append(article_count)
                row.append(ss_sum)

            print(f"Processed query {index}: {row}")
            writer.writerow(row)

if __name__ == "__main__":
    import os
    os.environ["GRPC_WAIT_FOR_SHUTDOWN_TIMEOUT"] = "60"  # Increase timeout to 60 seconds
    main()
