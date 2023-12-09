import unittest
from prompting.validators.characterset import CharacterSet


class CharacterSetTest(unittest.TestCase):
    def setUp(self):
        self.data = {
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

    def test_next_skips_empty_and_newline_only_strings(self):
        mock_data = iter(
            [
                {
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
                },
                self.data,
            ]
        )
        dataset = CharacterSet()
        dataset.character_set = mock_data

        # Test that __next__ skips empty texts and texts that consist only of newline characters
        self.assertEqual(dataset.__next__(), self.data)

    def test_next_returns_regular_strings(self):
        mock_data = iter([self.data])
        dataset = CharacterSet()
        dataset.character_set = mock_data

        # Test that __next__ returns a non-empty text
        self.assertEqual(dataset.__next__(), self.data)


if __name__ == "__main__":
    unittest.main()
