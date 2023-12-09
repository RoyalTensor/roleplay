from collections.abc import Iterator
import random
import bittensor as bt
from datasets import load_dataset

CHUB_DATASET = "RoyalTensor/chub_popular_characters"


class CharacterSet(Iterator):
    def __init__(self, is_mock=False):
        super().__init__()
        if is_mock:
            self.character_set = iter([])
        else:
            self.character_set = self.load_iterator()

    def load_iterator(self):
        seed = random.randint(0, 1000)
        return iter(
            load_dataset(CHUB_DATASET, split="train", streaming=True).shuffle(
                seed=seed, buffer_size=10000
            )
        )

    def __next__(self):
        while True:
            try:
                bt.logging.debug("Retrieving data from dataset...")

                character = next(self.character_set)
                name = character["name"]
                description = character["description"]

                # Check if these fields are not empty strings or do not consist only of newline characters
                if name.strip() and description.strip():
                    return character
            except StopIteration:
                # We have reached the end of the dataset, so we need to reload it
                self.character_set = self.load_iterator()


class MockDataset(Iterator):
    def __next__(self):
        return {"text": "What is the capital of Texas?"}
