import json
from collections import defaultdict
from typing import Dict, List


class ChunkProcessor:
    def __init__(self,token_limit=None):
        # Define hierarchy tree
        self.token_limit = token_limit
        self.hierarchy = {
            1: [2, 3],
            2: [4, 5],
            3: [6, 7],
            4: [],
            5: [],
            6: [],
            7: []
        }

    def is_subset(self, parent_block, child_block):
        """Check if child_block is a direct child of parent_block."""
        if parent_block not in self.hierarchy:
            return False
        return child_block in self.hierarchy[parent_block]

    def get_level(self, block):
        """Find the depth level of a block in the hierarchy."""
        level = 1
        current_level_blocks = [1]

        while len(current_level_blocks) > 0:
            if block in current_level_blocks:
                return level

            next_level_blocks = []
            for b in current_level_blocks:
                if b in self.hierarchy:
                    children = self.hierarchy[b]
                    for child in children:
                        next_level_blocks.append(child)

            current_level_blocks = next_level_blocks
            level += 1

        return None

    def highest_level_with_count(self, group_blocks):
        """Find highest level (lowest depth number) and its count in group."""
        level_list = []
        for block in group_blocks:
            level_list.append(self.get_level(block))

        highest_level = min(level_list)
        count_highest = level_list.count(highest_level)
        return highest_level, count_highest

    def group_chunks(self, combined_result):
        """Group chunks by (ori_doc_title, paragraph)."""
        groups = defaultdict(list)
        
        ids = combined_result['ids'][0]
        metadatas = combined_result['metadatas'][0]
        distances = combined_result['distances'][0]
        documents = combined_result['documents'][0]

        for i in range(len(ids)):
            meta = metadatas[i]
            if isinstance(meta, str):
                meta = json.loads(meta)
            
            item = {
                'id': ids[i],
                'metadata': [meta],
                'distance': distances[i], # Assuming distance is convertible to similarity
                'document': documents[i]
            }
            
            key = (meta['ori_doc_title'], meta['paragraph'])
            groups[key].append(item)
            
        return groups

    def process_group(self, group_items) -> Dict[str, List[dict]]:
        """Apply hierarchical similarity-based filtering rules to one group."""

        # Build a dict of {chunk_level: similarity_score}
        scores = {}
        for item in group_items:
            chunk_level = item['metadata'][0]['chunk_level']
            similarity_score = item['distance']
            scores[chunk_level] = similarity_score

        kept = set()
        discarded = set()

        # Step 1: Evaluate 512 (root)
        if 1 in scores:
            score_512 = scores[1]
            highest_other_score = float("-inf")
            for key, score in scores.items():
                if key != 1 and score > highest_other_score:
                    highest_other_score = score

            difference = score_512 - highest_other_score

            if difference >= -0.015:
                kept = {1}
                discarded = {lvl for lvl in scores if lvl != 1}
                kept_items = [item for item in group_items if item['metadata'][0]['chunk_level'] in kept]
                discarded_items = [item for item in group_items if item['metadata'][0]['chunk_level'] in discarded]
                return {"kept": kept_items, "discarded": discarded_items}
            # else:
            #     discarded.add(1)

        # Step 2: Evaluate 256 parents independently
        for parent256 in [2, 3]:
            if parent256 not in scores:
                continue

            score_256 = scores[parent256]
            children = []

            if parent256 in self.hierarchy:
                for child in self.hierarchy[parent256]:
                    if child in scores:
                        children.append(child)

            if len(children) == 0:
                kept.add(parent256)
                continue

            max_child_score = max(scores[c] for c in children)
            diff = score_256 - max_child_score

            if diff > -0.005:
                kept.add(parent256)
                for child in children:
                    discarded.add(child)
            else:
                total = 0.0
                for c in children:
                    total += scores[c]
                mean_child_score = total / len(children)
                diff2 = score_256 - mean_child_score

                if diff2 < -0.01:
                    for c in children:
                        kept.add(c)
                    discarded.add(parent256)
                elif diff2 >= -0.01 and diff2 <= -0.005:
                    kept.add(parent256)
                    for c in children:
                        discarded.add(c)
                else:
                    kept.add(parent256)
                    for c in children:
                        kept.add(c)

        # Step 3: Re-check 512 if it was discarded
        pattern_a = {1, 2, 6, 7}
        pattern_b = {1, 3, 4, 5}

        if kept == pattern_a or kept == pattern_b:
            # 512 exists in scores but might have been discarded earlier
            if 1 in scores and 1 not in kept:
                remaining_scores = []
                for c in kept:
                    if c != 1:
                        remaining_scores.append(scores[c])

                if len(remaining_scores) > 0:
                    mean_rest = sum(remaining_scores) / len(remaining_scores)
                    diff3 = scores[1] - mean_rest

                    # if 512 is close enough to mean of children
                    if -0.0025 <= diff3 < -0.002:
                        kept = {1}  # override → keep 512, discard children

        # # Final return: keep only surviving items
        # final_items = []
        # for item in group_items:
        #     chunk_level = item['metadata'][0]['chunk_level']
        #     if chunk_level in kept:
        #         final_items.append(item)

        # return final_items
                # Build return
        kept_items = [i for i in group_items if i['metadata'][0]['chunk_level'] in kept]
        discarded_items = [i for i in group_items if i['metadata'][0]['chunk_level'] not in kept]
        return {"kept": kept_items, "discarded": discarded_items}

    
    # def control_token_list(self, processed_group):
    #     if not processed_group:
    #         return []
        
    #     # Flatten chunks into simpler form
    #     chunks = [{
    #         'chunk_level': item["metadata"][0]["chunk_level"],
    #         'chunk_size': item["metadata"][0]["chunk_size"],
    #         'ori_doc_title': item["metadata"][0]["ori_doc_title"],
    #         'paragraph': item["metadata"][0]["paragraph"],
    #         'distance': item["distance"]
    #     } for item in processed_group]

    #     # Sort by relevance (distance ascending)
    #     chunks.sort(key=lambda x: x['distance'])

    #     # Extract sizes
    #     sizes = [c['chunk_size'] for c in chunks]
    #     n = len(sizes)
    #     limit = self.token_limit

    #     # DP table: dp[i][t] = max total tokens achievable with first i items and limit t
    #     dp = [[0]*(limit+1) for _ in range(n+1)]

    #     for i in range(1, n+1):
    #         size = sizes[i-1]
    #         for t in range(1, limit+1):
    #             if size <= t:
    #                 dp[i][t] = max(dp[i-1][t], dp[i-1][t-size] + size)
    #             else:
    #                 dp[i][t] = dp[i-1][t]

    #     best_total = dp[n][limit]

    #     # Backtrack to find chosen chunks
    #     chosen = []
    #     t = limit
    #     for i in range(n, 0, -1):
    #         if dp[i][t] != dp[i-1][t]:
    #             chosen.append(chunks[i-1])
    #             t -= sizes[i-1]

    #     return chosen

    def control_token_list(self, kept_items, discarded_items=None):
        """Token control with recovery from discarded pool."""
        result, total_tokens = [], 0

        # Step 1: sort kept by similarity (higher first)
        kept_sorted = sorted(kept_items, key=lambda x: x['distance'], reverse=True)

        for item in kept_sorted:
            size = item["metadata"][0]["chunk_size"]
            if self.token_limit and total_tokens + size > self.token_limit:
                continue
            result.append(self.flatten_item(item))
            total_tokens += size

        # Step 2: recovery phase if tokens are under-utilized
        if discarded_items and total_tokens < 0.99 * self.token_limit:
            disc_sorted = sorted(discarded_items, key=lambda x: (x['distance'], -x["metadata"][0]["chunk_size"]), reverse=True)
            for item in disc_sorted:
                size = item["metadata"][0]["chunk_size"]
                if self.token_limit and total_tokens + size > self.token_limit:
                    continue
                result.append(self.flatten_item(item))
                total_tokens += size
                if total_tokens >= self.token_limit:
                    break

        return result

    def flatten_item(self, item):
        return {
            'chunk_level': item["metadata"][0]["chunk_level"],
            'chunk_size': item["metadata"][0]["chunk_size"],
            'ori_doc_title': item["metadata"][0]["ori_doc_title"],
            'paragraph': item["metadata"][0]["paragraph"],
            'distance': item["distance"]
        }

    def main(self, combined_result):
        k = min(150, len(combined_result['ids'][0])) 
        limited_result = {
            'ids': [combined_result['ids'][0][:k]],
            'documents': [combined_result['documents'][0][:k]],
            'metadatas': [combined_result['metadatas'][0][:k]],
            'distances': [combined_result['distances'][0][:k]]
        }

        grouped = self.group_chunks(limited_result)
        kept_all, discarded_all = [], []
        for _, items in grouped.items():
            processed = self.process_group(items)
            kept_all.extend(processed["kept"])
            discarded_all.extend(processed["discarded"])

        final_result = self.control_token_list(kept_all, discarded_all)
        # Ensure the final return is sorted by distance from high to low
        final_result_sorted = sorted(final_result, key=lambda x: x['distance'], reverse=True)
        return final_result_sorted
    

# if __name__ == "__main__":
#     processor= ChunkProcessor(token_limit=1000)
#     # Test Case 1: Simple 512 vs children
#     print("Test Case 1")
#     combined_result_1 = {
#         'ids': ['id1', 'id2', 'id3'],
#         'documents': [['Content A', 'Content B', 'Content C']],
#         'metadatas': [[
#             {'ori_doc_title': 'Doc1', 'paragraph': 1, 'chunk_level': 1, 'chunk_size': 512},
#             {'ori_doc_title': 'Doc1', 'paragraph': 1, 'chunk_level': 2, 'chunk_size': 256},
#             {'ori_doc_title': 'Doc1', 'paragraph': 1, 'chunk_level': 4, 'chunk_size': 128}
#         ]],
#         'distances': [[0.30, 0.25, 0.15]]  # similarity scores
#     }

#     result1 = processor.main(combined_result_1)
#     print(f"Result: {len(result1)} items")
#     for i, item in enumerate(result1): # Changed 'meta' to 'item'
#         print(f"  {i+1}. Doc: {item.get('ori_doc_title')}, Para: {item.get('paragraph')}, Level: {item.get('chunk_level')}, Size: {item.get('chunk_size')}") # Corrected access
#         print(item.get('distance')) # Corrected access

#     print()

#     # Test Case 2: 512 discarded, check 256 vs 128
#     print("Test Case 2")

#     combined_result_2 = {
#         'ids': ['id1', 'id2', 'id3', 'id4'],
#         'documents': [['Doc A', 'Doc B', 'Doc C', 'Doc D']],
#         'metadatas': [[
#             {'ori_doc_title': 'Doc2', 'paragraph': 1, 'chunk_level': 2, 'chunk_size': 256},
#             {'ori_doc_title': 'Doc2', 'paragraph': 1, 'chunk_level': 4, 'chunk_size': 128},
#             {'ori_doc_title': 'Doc2', 'paragraph': 1, 'chunk_level': 5, 'chunk_size': 128},
#             {'ori_doc_title': 'Doc2', 'paragraph': 1, 'chunk_level': 3, 'chunk_size': 256}
#         ]],
#         'distances': [[0.11, 0.18, 0.16, 0.20]]  # similarity scores
#     }
#     result2 = processor.main(combined_result_2)
#     print(f"Result: {len(result2)} items")
#     for i, item in enumerate(result2): # Changed 'meta' to 'item'
#         print(f"  {i+1}. Doc: {item.get('ori_doc_title')}, Para: {item.get('paragraph')}, Level: {item.get('chunk_level')}, Size: {item.get('chunk_size')}") # Corrected access
#         print(item.get('distance')) # Corrected access

#     print()
#     # Test Case 3: Mixed paragraphs, re-check 512 pattern {1,2,6,7}
#     print("Test Case 3")

#     combined_result_3 = {
#         'ids': ['id1','id2','id3','id4'],
#         'documents': [['Doc A','Doc B','Doc C','Doc D']],
#         'metadatas': [[
#             {'ori_doc_title': 'Doc3', 'paragraph': 1, 'chunk_level': 1, 'chunk_size': 512},
#             {'ori_doc_title': 'Doc3', 'paragraph': 1, 'chunk_level': 2, 'chunk_size': 256},
#             {'ori_doc_title': 'Doc3', 'paragraph': 1, 'chunk_level': 6, 'chunk_size': 128},
#             {'ori_doc_title': 'Doc3', 'paragraph': 1, 'chunk_level': 7, 'chunk_size': 128}
#         ]],
#         'distances': [[0.18, 0.16, 0.14, 0.15]]
#     }
#     result3 = processor.main(combined_result_3)
#     print(f"Result: {len(result3)} items")
#     for i, item in enumerate(result3): # Changed 'meta' to 'item'
#         print(f"  {i+1}. Doc: {item.get('ori_doc_title')}, Para: {item.get('paragraph')}, Level: {item.get('chunk_level')}, Size: {item.get('chunk_size')}") # Corrected access
#         print(item.get('distance')) # Corrected access

#     print()
#     # Test Case 4: Multiple 256 chunks, some children overlap
#     print("Test Case 4")
#     combined_result_4 = {
#         'ids': ['id1','id2','id3','id4','id5','id6'],
#         'documents': [['C1','C2','C3','C4','C5','C6']],
#         'metadatas': [[
#             {'ori_doc_title':'Doc4','paragraph':1,'chunk_level':2,'chunk_size':256},
#             {'ori_doc_title':'Doc4','paragraph':1,'chunk_level':4,'chunk_size':128},
#             {'ori_doc_title':'Doc4','paragraph':1,'chunk_level':5,'chunk_size':128},
#             {'ori_doc_title':'Doc4','paragraph':2,'chunk_level':3,'chunk_size':256},
#             {'ori_doc_title':'Doc4','paragraph':2,'chunk_level':6,'chunk_size':128},
#             {'ori_doc_title':'Doc4','paragraph':2,'chunk_level':7,'chunk_size':128}
#         ]],
#         'distances': [[0.20, 0.18, 0.17, 0.11, 0.23, 0.16]]
#     }
#     result4 = processor.main(combined_result_4)
#     print(f"Result: {len(result4)} items")
#     for i, item in enumerate(result4): # Changed 'meta' to 'item'
#         print(f"  {i+1}. Doc: {item.get('ori_doc_title')}, Para: {item.get('paragraph')}, Level: {item.get('chunk_level')}, Size: {item.get('chunk_size')}") # Corrected access
#         print(item.get('distance')) # Corrected access

#     print()

#     # Test Case 5: Token limit scenario
#     print("Test Case 5")
#     combined_result_5 = {
#         'ids': [f'id{i}' for i in range(1, 21)],
#         'documents': [['Doc']*20],
#         'metadatas': [[
#             {'ori_doc_title':'Doc5','paragraph':1,'chunk_level':4,'chunk_size':128} for _ in range(20)
#         ]],
#         'distances': [[0.10 for _ in range(20)]]
#     }

#     result5 = processor.main(combined_result_5)
#     print(f"Result: {len(result5)} items")
#     for i, item in enumerate(result5): # Changed 'meta' to 'item'
#         print(f"  {i+1}. Doc: {item.get('ori_doc_title')}, Para: {item.get('paragraph')}, Level: {item.get('chunk_level')}, Size: {item.get('chunk_size')}") # Corrected access
#         print(item.get('distance')) # Corrected access

#     print()
