from collections import defaultdict
from datetime import datetime

class ChunkSelector:
    def __init__(self, combined_result, token_limit):
        self.combined_result = combined_result
        self.token_limit = token_limit
        self.selected_chunks = []
        self.total_tokens = 0
        self.seen_chunks = defaultdict(lambda: None)  # Tracks the highest-level chunk per (article, paragraph)
        self.chunk_level_mapping = {
            1: 1,
            2: 2, 
            3: 2,
            4: 3, 
            5: 3, 
            6: 3, 
            7: 3
        }

    def process_chunks(self):
        for chunk in self.combined_result['metadatas'][0]:
            if self._can_add_chunk(chunk):
                self._add_chunk(chunk)
        self._log_summary()
        self._validate_chunks()
        return self.selected_chunks

    def _can_add_chunk(self, chunk):
        chunk_size = chunk["chunk_size"]
        if self.total_tokens + chunk_size > self.token_limit:
            return False
        return True

    def _add_chunk(self, chunk):
        key = (chunk["ori_doc_title"], chunk["paragraph"])
        existing_chunk = self.seen_chunks[key]
        chunk_level = chunk["chunk_level"]
        current_hierarchy = self.chunk_level_mapping[chunk_level]

        if existing_chunk:
            existing_hierarchy = self.chunk_level_mapping[existing_chunk["chunk_level"]]
            if existing_hierarchy < current_hierarchy:
                if existing_chunk["chunk_level"] == 1 or (existing_chunk["chunk_level"] == 2 and chunk_level in [4, 5]) or (existing_chunk["chunk_level"] == 3 and chunk_level in [6, 7]):
                    return
                else:
                    self._log_removal(existing_chunk)
                    self._replace_chunk(chunk, key)
            elif existing_hierarchy > current_hierarchy:
                self._remove_lower_chunks(chunk, key)
                self._replace_chunk(chunk, key)
        else:
            self.selected_chunks.append(chunk)
            self.seen_chunks[key] = chunk
            self.total_tokens += chunk["chunk_size"]
            self._log_addition(chunk)

    def _remove_lower_chunks(self, chunk, key):
        article, paragraph = key
        chunk_level = chunk["chunk_level"]
        # if chunk_level == 1:
        #     self.selected_chunks = [c for c in self.selected_chunks if c["ori_doc_title"] != article or c["paragraph"] != paragraph or c["chunk_level"] == 1]
        # elif chunk_level == 2:
        #     self.selected_chunks = [c for c in self.selected_chunks if not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in [4, 5])]
        # elif chunk_level == 3:
        #     self.selected_chunks = [c for c in self.selected_chunks if not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in [6, 7])]
        
        
    
        level_map = {
            1: lambda c: not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] != 1),
            2: lambda c: not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in {4, 5}),
            3: lambda c: not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in {6, 7}),
        }

        if chunk_level in level_map:
            removed_chunks = [c for c in self.selected_chunks if not level_map[chunk_level](c)]
            self.selected_chunks = [c for c in self.selected_chunks if level_map[chunk_level](c)]
            
            for removed_chunk in removed_chunks:
                self._log_removal(removed_chunk)




        self.total_tokens = sum(c["chunk_size"] for c in self.selected_chunks)

    def _replace_chunk(self, chunk, key):
        self.selected_chunks.append(chunk)
        self.seen_chunks[key] = chunk
        self.total_tokens += chunk["chunk_size"]
        self._log_addition(chunk)

    # def _validate_chunks(self):
    #     for i in range(len(self.selected_chunks)):
    #         for j in range(i + 1, len(self.selected_chunks)):
    #             chunk1, chunk2 = self.selected_chunks[i], self.selected_chunks[j]
    #             if chunk1["ori_doc_title"] == chunk2["ori_doc_title"] and chunk1["paragraph"] == chunk2["paragraph"]:
    #                 print(f"Found invalid combination: chunk_level {chunk1['chunk_level']}, chunk_level {chunk2['chunk_level']}, article {chunk1['ori_doc_title']}, paragraph {chunk1['paragraph']}")

    # def _validate_chunks(self):
    #     chunk_groups = defaultdict(list)
        
    #     # Group chunks by (ori_doc_title, paragraph)
    #     for chunk in self.selected_chunks:
    #         key = (chunk["ori_doc_title"], chunk["paragraph"])
    #         chunk_groups[key].append(chunk)

    #     # Check for invalid combinations
    #     for (doc_title, paragraph), chunks in chunk_groups.items():
    #         if len(chunks) > 1:
    #             chunk_levels = [chunk["chunk_level"] for chunk in chunks]
    #             print(f"Found invalid combination in article '{doc_title}', paragraph {paragraph}: chunk levels {chunk_levels}")



    # def _log_addition(self, chunk):
    #     with open("selected_chunks.txt", "a") as f:
    #         f.write(f"Added chunk: {chunk['ori_doc_title']}, paragraph: {chunk['paragraph']}, chunk_level: {chunk['chunk_level']}\n")

    # def _log_removal(self, chunk):
    #     with open("selected_chunks.txt", "a") as f:
    #         f.write(f"\nRemoving smaller chunk: {chunk['ori_doc_title']}, paragraph: {chunk['paragraph']}, chunk_level: {chunk['chunk_level']}\n")

    # def _log_summary(self):
    #     chunk_size_counts = defaultdict(int)
    #     for chunk in self.selected_chunks:
    #         chunk_size_counts[chunk['chunk_size']] += 1
        
    #     with open("selected_chunks.txt", "a") as f:
    #         f.write(f"\nTotal tokens: {self.total_tokens}\n")
    #         f.write(f"Chunks of size 512: {chunk_size_counts[512]}\n")
    #         f.write(f"Chunks of size 256: {chunk_size_counts[256]}\n")
    #         f.write(f"Chunks of size 128: {chunk_size_counts[128]}\n")
    #         f.write("############################## Finished this task ##############################\n")

# Usage Example
# selector = ChunkSelector(combined_result, k)
# selected_chunks = selector.process_chunks()



    def _log_addition(self, chunk):
        with open("selected_chunks.txt", "a") as f:
            f.write("\n--- Chunk Added ---\n")
            f.write(f"Time       : {datetime.now()}\n")
            f.write(f"Article    : {chunk['ori_doc_title']}\n")
            f.write(f"Segment  : {chunk['paragraph']}\n")
            f.write(f"Chunk Level: {chunk['chunk_level']}\n")
            f.write("-------------------\n")

    def _log_removal(self, chunk):
        with open("selected_chunks.txt", "a") as f:
            f.write("\n--- Chunk Removed ---\n")
            f.write(f"Time       : {datetime.now()}\n")
            f.write(f"Article    : {chunk['ori_doc_title']}\n")
            f.write(f"Segment  : {chunk['paragraph']}\n")
            f.write(f"Chunk Level: {chunk['chunk_level']} (removed due to smaller size)\n")
            f.write("---------------------\n")

    def _log_summary(self):
        chunk_size_counts = defaultdict(int)
        for chunk in self.selected_chunks:
            chunk_size_counts[chunk['chunk_size']] += 1

        with open("selected_chunks.txt", "a") as f:
            f.write("\n========== Summary ==========\n")
            f.write(f"Time         : {datetime.now()}\n")
            f.write(f"Total tokens : {self.total_tokens}\n")
            f.write(f"Chunk sizes  :\n")
            for size in sorted(chunk_size_counts):
                f.write(f"  - Size {size}: {chunk_size_counts[size]} chunks\n")
            f.write("========= End Summary ========\n\n")

    def _validate_chunks(self):
        chunk_groups = defaultdict(list)
        
        for chunk in self.selected_chunks:
            key = (chunk["ori_doc_title"], chunk["paragraph"])
            chunk_groups[key].append(chunk)

        for (doc_title, paragraph), chunks in chunk_groups.items():
            if len(chunks) > 1:
                chunk_levels = [chunk["chunk_level"] for chunk in chunks]
                print(f"[Warning] Conflicting chunks in '{doc_title}', paragraph {paragraph}: Levels = {chunk_levels}")
                with open("selected_chunks.txt", "a") as f:
                    f.write("\n!!! Conflict Detected !!!\n")
                    f.write(f"Article    : {doc_title}\n")
                    f.write(f"Segment  : {paragraph}\n")
                    f.write(f"Chunk Levels: {chunk_levels}\n")
                    f.write("!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

