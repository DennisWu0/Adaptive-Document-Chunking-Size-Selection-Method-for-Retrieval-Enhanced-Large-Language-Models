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

    # def process_group(self, group_items):
    #     scores = {}
    #     for item in group_items:
    #         lvl = item['metadata'][0]['chunk_level']

    #         scores[lvl] = item['distance']

    #     kept = set()
    #     discarded = set()

    #     # Step 1: Compare 512 vs mean of children (256 + 128)
    #     if 1 in scores:
    #         children = []
    #         if 1 in self.hierarchy:
    #             for child in self.hierarchy[1]:
    #                 if child in scores:
    #                     children.append(child)

    #         if len(children) > 0:
    #             total = 0.0
    #             count = 0
    #             for c in children:
    #                 total += scores[c]
    #                 count += 1
    #             mean_children = total / count

    #             diff = scores[1] - mean_children
    #             if diff >= -0.005: # try 0.01 would be ok
    #                 kept.add(1)
    #                 for c in children:
    #                     discarded.add(c)
    #             else:
    #                 for c in children:
    #                     kept.add(c)
    #                 discarded.add(1)
    #         else:
    #             kept.add(1)

    #     # Step 2: Compare 256 vs mean of 128 children
    #     for parent256 in [2, 3]:
    #         if parent256 not in scores:
    #             continue

    #         children = []
    #         if parent256 in self.hierarchy:
    #             for child in self.hierarchy[parent256]:
    #                 if child in scores:
    #                     children.append(child)

    #         if len(children) == 0:
    #             kept.add(parent256)
    #             continue

    #         total = 0.0
    #         count = 0
    #         for c in children:
    #             total += scores[c]
    #             count += 1
    #         mean_children = total / count

    #         diff = scores[parent256] - mean_children
    #         if diff > -0.0075: # try 0.005 would be ok
    #             kept.add(parent256)
    #             for c in children:
    #                 discarded.add(c)
    #         else:
    #             for c in children:
    #                 kept.add(c)
    #             discarded.add(parent256)

    #     kept_items = [
    #         item for item in group_items
    #         if item['metadata'][0]['chunk_level'] in kept
    #     ]
    #     discarded_items = [
    #         item for item in group_items
    #         if item['metadata'][0]['chunk_level'] in discarded
    #     ]

    #     return {"kept": kept_items, "discarded": discarded_items}
    # 0.0025 0.005 0.0075 0.01 0.0125 0.015 0.0175
    def process_group(self, group_items, threshold=0.0025):
        scores = {}
        for item in group_items:
            lvl = item['metadata'][0]['chunk_level']
            scores[lvl] = item['distance']

        kept = set()
        discarded = set()

        # Step 1: Compare 256 vs mean of 128 children
        for parent256 in [2, 3]:
            if parent256 not in scores:
                continue

            children = []
            if parent256 in self.hierarchy:
                for child in self.hierarchy[parent256]:
                    if child in scores:
                        children.append(child)

            if len(children) == 0:
                kept.add(parent256)
                continue

            total = 0.0
            count = 0
            for c in children:
                total += scores[c]
                count += 1
            mean_children = total / count

            diff = scores[parent256] - mean_children
            if diff > -threshold: 
                kept.add(parent256)
                for c in children:
                    discarded.add(c)
            else:
                for c in children:
                    kept.add(c)
                discarded.add(parent256)

        # Step 2: Compare 512 vs mean of children (256 + 128)
        if 1 in scores:
            children = []
            if 1 in self.hierarchy:
                for child in self.hierarchy[1]:
                    if child in scores and child in kept:
                        children.append(child)

            if len(children) > 0:
                total = 0.0
                count = 0
                for c in children:
                    total += scores[c]
                    count += 1
                mean_children = total / count

                diff = scores[1] - mean_children
                if diff >= 2*threshold: 
                    kept.add(1)
                    for c in children:
                        discarded.add(c)
                else:
                    for c in children:
                        kept.add(c)
                    discarded.add(1)
            else:
                kept.add(1)

        kept_items = [
            item for item in group_items
            if item['metadata'][0]['chunk_level'] in kept
        ]
        discarded_items = [
            item for item in group_items
            if item['metadata'][0]['chunk_level'] in discarded
        ]

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

    # def control_token_list(self, kept_items, discarded_items=None):
    #     """Token control with recovery from discarded pool."""
    #     result, total_tokens = [], 0

    #     # Step 1: sort kept by similarity (higher first)
    #     kept_sorted = sorted(kept_items, key=lambda x: x['distance'], reverse=True)

    #     for item in kept_sorted:
    #         size = item["metadata"][0]["chunk_size"]
    #         if self.token_limit and total_tokens + size > self.token_limit:
    #             continue
    #         result.append(self.flatten_item(item))
    #         total_tokens += size

    #     # Step 2: recovery phase if tokens are under-utilized
    #     if discarded_items and total_tokens < 0.99 * self.token_limit:
    #         disc_sorted = sorted(discarded_items, key=lambda x: (x['distance'], -x["metadata"][0]["chunk_size"]), reverse=True)
    #         for item in disc_sorted:
    #             size = item["metadata"][0]["chunk_size"]
    #             if self.token_limit and total_tokens + size > self.token_limit:
    #                 continue
    #             result.append(self.flatten_item(item))
    #             total_tokens += size
    #             if total_tokens >= self.token_limit:
    #                 break

    #     return result
    def control_token_list(self, kept_items, discarded_items=None):
        result, total_tokens = [], 0

        # Step 1: sort kept by similarity (higher first)
        kept_sorted = sorted(kept_items, key=lambda x: x['distance'], reverse=True)

        for item in kept_sorted:
            size = item["metadata"][0]["chunk_size"]
            if self.token_limit and total_tokens + size > self.token_limit:
                continue
            result.append(self.flatten_item(item))
            total_tokens += size

        # Step 2: recovery phase from discarded
        pool = discarded_items if discarded_items else []
        pool_sorted = sorted(pool, key=lambda x: (x['distance'], -x["metadata"][0]["chunk_size"]), reverse=True)

        # Try to fill remaining space as much as possible
        filled = True
        while filled and total_tokens < self.token_limit:
            filled = False
            for item in pool_sorted:
                size = item["metadata"][0]["chunk_size"]
                if total_tokens + size <= self.token_limit and self.flatten_item(item) not in result:
                    result.append(self.flatten_item(item))
                    total_tokens += size
                    filled = True
                    break  # restart loop to always try best fit again

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
