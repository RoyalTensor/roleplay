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
# DEALINGS IN
#  THE SOFTWARE.

import time
import torch
import random
import bittensor as bt
import random

from loguru import logger
from typing import List
from dataclasses import asdict
from prompting.validators.event import EventSchema
from prompting.validators.misc import ttl_get_block
from prompting.validators.prompts import followup_prompt, answer_prompt, augment_prompt
from prompting.validators.utils import check_uid_availability
from prompting.validators.tasks import (
    RoleplayTask,

    create_message_from_description_task,
)
from prompting.protocol import Message

from prompting.validators.characterset import CharacterSet, Character

import prompting

import pdb


def get_random_uids(self, k: int, exclude: List[int] = None) -> torch.LongTensor:
    """Returns k available random uids from the metagraph.
    Args:
        k (int): Number of uids to return.
        exclude (List[int]): List of uids to exclude from the random sampling.
    Returns:
        uids (torch.LongTensor): Randomly sampled available uids.
    Notes:
        If `k` is larger than the number of available `uids`, set `k` to the number of available `uids`.
    """
    candidate_uids = []
    avail_uids = []

    for uid in range(self.metagraph.n.item()):
        uid_is_available = check_uid_availability(
            self.metagraph, uid, self.config.neuron.vpermit_tao_limit
        )
        uid_is_not_excluded = exclude is None or uid not in exclude

        if uid_is_available and uid_is_not_excluded:
            candidate_uids.append(uid)

    # If not enough candidate_uids, use all available uids
    if len(candidate_uids) < k:
        k = len(candidate_uids)

    uids = (
        torch.tensor(random.sample(candidate_uids, k))
        if candidate_uids
        else torch.LongTensor([])
    )
    return uids


def restrict_format_followup_responses(
    self, responses: List[bt.Synapse], task_name: str
):
    # Restrict the format of acceptable followup completions.
    for response in responses:
        # remove leading and trailing periods
        completion = response.completion.strip(".")

        if "followup" in task_name and len(completion) > 0:
            # take maximum of 40 words
            max_words = 40
            if "?" in completion:
                # take first question that is found and only use the sentence before the question mark
                completion = completion.split("?")[0].split(".")[-1]
                response.completion = " ".join(completion.split(" ")[-max_words:]) + "?"
            else:
                # otherwise take the last sentence
                completion = completion.split(".")[-1].split(".")[-1]
                response.completion = " ".join(completion.split(" ")[-max_words:])


def compute_rewards(
    self, task: RoleplayTask, responses: List[bt.Synapse], task_name: str, event: dict
) -> torch.FloatTensor:
    # Compute the rewards for the responses given the prompt.
    rewards: torch.FloatTensor = torch.zeros(len(responses), dtype=torch.float32).to(
        self.device
    )

    # Computes the rewards for the responses given the prompt.
    for weight_i, reward_fn_i in zip(self.reward_weights, self.reward_functions):
        reward_i_normalized, reward_event = reward_fn_i.apply(
            task.base_text, responses, task_name
        )
        rewards += weight_i * reward_i_normalized.to(self.device)
        if not self.config.neuron.disable_log_rewards:
            event.update(reward_event)
        bt.logging.trace(str(reward_fn_i.name), reward_i_normalized.tolist())
    

    for masking_fn_i in self.masking_functions:
        mask_i_normalized, reward_event = masking_fn_i.apply(
            task.base_text, responses, task_name
        )
        rewards *= mask_i_normalized.to(self.device)  # includes diversity

        if not self.config.neuron.disable_log_rewards:
            event.update(reward_event)
        bt.logging.trace(str(masking_fn_i.name), mask_i_normalized.tolist())
        

    for penalty_fn_i in self.penalty_functions:
        (
            raw_penalty_i,
            adjusted_penalty_i,
            applied_penalty_i,
        ) = penalty_fn_i.apply_penalties(responses, task)
        rewards *= applied_penalty_i.to(self.device)

        if not self.config.neuron.disable_log_rewards:
            event[penalty_fn_i.name + "_raw"] = raw_penalty_i.tolist()
            event[penalty_fn_i.name + "_adjusted"] = adjusted_penalty_i.tolist()
            event[penalty_fn_i.name + "_applied"] = applied_penalty_i.tolist()
        bt.logging.trace(str(penalty_fn_i.name), applied_penalty_i.tolist())

    return rewards


async def run_step(
    self, task: RoleplayTask, k: int, timeout: float, exclude: list = []
):
    task_name = task.task_name

    task_message: Message = {
        "name": "system",
        "content": task.compose_instruction(), # Essentially the instruction (e.g. "Your task is...")
    }
    
    prompt = task.compose_prompt()
    

    character: Character = task.character

    bt.logging.debug("run_step", task_name)

    # Record event start time.
    event = {"name": task_name, "task_type": task.task_type}
    start_time = time.time()
    # Get the list of uids to query for this step.
    uids = get_random_uids(self, k=k, exclude=exclude).to(self.device)
    axons = [self.metagraph.axons[uid] for uid in uids]

    synapse = prompting.protocol.Prompting(
        character_name=character["name"],
        character_info=character["description"],
        char_names=[character["name"]],
        user_names=["user"],
        messages=[task_message],
        criteria=task.get_criteria_strs(),
    )

    # Make calls to the network with the prompt.
    responses: List[bt.Synapse] = await self.dendrite(
        axons=axons,
        synapse=synapse,
        timeout=timeout,
    )

    # Update blacklist with completions so that n-gram filtering can be applied
    self.blacklist.add(
        [response.completion for response in responses if response.completion]
    )

    restrict_format_followup_responses(self, responses, task_name)

    rewards : torch.FloatTensor  = compute_rewards(self, task, responses, task_name, event)
    
    # Train the gating model based on the predicted scores and the actual rewards.
    gating_scores: torch.FloatTensor = self.gating_model(prompt).to(self.device)
    gating_loss: torch.FloatTensor = self.gating_model.backward(
        scores=gating_scores[uids], rewards=rewards
    )

    # Find the best completion given the rewards vector.
    completions: List[str] = [comp.completion for comp in responses]
    completion_status_message: List[str] = [
        str(comp.dendrite.status_message) for comp in responses
    ]
    completion_status_codes: List[str] = [
        str(comp.dendrite.status_code) for comp in responses
    ]

    best: str = completions[rewards.argmax(dim=0)].strip()

    # Get completion times
    completion_times: List[float] = [
        comp.dendrite.process_time if comp.dendrite.process_time != None else 0
        for comp in responses
    ]

    # Compute forward pass rewards, assumes followup_uids and answer_uids are mutually exclusive.
    # shape: [ metagraph.n ]
    scattered_rewards: torch.FloatTensor = self.moving_averaged_scores.scatter(
        0, uids, rewards
    ).to(self.device)

    # Update moving_averaged_scores with rewards produced by this step.
    # shape: [ metagraph.n ]
    alpha: float = self.config.neuron.moving_average_alpha
    self.moving_averaged_scores: torch.FloatTensor = alpha * scattered_rewards + (
        1 - alpha
    ) * self.moving_averaged_scores.to(self.device)
    
    # Log the step event.
    event.update(
        {
            "block": ttl_get_block(self),
            "step_length": time.time() - start_time,
            "prompt": prompt,
            "uids": uids.tolist(),
            "completions": completions,
            "completion_times": completion_times,
            "completion_status_messages": completion_status_message,
            "completion_status_codes": completion_status_codes,
            "rewards": rewards.tolist(),
            "gating_loss": gating_loss.item(),
            "best": best,
        }
    )

    bt.logging.debug("event:", str(event))
    if not self.config.neuron.dont_save_events:
        logger.log("EVENTS", "events", **event)

    # Log the event to wandb.
    if not self.config.wandb.off:
        wandb_event = EventSchema.from_dict(
            event, self.config.neuron.disable_log_rewards
        )
        self.wandb.log(asdict(wandb_event))

    # Return the event.
    return event


async def run_character_flow(self):
    # Choose some random character
    character: Character = next(self.character_set)

    random_sentence_cutoff = random.randint(20, 30)

    # Generate a message from the description
    description = ".".join(
        character["description"].split(".", maxsplit=random_sentence_cutoff)[:-1]
    )
    message_from_description_task: RoleplayTask = create_message_from_description_task(
        f"Your name is {character['name']}. Here is your character description: {description}.",
        character,
    )

    message_from_description_event = await run_step(
        self,
        task=message_from_description_task,
        k=self.config.neuron.followup_sample_size,
        timeout=self.config.neuron.followup_timeout,
    )



async def forward(self):
    # Definition of flow to be executed at forward step
    # await questions_and_answers_around_summary_flow(self)
    await run_character_flow(self)
