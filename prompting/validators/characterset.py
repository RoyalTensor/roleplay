from collections.abc import Iterator
import random
import bittensor as bt
from datasets import load_dataset
from typing import TypedDict

CHUB_DATASET = "RoyalTensor/chub_popular_characters"


class Character(TypedDict):
    creator: str
    description: str
    first_mes: str
    mes_example: str
    name: str
    personality: str
    scenario: str
    system_prompt: str
    char_greeting: str
    example_dialogue: str
    world_scenario: str
    char_persona: str
    char_name: str


def default_character() -> Character:
    return {
        "creator": "",
        "description": "",
        "first_mes": "",
        "mes_example": "",
        "name": "",
        "personality": "",
        "scenario": "",
        "system_prompt": "",
        "char_greeting": "",
        "example_dialogue": "",
        "world_scenario": "",
        "char_persona": "",
        "char_name": "",
    }


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

    def __next__(self) -> Character:
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


class MockCharacterSet(Iterator):
    def __next__(self) -> Character:
        return {
            "creator": "a",
            "description": "a",
            "first_mes": "a",
            "mes_example": "a",
            "name": "a",
            "personality": "a",
            "scenario": "a",
            "system_prompt": "a",
            "char_greeting": "a",
            "example_dialogue": "a",
            "world_scenario": "a",
            "char_persona": "a",
            "char_name": "a",
        }
