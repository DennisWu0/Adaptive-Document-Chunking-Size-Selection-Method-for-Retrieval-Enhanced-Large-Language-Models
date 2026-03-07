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

    def get_parent_child_pairs(self, group_items):
        """Group items into parent-child relationships"""
        pairs = {}
        
        for i, item in enumerate(group_items):
            chunk_level = item['metadata'][0].get('chunk_level')
            children = []
            
            # Find children of this item
            for j, other_item in enumerate(group_items):
                if i == j:  # Skip self
                    continue
                other_chunk_level = other_item['metadata'][0].get('chunk_level')
                if self.is_descendant(chunk_level, other_chunk_level):
                    children.append(other_item)
            
            if children:  # Only add if there are children
                pairs[i] = {'parent': item, 'children': children}
        
        return pairs

    def remove_redundant_overlaps(self, items):
        """Remove remaining overlaps after noise filtering"""
        final_items = []
        processed_chunks = set()
        
        # Sort by similarity (best first) - lower distance = better similarity
        sorted_items = sorted(items, key=lambda x: self.get_distance(x))
        
        for item in sorted_items:
            chunk_level = item['metadata'][0].get('chunk_level')
            
            # Check if this chunk overlaps with already selected chunks
            has_overlap = any(
                self.is_descendant(chunk_level, selected_chunk) or 
                self.is_descendant(selected_chunk, chunk_level)
                for selected_chunk in processed_chunks
            )
            
            if not has_overlap:
                final_items.append(item)
                processed_chunks.add(chunk_level)
        
        return final_items

    def adaptive_hierarchical_filter(self, group_items, noise_threshold=0.25):
        """
        Stage 1: Noise Detection - Keep smaller chunks if parent has too much noise
        Stage 2: Redundancy Removal - Remove remaining overlaps
        """
        if not group_items:
            return []
        
        # Stage 1: Noise Detection
        noise_filtered_items = []
        parent_child_pairs = self.get_parent_child_pairs(group_items)
        processed_indices = set()
        
        if self.verbose:
            print(f"Processing group with {len(group_items)} items")
        
        for parent_idx, pair_data in parent_child_pairs.items():
            if parent_idx in processed_indices:
                continue
                
            parent = pair_data['parent']
            children = pair_data['children']
            parent_similarity = 1 - self.get_distance(parent)  # Convert distance to similarity
            
            # Check each child against parent
            keep_parent = True
            children_to_keep = []
            
            for child in children:
                # Find child index
                child_idx = None
                for idx, item in enumerate(group_items):
                    if item is child:
                        child_idx = idx
                        break
                
                if child_idx is not None and child_idx in processed_indices:
                    continue
                    
                child_similarity = 1 - self.get_distance(child)
                
                # Calculate improvement ratio: how much better is child vs parent
                if parent_similarity > 0:
                    improvement_ratio = (child_similarity - parent_similarity) / parent_similarity
                else:
                    improvement_ratio = float('inf') if child_similarity > 0 else 0
                
                if improvement_ratio > noise_threshold:  # Threshold improvement
                    # Child is significantly better - parent has noise
                    children_to_keep.append(child)
                    keep_parent = False
                    if child_idx is not None:
                        processed_indices.add(child_idx)
                    if self.verbose:
                        print(f"Noise detected: Parent {parent_similarity:.3f} vs Child {child_similarity:.3f}")
            
            if keep_parent:
                noise_filtered_items.append(parent)
                processed_indices.add(parent_idx)
            else:
                noise_filtered_items.extend(children_to_keep)
        
        # Add items that don't have parent-child relationships
        for idx, item in enumerate(group_items):
            if idx not in processed_indices:
                noise_filtered_items.append(item)
        
        # Stage 2: Remove remaining redundancies
        return self.remove_redundant_overlaps(noise_filtered_items)

    def process_group(self, items: List[Dict[str, Any]], use_adaptive_filter=True, noise_threshold=0.25):
        """Process a group of items with the same document title and paragraph."""
        
        if use_adaptive_filter:
            # Use the new adaptive hierarchical filtering method
            return self.adaptive_hierarchical_filter(items, noise_threshold)
        
        # Original method (kept for backward compatibility)
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

    def main(self, combined_result, token_budget=None, use_adaptive_filter=True, noise_threshold=0.25):
        """Main processing function that handles the new combined_result format."""
        # Step 1: Flatten the new format into individual items
        items = self.flatten_combined_result(combined_result)
        items = items[:250]
        
        # Step 2: Group & filter
        grouped = self.group_chunks(items)
        processed_results = []
        for _, group_items in grouped.items():
            processed_results.extend(self.process_group(group_items, use_adaptive_filter, noise_threshold))

        # Step 3: Sort by distance (lowest distance first - best matches first)
        processed_results.sort(key=lambda x: x['distances'][0])

        # Step 4: Apply token budget if provided
        final_list = []
        if token_budget is not None:
            total_tokens = 0
            remaining_items = processed_results.copy()

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
        else:
            final_list = [item['metadata'][0] for item in processed_results]

        # Count chunk sizes
        chunk_counts = {512: 0, 256: 0, 128: 0}
        for item in final_list:
            size = item.get('chunk_size')
            if size in chunk_counts:
                chunk_counts[size] += 1
        
        print(f"CHUNK COUNTS: 512={chunk_counts[512]}, 256={chunk_counts[256]}, 128={chunk_counts[128]}")
        print(f"TOTAL CHUNKS: {512 * chunk_counts[512] + 256 * chunk_counts[256] + 128 * chunk_counts[128]}")
        
        if use_adaptive_filter:
            print(f"Used Adaptive Hierarchical Filtering with noise threshold: {noise_threshold}")
        
        return final_list


# Test the enhanced functionality
def test_adaptive_filtering():
    print("=== Testing Adaptive Hierarchical Filtering ===\n")
    
    processor = ChunkProcessor(verbose=True)
    
    # Test case: 512-chunk (0.4 distance = 0.6 similarity) vs 128-chunk (0.1 distance = 0.9 similarity)
    test_result = {
        'ids': ['id1', 'id2', 'id3', 'id4', 'id5', 'id6', 'id7'],
        'documents': [['Doc1', 'Doc2', 'Doc3', 'Doc4', 'Doc5', 'Doc6', 'Doc7']],
        'metadatas': [[
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 1, 'chunk_size': 512},  # 512-size chunk
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 2, 'chunk_size': 256},  # 256-size chunk 1
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 3, 'chunk_size': 256},  # 256-size chunk 2
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 4, 'chunk_size': 128},  # 128-size chunk 1
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 5, 'chunk_size': 128},  # 128-size chunk 2
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 6, 'chunk_size': 128},  # 128-size chunk 3
            {'ori_doc_title': 'TestDoc', 'paragraph': 1, 'chunk_level': 7, 'chunk_size': 128}   # 128-size chunk 4
        ]],
        'distances': [[0.4, 0.35, 0.3, 0.1, 0.15, 0.2, 0.25]]  # 512 has high distance (low similarity), 128s have low distance (high similarity)
    }
    
    print("Original method:")
    result_original = processor.main(test_result, use_adaptive_filter=False)
    print(f"Selected {len(result_original)} chunks")
    for i, meta in enumerate(result_original):
        print(f"  {i+1}. Level: {meta.get('chunk_level')}, Size: {meta.get('chunk_size')}")
    print()
    
    print("Adaptive filtering method (threshold=0.25):")
    result_adaptive = processor.main(test_result, use_adaptive_filter=True, noise_threshold=0.25)
    print(f"Selected {len(result_adaptive)} chunks")
    for i, meta in enumerate(result_adaptive):
        print(f"  {i+1}. Level: {meta.get('chunk_level')}, Size: {meta.get('chunk_size')}")
    print()


if __name__ == "__main__":
    test_adaptive_filtering()