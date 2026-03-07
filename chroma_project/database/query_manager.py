
CHUNK_SIZES = ["512", "256", "128"]
import math

class QueryManager:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client

    # def similarity_score(self, distances):
    #     return [1 - d for d in distances]
    # def similarity_score(self, distances):
    #     return [1.0 - d/2.0 for d in distances]

    def similarity_score(self, distances: float) -> float:
        return [1.0 - distance / 2 for distance in distances]
    # def similarity_score(self,distances):
    #     """
    #     Remap a distance-squared value in the range of [0, 4] to a relevance score
    #     in the range of [1, 0]
    #     """
    #     return [1.0 - math.sqrt(d) / 2 for d in distances]


    def query_collections(self, size: str, text: str, n_results: int):
        collection = self.chroma_client.get_collection(size)
        results = collection.query(query_texts=[text], 
                                   n_results=n_results,
                                   include=['documents','metadatas','distances'])
        return results
    
    def query_from_all_collections(self, text: str):
        retrieval_data = []
        n_results_map = {'512': 100, '256': 200, '128': 400}
        for i in CHUNK_SIZES:
            query_collection = self.query_collections(i, text, n_results=n_results_map[i])
            retrieval_data.append(query_collection)
        
        # print("retrieval_data:", retrieval_data)
        return retrieval_data
        
    # 700 chunks
    def combine_query_results(self, retrieval_data):
        # print("retrieval_data:", retrieval_data)
        combined_ids = []
        combined_documents = []
        combined_metadatas = []
        combined_distances = []

        for result in retrieval_data:
            combined_ids.extend(result['ids'][0])
            combined_documents.extend(result['documents'][0])
            combined_metadatas.extend(result['metadatas'][0])
            combined_distances.extend(result['distances'][0])

        # Create a list of tuples (distance, index)
        distance_index_pairs = list(enumerate(combined_distances))

        # Sort the list of tuples in ascending order based on distance
        distance_index_pairs.sort(key=lambda x: x[1], reverse=False)

        # Create new lists based on the sorted order
        sorted_ids = [combined_ids[i] for i, _ in distance_index_pairs]
        sorted_documents = [combined_documents[i] for i, _ in distance_index_pairs]
        sorted_metadatas = [combined_metadatas[i] for i, _ in distance_index_pairs]
        sorted_distances = [combined_distances[i] for i, _ in distance_index_pairs]
        similarity_scores = self.similarity_score(sorted_distances)

        combined_result = {
            'ids': [sorted_ids],
            'embeddings': None,
            'documents': [sorted_documents],
            'metadatas': [sorted_metadatas],
            'distances': [similarity_scores]
            # 'distances': [sorted_distances]
        }

        return combined_result
