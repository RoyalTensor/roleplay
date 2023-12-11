import torch
from typing import List, Union
from .config import RewardModelType
from .reward import BaseRewardModel, BaseRewardEvent
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline


class MistralRewardModel(BaseRewardModel):
    reward_model_path: str = "reciprocate/mistral-7b-rm"
    revision: str = "e301d78"

    @property
    def name(self) -> str:
        return RewardModelType.mistral.value

    def __init__(self, device: str):
        super().__init__()
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(
            MistralRewardModel.reward_model_path,
            revision=MistralRewardModel.revision,
        )
        # self.tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.1")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            MistralRewardModel.reward_model_path,
            revision=MistralRewardModel.revision,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)
        self.reward_fn = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            truncation=True,
            batch_size=8,
            max_length=4096,
            device=self.device,
        )

    def reward(self, prompt: str, completion: str, name: str) -> BaseRewardEvent:
        reward_event = BaseRewardEvent()
        with torch.no_grad():
            chat = [
                {
                    "role": "user",
                    "content": prompt,
                },
                {
                    "role": "assistant",
                    "content": completion,
                },
            ]

            output = self.reward_fn(
                self.tokenizer.apply_chat_template(chat, tokenize=False)
            )
            scores = [x["score"] for x in output]
            reward_event.reward = float(scores[0])
            return reward_event

    def get_rewards(
        self, prompt: str, completions: List[str], name: str
    ) -> List[BaseRewardEvent]:
        # Get all the reward results.
        reward_events = [
            self.reward(prompt, completion, name) for completion in completions
        ]

        return reward_events
