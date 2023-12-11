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
import os
import time
import requests
import json
import argparse
import bittensor
from typing import Optional

from prompting.baseminer.miner import Miner
from prompting.protocol import Prompting


class OpenRouterMiner(Miner):
    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        """
        Adds OpenRouter-specific arguments to the command line parser.

        Args:
            parser (argparse.ArgumentParser):
                The command line argument parser to which the OpenRouter-specific arguments should be added.
        """
        # Add OpenRouter specific arguments here
        parser.add_argument(
            "--openrouter.api_key",
            type=str,
            default=None,
            help="OpenRouter API key for authenticating requests."
        )
        pass

    def config(self) -> "bittensor.Config":
        """
        Provides the configuration for the OpenRouterMiner.

        Returns:
            bittensor.Config:
                A configuration object specific to the OpenRouterMiner.
        """
        parser = argparse.ArgumentParser(description="OpenRouter Miner Configs")
        self.add_args(parser)
        return bittensor.config(parser)

    def __init__(self, *args, **kwargs):
        super(OpenRouterMiner, self).__init__(*args, **kwargs)

        # Load the configuration for the miner
        config = self.config

        # Additional configurations
        # Set up any additional initializations here

        self.openrouter_api_key = config.openrouter.api_key
        # Check if the API key is provided
        if self.openrouter_api_key is None:
            raise ValueError(
                "OpenRouter API key is required. Please provide it via command-line argument '--openrouter.api_key' or environment variable.")

    def prompt(self, synapse: Prompting) -> Prompting:
        """
        Overrides the Miner's abstract `prompt` method to process incoming requests using OpenRouter.

        Args:
            synapse (Prompting):
                The incoming request object.

        Returns:
            Prompting:
                The response object containing the model's generated completion.
        """

        # Let's collect the synapse data.
        character_info = synapse.character_info  # Character info used in sys prompt
        character_name = synapse.character_name  # Character name
        user_names = synapse.user_names  # List of users' names
        char_names = synapse.char_names  # List of other AI character names
        messages = synapse.messages  # List of messages

        # Constructing the prompt string
        prompt_string = "<|im_start|>system\n"
        prompt_string += messages[0].content if len(messages) > 0 else "" # Add the system prompt
        char_names_str = ', '.join(char_names)  # Joining all AI character names with commas
        prompt_string += f"You're {character_name} in this fictional never-ending roleplay with {char_names_str}.\n"
        prompt_string += f"[{character_name}'s info: {character_info}]\n"
        prompt_string += "<|im_end|>\n"

        # Loop through messages and construct the prompt
        for i, message in enumerate(messages[1:]):
            name = message.name
            content = message.content

            # Determine the role based on the name
            if name in user_names:
                role = 'user'
            elif name in char_names:
                role = 'assistant'
            else:
                role = 'assistant'  # Defaulting to assistant if not found

            # Append the message to the prompt string
            prompt_string += f"<|im_start|>{role}\n{name}: {content}<|im_end|>\n"

        # Append a line indicating response from the current character
        prompt_string += f"<|im_start|>assistant\n{character_name}: "

        bittensor.logging.info(f"Prompt being passed to openrouter:\n{prompt_string}")

        all_names = user_names + char_names
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "HTTP-Referer": "https://royaltensor.com",
                "X-Title": "RoyalTensor"
            },
            data=json.dumps({
                "prompt": prompt_string,
                "transforms": ["middle-out"],
                "model": "open-orca/mistral-7b-openorca",  # Adjust as needed
                "max_tokens": 500,
                "stop": all_names,
                "temperature": 0.8,
            })
        )

        # Handle the response and set the completion
        response_data = response.json()

        # Extract the text from the response
        if 'choices' in response_data and len(response_data['choices']) > 0:
            response_text = response_data['choices'][0].get('text', '')
        else:
            response_text = "Unable to get response!?"

        bittensor.logging.info(f"We got this response from openrouter:\n{response_text}")
        
        # Set the extracted text as the completion
        synapse.completion = response_text

        return synapse


if __name__ == "__main__":
    """
    Main execution point for the OpenRouterMiner.
    """
    with OpenRouterMiner():
        while True:
            print("running...", time.time())
            time.sleep(1)
