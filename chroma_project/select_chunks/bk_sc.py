from collections import defaultdict
from datetime import datetime

class ChunkSelector:
    def __init__(self, combined_result, token_limit):
        self.combined_result = combined_result
        self.token_limit = token_limit
        self.selected_chunks = []
        self.total_tokens = 0
        self.seen_chunks = defaultdict(lambda: None)  # Tracks highest-level chunk per (article, paragraph)
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
            self._add_or_replace_chunk(chunk)
        self._log_summary()
        self._validate_chunks()
        return self.selected_chunks

    # -------------------------------
    # Centralized Add/Replace Logic
    # -------------------------------
    def _add_or_replace_chunk(self, chunk):
        """Add or replace chunk while respecting token limit and hierarchy rules."""
        key = (chunk["ori_doc_title"], chunk["paragraph"])
        existing_chunk = self.seen_chunks[key]
        chunk_level = chunk["chunk_level"]
        current_hierarchy = self.chunk_level_mapping[chunk_level]

        # If we have an existing chunk for this key
        if existing_chunk:
            existing_hierarchy = self.chunk_level_mapping[existing_chunk["chunk_level"]]

            # Case 1: Existing chunk is higher priority
            if existing_hierarchy < current_hierarchy:
                # Keep the existing one if hierarchy rules demand
                if existing_chunk["chunk_level"] == 1 or \
                   (existing_chunk["chunk_level"] == 2 and chunk_level in [4, 5]) or \
                   (existing_chunk["chunk_level"] == 3 and chunk_level in [6, 7]):
                    return
                else:
                    self._log_removal(existing_chunk)
                    self._safe_replace_chunk(key, chunk)

            # Case 2: New chunk is higher priority
            elif existing_hierarchy > current_hierarchy:
                self._remove_lower_chunks(chunk, key)
                self._safe_replace_chunk(key, chunk)

        else:
            # No existing chunk for this key — just add it
            self._safe_add_chunk(key, chunk)

    # -------------------------------
    # Safe Add / Replace Methods
    # -------------------------------
    def _safe_add_chunk(self, key, chunk):
        """Add a chunk if it fits in the token budget."""
        if self.total_tokens + chunk["chunk_size"] > self.token_limit:
            return  # Skip if over budget
        self.selected_chunks.append(chunk)
        self.seen_chunks[key] = chunk
        self.total_tokens += chunk["chunk_size"]
        self._log_addition(chunk)

    def _safe_replace_chunk(self, key, chunk):
        """Replace an existing chunk while keeping within token budget."""
        old_chunk = self.seen_chunks.get(key)
        old_size = old_chunk["chunk_size"] if old_chunk else 0
        new_total = self.total_tokens - old_size + chunk["chunk_size"]

        if new_total > self.token_limit:
            return  # Skip if replacement exceeds budget

        # Remove old chunk from list if it exists there
        if old_chunk and old_chunk in self.selected_chunks:
            self.selected_chunks.remove(old_chunk)
            self.total_tokens -= old_size

        # Add the new chunk
        self.selected_chunks.append(chunk)
        self.seen_chunks[key] = chunk
        self.total_tokens += chunk["chunk_size"]
        self._log_addition(chunk)


    # -------------------------------
    # Remove lower-level chunks
    # -------------------------------
    def _remove_lower_chunks(self, chunk, key):
        article, paragraph = key
        chunk_level = chunk["chunk_level"]

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

    # -------------------------------
    # Logging Helpers
    # -------------------------------
    def _log_addition(self, chunk):
        with open("selected_chunks.txt", "a") as f:
            f.write("\n--- Chunk Added ---\n")
            f.write(f"Time       : {datetime.now()}\n")
            f.write(f"Article    : {chunk['ori_doc_title']}\n")
            f.write(f"Segment    : {chunk['paragraph']}\n")
            f.write(f"Chunk Level: {chunk['chunk_level']}\n")
            f.write("-------------------\n")

    def _log_removal(self, chunk):
        with open("selected_chunks.txt", "a") as f:
            f.write("\n--- Chunk Removed ---\n")
            f.write(f"Time       : {datetime.now()}\n")
            f.write(f"Article    : {chunk['ori_doc_title']}\n")
            f.write(f"Segment    : {chunk['paragraph']}\n")
            f.write(f"Chunk Level: {chunk['chunk_level']} (removed)\n")
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

    # -------------------------------
    # Validation
    # -------------------------------
    def _validate_chunks(self):
        chunk_groups = defaultdict(list)

        for chunk in self.selected_chunks:
            key = (chunk["ori_doc_title"], chunk["paragraph"])
            chunk_groups[key].append(chunk)

        for (doc_title, paragraph), chunks in chunk_groups.items():
            if len(chunks) > 1:
                chunk_levels = [chunk["chunk_level"] for chunk in chunks]
                print(f"[Warning] Conflicting chunks in '{doc_title}', segment {paragraph}: Levels = {chunk_levels}")
                with open("selected_chunks.txt", "a") as f:
                    f.write("\n!!! Conflict Detected !!!\n")
                    f.write(f"Article    : {doc_title}\n")
                    f.write(f"Segment    : {paragraph}\n")
                    f.write(f"Chunk Levels: {chunk_levels}\n")
                    f.write("!!!!!!!!!!!!!!!!!!!!!!!!!!\n")