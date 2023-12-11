# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import torch
import textwrap
import random
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List
from prompting.validators.criteria import (
    TaskCriterion,
    MatchLengthCriteria,
    TextLengthUnitEnum,
    ContentMatchTypeEnum,
    SimpleResponseLayoutCriteria,
    MatchContentCriteria,
    MatchLayoutCriteria,
    LayoutMatchTypeEnum,
)
from prompting.validators.characterset import Character, default_character


@dataclass
class Task(ABC):
    base_text: str
    task_name: str
    task_type: str
    criteria: List[TaskCriterion] = field(default_factory=list)

    def get_criteria_strs(self) -> List[str]:
        # For getting criterions to give to the synapse
        return [criterion.compose_text() for criterion in self.criteria]

    def compose_criteria_str(self) -> str:
        criteria_bullet_points = [
            f"- {criterion.compose_text()}" for criterion in self.criteria
        ]
        criteria_bullet_points_str = "\n".join(criteria_bullet_points)
        text = textwrap.dedent("""\
        The following criteria must be respected:
        {criteria}
        """)
        return text.format(criteria = criteria_bullet_points_str)
    
    @abstractmethod
    def compose_instruction(self) -> str:
        ...

    def compose_prompt(self) -> str:
        
        text = textwrap.dedent(
            """\
            {instruction}
            {base_text}
            {criteria}
            """
        )
        
        return text.format(instruction = self.compose_instruction(), base_text=self.base_text,criteria = self.compose_criteria_str())

@dataclass
class RoleplayTask(Task, ABC):
    character: Character = field(default_factory=default_character)

    @abstractmethod
    def compose_instruction(self) -> str:
        ...


class MessageFromDescriptionTask(RoleplayTask):
    
    def compose_instruction(self) -> str:
        
        instruction = textwrap.dedent(
            f"""\
        Please read the following character description carefully.
        Your task is roleplay as the character described in the text below and to write a message that would be typical of that character.
        No matter what, do not break character.
        """
        )
        return instruction
    
    # def compose_prompt(self) -> str:
    #     criteria_bullet_points_str = self.compose_criteria_str()

    #     prompt_template = textwrap.dedent(
    #         """\
    #     Please read the following character description carefully.
    #     Your task is roleplay as the character described in the text below and to write a message that would be typical of that character.
    #     No matter what, do not break character.
        
    #     {base_text}
        
    #     The following criteria must be respected:
    #     {criteria}
    #     """
    #     )

    #     prompt = prompt_template.format(
    #         base_text=self.base_text, criteria=criteria_bullet_points_str
    #     )
    #     return prompt


def create_message_from_description_task(
    base_text: str, character: Character
) -> MessageFromDescriptionTask:
    criteria = [
        MatchLengthCriteria(
            penalty=0.25,
            target_length=random.randint(50, 200),
            unit=TextLengthUnitEnum.WORDS,
        ),
        MatchLengthCriteria(
            penalty=0.25,
            target_length=random.randint(4, 10),
            unit=TextLengthUnitEnum.SENTENCES,
        ),
    ]

    return MessageFromDescriptionTask(
        base_text=base_text,
        criteria=criteria,
        task_type="message-from-description",
        task_name="augment",
        character=character,
    )



