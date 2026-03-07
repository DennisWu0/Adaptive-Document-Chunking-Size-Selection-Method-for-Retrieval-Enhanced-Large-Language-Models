#back up file for selected_chunks.py


from collections import defaultdict

def select_chunks(combined_result, k):
    selected_chunks = []
    total_tokens = 0
    seen_chunks = defaultdict(lambda: None)  # Tracks the highest-level chunk per (article, paragraph)

    # Define chunk hierarchy mapping
    chunk_level_mapping = {
        1: 1,
        2: 2,
        3: 2,
        4: 3,
        5: 3,
        6: 3,
        7: 3
    }

    for chunk in combined_result['metadatas'][0]:
        chunk_size = chunk["chunk_size"]
        article = chunk["ori_doc_title"]
        paragraph = chunk["paragraph"]
        chunk_level = chunk["chunk_level"]

        if total_tokens + chunk_size > k:
            continue  # Skip if adding this chunk exceeds token limit

        key = (article, paragraph)
        existing_chunk = seen_chunks[key]

        if existing_chunk:
            existing_hierarchy = chunk_level_mapping[existing_chunk["chunk_level"]]
            current_hierarchy = chunk_level_mapping[chunk_level]

            # If a higher-level chunk exists, skip adding a lower-level chunk
            if existing_hierarchy < current_hierarchy:
                related_chunks = [
                    c for c in selected_chunks
                    if c["ori_doc_title"] == article and c["paragraph"] == paragraph
                ]
                # Handling chunk level 1
                if existing_chunk["chunk_level"] == 1:
                    continue
                elif existing_hierarchy == 2:
                    has_level_3 = any(c["chunk_level"] == 3 for c in related_chunks)
                    if has_level_3:
                        continue  # Skip if level 3 chunk exists
                    if chunk_level in [4, 5]:
                        continue  # Skip if child of level 2
                    # Allow 6,7

                # Specific logic for chunk level 3
                elif existing_hierarchy == 3:
                    has_level_2 = any(c["chunk_level"] == 2 for c in related_chunks)
                    if has_level_2:
                        continue  # Skip if level 2 chunk exists
                    if chunk_level in [6, 7]:
                        continue  # Skip child of level 3
                    # Allow 4,5
                # Handling chunk level 2, skip adding child chunks 4, 5
                # elif existing_chunk["chunk_level"] == 2 and chunk_level in [4, 5]:
                #     continue
                # # Handling chunk level 3, skip adding child chunks 6, 7
                # elif existing_chunk["chunk_level"] == 3 and chunk_level in [6, 7]:
                #     continue
                else:
                    # Add current chunk and update total tokens
                    selected_chunks.append(chunk)
                    total_tokens += chunk_size
                    seen_chunks[key] = chunk
                    with open("selected_chunks.txt", "a") as f:
                        f.write(f"Added chunk: {chunk['ori_doc_title']}, paragraph: {chunk['paragraph']}, chunk_level: {chunk['chunk_level']}\n")
                    continue

            # If a lower-level chunk exists and a parent chunk is added, remove the lower-level one
            elif existing_hierarchy > current_hierarchy:
                if current_hierarchy == 1:
                    selected_chunks[:] = [c for c in selected_chunks if c["ori_doc_title"] != article or c["paragraph"] != paragraph or c["chunk_level"] == 1]
                    total_tokens -= sum(c["chunk_size"] for c in selected_chunks if c["ori_doc_title"] == article and c["paragraph"] == paragraph)
                elif chunk_level == 2:
                    selected_chunks[:] = [c for c in selected_chunks if not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in [4, 5])]
                    total_tokens -= sum(c["chunk_size"] for c in selected_chunks if c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in [4, 5])
                elif chunk_level == 3:
                    selected_chunks[:] = [c for c in selected_chunks if not (c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in [6, 7])]
                    total_tokens -= sum(c["chunk_size"] for c in selected_chunks if c["ori_doc_title"] == article and c["paragraph"] == paragraph and c["chunk_level"] in [6, 7])

                # After removal, add the current chunk and update total tokens
                selected_chunks.append(chunk)
                total_tokens += chunk_size
                seen_chunks[key] = chunk

                with open("selected_chunks.txt", "a") as f:
                    f.write(f"\nRemoving smaller chunk: {existing_chunk}\n")
                    f.write(f"Total tokens after removal: {total_tokens}\n\n")
                    f.write(f"Added chunk: {chunk['ori_doc_title']}, paragraph: {chunk['paragraph']}, chunk_level: {chunk['chunk_level']}\n")

        else:
            # If no existing chunk, add the current chunk
            selected_chunks.append(chunk)
            seen_chunks[key] = chunk
            total_tokens += chunk_size
            with open("selected_chunks.txt", "a") as f:
                f.write(f"Added chunk: {chunk['ori_doc_title']}, paragraph: {chunk['paragraph']}, chunk_level: {chunk['chunk_level']}\n")

    # Count different chunk sizes
    chunk_size_counts = defaultdict(int)
    for chunk in selected_chunks:
        chunk_size_counts[chunk['chunk_size']] += 1

    print(f"Total tokens: {total_tokens}")
    with open("selected_chunks.txt", "a") as f:
        f.write(f"\nTotal tokens: {total_tokens}\n")
        f.write(f"Chunks of size 512: {chunk_size_counts[512]}\n")
        f.write(f"Chunks of size 256: {chunk_size_counts[256]}\n")
        f.write(f"Chunks of size 128: {chunk_size_counts[128]}\n")
        f.write("############################## Finished this task ##############################\n")

    # Check for invalid chunk combinations
    for i in range(len(selected_chunks)):
        for j in range(i + 1, len(selected_chunks)):
            chunk1 = selected_chunks[i]
            chunk2 = selected_chunks[j]
            if chunk1["ori_doc_title"] == chunk2["ori_doc_title"] and chunk1["paragraph"] == chunk2["paragraph"]:
                print(f"Found invalid combination: chunk_level {chunk1['chunk_level']}, chunk_level {chunk2['chunk_level']}, article {chunk1['ori_doc_title']}, paragraph {chunk1['paragraph']}")

    return selected_chunks