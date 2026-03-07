from collections import defaultdict

class ChunkProcessor:
    def __init__(self):
        # Set hierarchy inside the class
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
        """Check if child_block is a subset of parent_block in hierarchy."""
        return child_block in self.hierarchy.get(parent_block, [])

    def get_level(self, block):
        """Find the level of the given block."""
        level = 1
        current_level_blocks = [1]  # Start from the root (level 1)

        while current_level_blocks:
            if block in current_level_blocks:
                return level
            next_level_blocks = []
            for b in current_level_blocks:
                next_level_blocks.extend(self.hierarchy[b])
            current_level_blocks = next_level_blocks
            level += 1

        return None

    def highest_level_with_count(self, group_blocks):
        """Find highest level and its count in a group."""
        level_list = [self.get_level(i) for i in group_blocks]
        highest_level = min(level_list)
        count_highest = level_list.count(highest_level)
        return highest_level, count_highest

    def group_chunks(self, combined_result):
        """Group chunks by (ori_doc_title, paragraph)."""
        groups = defaultdict(list)
        for item in combined_result:
            meta = item['metadata'][0]
            key = (meta['ori_doc_title'], meta['paragraph'])
            groups[key].append(item)
        return groups

    def process_group(self, group_items):
        """Apply filtering rules to a single group."""
        labels = [item['metadata'][0]['chunk_level'] for item in group_items]
        highest_level, count_highest = self.highest_level_with_count(labels)

        if highest_level == 1:
            filtered_items = []
            for item in group_items:
                chunk_level = item['metadata'][0]['chunk_level']
                if self.get_level(chunk_level) == 1:
                    filtered_items.append(item)

            # Get the first item from the filtered list
            first_item = filtered_items[:1]
            return first_item

        elif highest_level == 2:
            level2_items = [item for item in group_items if self.get_level(item['metadata'][0]['chunk_level']) == 2]
            level3_items = [item for item in group_items if self.get_level(item['metadata'][0]['chunk_level']) == 3]

            if count_highest == 1:
                parent_block = level2_items[0]['metadata'][0]['chunk_level']
                filtered_level3 = [
                    item for item in level3_items
                    if not self.is_subset(parent_block, item['metadata'][0]['chunk_level'])
                ]
                return level2_items + filtered_level3
            else:
                result = []
                for lvl2 in level2_items:
                    parent_block = lvl2['metadata'][0]['chunk_level']
                    result.append(lvl2)
                    filtered_level3 = [
                        item for item in level3_items
                        if not self.is_subset(parent_block, item['metadata'][0]['chunk_level'])
                    ]
                    result.extend(filtered_level3)
                return result

        else:
            return group_items

    def main(self, combined_result):
        grouped = self.group_chunks(combined_result)
        processed_results = []
        for _, items in grouped.items():
            processed_results.extend(self.process_group(items))
        return processed_results
