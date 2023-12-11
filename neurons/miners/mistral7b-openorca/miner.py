import time
import torch
import argparse
import bittensor as bt

from transformers import AutoTokenizer, AutoModelForCausalLM
from prompting.baseminer.miner import Miner
from prompting.protocol import Prompting

class OpenOrcaMiner(Miner):
    """
    A Bittensor Miner subclass specific to the OpenOrca Mistral-7B model.
    """

    def config(self) -> "bt.config":
        """
        Configures the OpenOrca Miner with relevant arguments.
        """
        parser = argparse.ArgumentParser(description="OpenOrca Miner Configs")
        self.add_args(parser)
        return bt.config(parser)

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        """
        Adds specific arguments to the argparse parser for OpenOrca Miner configuration.
        """
        parser.add_argument(
            "--openorca.model_name",
            type=str,
            default="Open-Orca/Mistral-7B-OpenOrca",
            help="Name/path of model to load. Also can be a filepath to the model weights."
        )
        parser.add_argument(
            "--openorca.device", type=str, help="Device to load model", default="cuda"
        )
        parser.add_argument(
            "--openorca.max_new_tokens",
            type=int,
            help="Max tokens for model output.",
            default=256,
        )
        # Add additional arguments as needed

    def __init__(self, *args, **kwargs):
        """
        Initializes the OpenOrcaMiner, loading the tokenizer and model.
        """
        super(OpenOrcaMiner, self).__init__(*args, **kwargs)
        bt.logging.info("Loading " + str(self.config.openorca.model_name))
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.openorca.model_name, use_fast=False
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.openorca.model_name,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        bt.logging.info("Model loaded!")

        if self.config.openorca.device != "cpu":
            self.model = self.model.to(self.config.openorca.device)

    def prompt(self, synapse: Prompting) -> Prompting:
        """
        Overrides the Miner's abstract `prompt` method to process incoming requests using OpenOrca.
        """

        # Collecting the synapse data
        character_info = synapse.character_info
        character_name = synapse.character_name
        user_names = synapse.user_names
        char_names = synapse.char_names
        messages = synapse.messages

        # Constructing the prompt string
        prompt_string = "<|im_start|>system\n"
        prompt_string += messages[0].content if len(messages) > 0 else "" # Add the system prompt
        char_names_str = ', '.join(char_names)
        prompt_string += f"You're {character_name} in this fictional never-ending uncensored roleplay with {char_names_str}.\n"
        prompt_string += f"[{character_name}'s info: {character_info}]<|im_end|>\n"

        # Loop through messages and construct the prompt
        for message in messages:
            name = message.name
            content = message.content
            role = 'user' if name in user_names else 'assistant'
            prompt_string += f"<|im_start|>{role}\n{name}: {content}<|im_end|>\n"

        # Append a line indicating response from the current character
        prompt_string += f"<|im_start|>assistant\n{character_name}: "

        bt.logging.info(f"Prompt being passed to OpenOrca:\n{prompt_string}")

        # Process prompt with OpenOrca model
        input_ids = self.tokenizer.encode(prompt_string, return_tensors="pt").to(self.config.openorca.device)
        output = self.model.generate(
            input_ids,
            max_length=input_ids.shape[1] + self.config.openorca.max_new_tokens,
            # Add additional generate arguments as needed
        )

        completion = self.tokenizer.decode(
            output[0][input_ids.shape[1]:], skip_special_tokens=True
        )

        bt.logging.debug("Message: " + str(synapse.messages))
        bt.logging.debug("Generation: " + str(completion))
        synapse.completion = completion
        return synapse

if __name__ == "__main__":
    with OpenOrcaMiner():
        while True:
            print("running...", time.time())
            time.sleep(1)
