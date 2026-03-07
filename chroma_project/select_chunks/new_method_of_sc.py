from collections import defaultdict
from typing import Any, Dict, List
import json


class ChunkProcessor:
    def __init__(self, hierarchy: Dict[int, List[int]] = None, verbose: bool = False):
        # default hierarchy (can be overridden)
        self.hierarchy = hierarchy or {
            1: [2, 3],
            2: [4, 5],
            3: [6, 7],
            4: [],
            5: [],
            6: [],
            7: []
        }
        self.verbose = verbose

    def is_descendant(self, parent_block: int, child_block: int) -> bool:
        """Return True if child_block is a descendant (any depth) of parent_block.
           parent_block == child_block => False (not considered a descendant)."""
        if parent_block == child_block:
            return False
        stack = list(self.hierarchy.get(parent_block, []))
        while stack:
            node = stack.pop()
            if node == child_block:
                return True
            stack.extend(self.hierarchy.get(node, []))
        return False

    def get_level(self, block: int) -> int:
        """Return the level(depth) of a block: 1 for root, 2 for its children, ...
           If not found, returns None."""
        if block is None:
            return None
        level = 1
        current = [1]
        while current:
            if block in current:
                return level
            next_level = []
            for b in current:
                next_level.extend(self.hierarchy.get(b, []))
            current = next_level
            level += 1
        return None

    def top_level_with_count(self, blocks: List[int]):
        """Return the shallowest (top) level and how many blocks are at that level."""
        level_list = [self.get_level(b) for b in blocks if b is not None]
        if not level_list:
            return None, 0
        top_level = min(level_list)       # <<-- use min (shallowest), not max
        return top_level, level_list.count(top_level)

    def parse_metadata(self, metadata_item):
        """Parse metadata item - it could be a string (JSON) or already a dict."""
        if isinstance(metadata_item, str):
            try:
                return json.loads(metadata_item)
            except json.JSONDecodeError:
                return {}
        elif isinstance(metadata_item, dict):
            return metadata_item
        else:
            return {}

    def flatten_combined_result(self, combined_result: Dict[str, List]):
        """Convert the new format to individual items."""
        items = []
        
        ids = combined_result.get('ids', [])
        documents = combined_result.get('documents', [[]])
        metadatas = combined_result.get('metadatas', [[]])
        distances = combined_result.get('distances', [[]])
        
        # Handle the case where we have nested lists
        if documents and isinstance(documents[0], list):
            docs_flat = documents[0]
        else:
            docs_flat = documents
            
        if metadatas and isinstance(metadatas[0], list):
            metas_flat = metadatas[0]
        else:
            metas_flat = metadatas
            
        if distances and isinstance(distances[0], list):
            dists_flat = distances[0]
        else:
            dists_flat = distances
        
        # Create individual items
        for i in range(len(docs_flat)):
            item = {
                'id': ids[i] if i < len(ids) else None,
                'document': docs_flat[i] if i < len(docs_flat) else '',
                'metadata': [self.parse_metadata(metas_flat[i])] if i < len(metas_flat) else [{}],
                'distances': [dists_flat[i]] if i < len(dists_flat) else [float('inf')]
            }
            items.append(item)
        
        return items

    def group_chunks(self, items: List[Dict[str, Any]]):
        """Group items by document title and paragraph."""
        groups = defaultdict(list)
        for item in items:
            meta_list = item.get('metadata', [])
            if not meta_list:
                continue
            meta0 = meta_list[0]
            key = (meta0.get('ori_doc_title'), meta0.get('paragraph'))
            groups[key].append(item)
        return groups

    def get_item_level(self, item: Dict[str, Any]) -> int:
        """Get the level of an item from its metadata."""
        meta_list = item.get('metadata', [])
        if not meta_list:
            return None
        return self.get_level(meta_list[0].get('chunk_level'))

    def get_distance(self, item: Dict[str, Any]):
        """Get the distance of an item."""
        d = item.get('distances', [])
        if isinstance(d, list) and d:
            try:
                return float(d[0])
            except Exception:
                return float('inf')
        return float('inf')

    def process_group(self, items: List[Dict[str, Any]]):
        """Process a group of items with the same document title and paragraph."""
        # collect block ids from items
        block_ids = []
        for it in items:
            meta_list = it.get('metadata', [])
            if meta_list:
                block_ids.append(meta_list[0].get('chunk_level'))

        top_level, count_top = self.top_level_with_count(block_ids)
        if top_level is None:
            return items

        parents = [it for it in items if self.get_item_level(it) == top_level]
        deeper = [it for it in items if (lvl := self.get_item_level(it)) is not None and lvl > top_level]


        # If the top (shallowest) level is 1 --> keep only ONE level-1 item (choose by distance)
        if top_level == 1:
            if not parents:
                return []
            # choose the best parent (lowest distance), then discard any deeper items that are descendants
            chosen_parent = min(parents, key=self.get_distance)
            result = [chosen_parent]
            parent_block = chosen_parent.get('metadata', [{}])[0].get('chunk_level')
            for child in deeper:
                child_block = child.get('metadata', [{}])[0].get('chunk_level')
                if not self.is_descendant(parent_block, child_block):
                    # keep deeper child only if it's NOT a descendant of chosen parent
                    result.append(child)
            return result

        # If top level >= 2: keep all parents, discard deeper items that are descendants of any parent
        result = parents.copy()
        parent_blocks = [(p, p.get('metadata', [{}])[0].get('chunk_level')) for p in parents]
        for child in deeper:
            child_block = child.get('metadata', [{}])[0].get('chunk_level')
            # discard child if it is descendant of any parent
            if any(self.is_descendant(pb, child_block) for _, pb in parent_blocks):
                continue
            result.append(child)
        return result

    def main(self, combined_result, token_budget=None):
        """Main processing function that handles the new combined_result format."""
        # Step 1: Flatten the new format into individual items
        items = self.flatten_combined_result(combined_result)
        items = items[:250]
        
        # Step 2: Group & filter
        grouped = self.group_chunks(items)
        processed_results = []
        for _, group_items in grouped.items():
            processed_results.extend(self.process_group(group_items))

        # Step 3: Sort by distance (lowest distance first - best matches first)
        processed_results.sort(key=lambda x: x['distances'][0])

        # # Step 4: Apply token budget if provided
        # final_list = []
        # if token_budget is not None:
        #     total_tokens = 0
        #     for item in processed_results:
        #         meta = item['metadata'][0]
        #         chunk_size = meta.get('chunk_size', 0)
        #         if total_tokens + chunk_size <= token_budget:
        #             final_list.append(meta)  # store only metadata
        #             total_tokens += chunk_size
        #         else:
        #             break
        # else:
        #     final_list = [item['metadata'][0] for item in processed_results]
        if token_budget is not None:
            total_tokens = 0
            remaining_items = processed_results.copy()
            final_list = []

            while remaining_items:
                # Pick the largest chunk that still fits in the budget
                fitting_chunks = [it for it in remaining_items 
                                if total_tokens + it['metadata'][0].get('chunk_size', 0) <= token_budget]
                if not fitting_chunks:
                    break
                best_chunk = max(fitting_chunks, key=lambda it: it['metadata'][0].get('chunk_size', 0))
                
                final_list.append(best_chunk['metadata'][0])
                total_tokens += best_chunk['metadata'][0].get('chunk_size', 0)
                remaining_items.remove(best_chunk)

        # Count chunk sizes
        chunk_counts = {512: 0, 256: 0, 128: 0}
        for item in final_list:
            size = item.get('chunk_size')
            if size in chunk_counts:
                chunk_counts[size] += 1
        
        print(f"CHUNK COUNTS: 512={chunk_counts[512]}, 256={chunk_counts[256]}, 128={chunk_counts[128]}")
        print(f"TOTAL CHUNKS: {512 * chunk_counts[512] + 256 * chunk_counts[256] + 128 * chunk_counts[128]}")
        return final_list



# # Test Cases
# def test_chunk_processor():
#     print("=== Testing ChunkProcessor ===\n")
    
#     # Test Case 1: Basic functionality with hierarchy filtering
#     print("Test Case 1: Basic hierarchy filtering")
#     processor = ChunkProcessor(verbose=True)
    
#     # Create test data in the new format
#     combined_result_1 = {
#         'ids': ['id1', 'id2', 'id3', 'id4', 'id5'],
#         'documents': [['Document 1 content', 'Document 2 content', 'Document 3 content', 'Document 4 content', 'Document 5 content']],
#         'metadatas': [[
#             {
#                 'ori_doc_title': 'TestDoc1',
#                 'paragraph': 1,
#                 'chunk_level': 1,
#                 'chunk_size': 100
#             },
#             {
#                 'ori_doc_title': 'TestDoc1',
#                 'paragraph': 1,
#                 'chunk_level': 2,
#                 'chunk_size': 80
#             },
#             {
#                 'ori_doc_title': 'TestDoc1',
#                 'paragraph': 1,
#                 'chunk_level': 4,
#                 'chunk_size': 60
#             },
#             {
#                 'ori_doc_title': 'TestDoc2',
#                 'paragraph': 1,
#                 'chunk_level': 3,
#                 'chunk_size': 90
#             },
#             {
#                 'ori_doc_title': 'TestDoc2',
#                 'paragraph': 1,
#                 'chunk_level': 6,
#                 'chunk_size': 70
#             }
#         ]],
#         'distances': [[0.1, 0.3, 0.5, 0.2, 0.4]]
#     }
    
#     result1 = processor.main(combined_result_1)
#     print(f"Result: {len(result1)} items")
#     for i, meta in enumerate(result1):
#         print(f"  {i+1}. Doc: {meta.get('ori_doc_title')}, Level: {meta.get('chunk_level')}, Size: {meta.get('chunk_size')}")
#     print()

#     # Test Case 2: With token budget
#     print("Test Case 2: With token budget (150 tokens)")
#     result2 = processor.main(combined_result_1, token_budget=150)
#     total_tokens = sum(meta.get('chunk_size', 0) for meta in result2)
#     print(f"Result: {len(result2)} items, Total tokens: {total_tokens}")
#     for i, meta in enumerate(result2):
#         print(f"  {i+1}. Doc: {meta.get('ori_doc_title')}, Level: {meta.get('chunk_level')}, Size: {meta.get('chunk_size')}")
#     print()

#     # Test Case 3: JSON string metadata
#     print("Test Case 3: JSON string metadata")
#     combined_result_3 = {
#         'ids': ['id1', 'id2', 'id3'],
#         'documents': [['Doc A', 'Doc B', 'Doc C']],
#         'metadatas': [[
#             '{"ori_doc_title": "TestDoc3", "paragraph": 1, "chunk_level": 2, "chunk_size": 120}',
#             '{"ori_doc_title": "TestDoc3", "paragraph": 1, "chunk_level": 5, "chunk_size": 80}',
#             '{"ori_doc_title": "TestDoc4", "paragraph": 2, "chunk_level": 1, "chunk_size": 150}'
#         ]],
#         'distances': [[0.15, 0.25, 0.05]]
#     }
    
#     result3 = processor.main(combined_result_3)
#     print(f"Result: {len(result3)} items")
#     for i, meta in enumerate(result3):
#         print(f"  {i+1}. Doc: {meta.get('ori_doc_title')}, Level: {meta.get('chunk_level')}, Size: {meta.get('chunk_size')}")
#     print()

#     # Test Case 4: Mixed hierarchy levels
#     print("Test Case 4: Complex hierarchy with multiple documents")
#     combined_result_4 = {
#         'ids': ['id1', 'id2', 'id3', 'id4', 'id5', 'id6'],
#         'documents': [['Content 1', 'Content 2', 'Content 3', 'Content 4', 'Content 5', 'Content 6']],
#         'metadatas': [[
#             {'ori_doc_title': 'Doc1', 'paragraph': 1, 'chunk_level': 1, 'chunk_size': 200},
#             {'ori_doc_title': 'Doc1', 'paragraph': 1, 'chunk_level': 2, 'chunk_size': 150},
#             {'ori_doc_title': 'Doc1', 'paragraph': 1, 'chunk_level': 4, 'chunk_size': 100},
#             {'ori_doc_title': 'Doc1', 'paragraph': 2, 'chunk_level': 3, 'chunk_size': 180},
#             {'ori_doc_title': 'Doc1', 'paragraph': 2, 'chunk_level': 6, 'chunk_size': 120},
#             {'ori_doc_title': 'Doc1', 'paragraph': 2, 'chunk_level': 7, 'chunk_size': 90}
#         ]],
#         'distances': [[0.1, 0.15, 0.3, 0.12, 0.25, 0.35]]
#     }
    
#     result4 = processor.main(combined_result_4)
#     print(f"Result: {len(result4)} items")
#     for i, meta in enumerate(result4):
#         print(f"  {i+1}. Doc: {meta.get('ori_doc_title')}, Para: {meta.get('paragraph')}, Level: {meta.get('chunk_level')}, Size: {meta.get('chunk_size')}")
#     print()

#     # Test Case 5: Edge case - empty or malformed data
#     print("Test Case 5: Edge cases")
    
#     # Empty data
#     empty_result = {
#         'ids': [],
#         'documents': [[]],
#         'metadatas': [[]],
#         'distances': [[]]
#     }
#     result5a = processor.main(empty_result)
#     print(f"Empty data result: {len(result5a)} items")
    
#     # Missing metadata
#     missing_meta = {
#         'ids': ['id1'],
#         'documents': [['Some content']],
#         'metadatas': [[]],
#         'distances': [[0.1]]
#     }
#     result5b = processor.main(missing_meta)
#     print(f"Missing metadata result: {len(result5b)} items")
#     print()

#     print("=== All tests completed ===")


# # Run the tests
# if __name__ == "__main__":
#     test_chunk_processor()
