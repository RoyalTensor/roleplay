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

import copy
import torch
import asyncio
import bittensor as bt
from traceback import print_exception
import pdb

import prompting

from prompting.validators.characterset import CharacterSet, MockCharacterSet
from prompting.validators.gating import GatingModel, SentenceEmbedGatingModel
from prompting.validators.mock import MockDendrite, MockRewardModel, MockGatingModel

# Load local forward function.
from prompting.validators.config import add_args, check_config, config
from prompting.validators.forward import forward
from prompting.validators.utils import (
    checkpoint,
    should_reinit_wandb,
    reinit_wandb,
    load_state,
    save_state,
    init_wandb,
)
from prompting.validators.weights import should_set_weights, set_weights
from prompting.validators.misc import ttl_get_block

# Load gating models
from prompting.validators.reward import (
    Blacklist,
    NSFWRewardModel,
    MistralRewardModel,
    RelevanceRewardModel,
    DiversityRewardModel,
    RewardModelType,
)

from prompting.validators.penalty import (
    TaskValidationPenaltyModel,
    KeywordMatchPenaltyModel,
    ContentMatchPenaltyModel,
)


class neuron:
    @classmethod
    def check_config(cls, config: "bt.Config"):
        check_config(cls, config)

    @classmethod
    def add_args(cls, parser):
        add_args(cls, parser)

    @classmethod
    def config(cls):
        return config(cls)

    subtensor: "bt.subtensor"
    wallet: "bt.wallet"
    metagraph: "bt.metagraph"

    def init_characterset(self):
        bt.logging.debug("loading", "characterset")
        if self.config.neuron.mock_character_set:
            self.character_set = MockCharacterSet()
        else:
            self.character_set = CharacterSet()
        bt.logging.debug(str(self.character_set))

    def init_reward_models(self):
        bt.logging.debug("loading", "reward_functions")
        if self.config.neuron.mock_reward_models:
            self.reward_functions = []
            self.reward_weights = []
            self.blacklist = MockRewardModel(RewardModelType.blacklist.value)
            self.masking_functions = [
                self.blacklist,
                MockRewardModel(RewardModelType.nsfw.value),
            ]
            self.penalty_functions = [
                TaskValidationPenaltyModel(max_penalty=0.75),
                ContentMatchPenaltyModel(max_penalty=0.2),
                KeywordMatchPenaltyModel(max_penalty=1),
            ]
            bt.logging.debug(str(self.reward_functions))
        else:
            self.reward_weights = torch.tensor(
                [
                    self.config.reward.mistral_weight,
                ],
                dtype=torch.float32,
            ).to(self.device)

            bt.logging.debug("reward_weights", str(self.reward_weights))

            # Ensure reward function weights sum to 1.
            if self.reward_weights.sum() != 1:
                message = (
                    f"Reward function weights do not sum to 1 (Current sum: {self.reward_weights.sum()}.)"
                    f"Check your reward config file at `reward/config.py` or ensure that all your cli reward flags sum to 1."
                )
                bt.logging.error(message)
                raise Exception(message)

            self.reward_functions = [
                MistralRewardModel(device=self.device)
                if self.config.reward.mistral_weight > 0
                else MockRewardModel(RewardModelType.mistral.value),
            ]

            if len(self.reward_functions) != len(self.reward_weights):
                message = (
                    f"Length of reward function weights and reward functions do not match. "
                    f"Reward functions: {len(self.reward_functions)}, Reward weights: {len(self.reward_weights)}"
                )

                bt.logging.error(message)
                raise Exception(message)

            # Masking functions
            self.blacklist = (
                Blacklist()
                if not self.config.neuron.blacklist_off
                else MockRewardModel(RewardModelType.blacklist.value)
            )

            relevance_model = (
                RelevanceRewardModel(device=self.device)
                if not self.config.neuron.relevance_off
                else MockRewardModel(RewardModelType.relevance.value)
            )

            self.diversity_model = (
                DiversityRewardModel(device=self.device)
                if not self.config.neuron.diversity_off
                else MockRewardModel(RewardModelType.diversity.value)
            )

            nsfw_model = (
                NSFWRewardModel(device=self.device)
                if not self.config.neuron.nsfw_off
                else MockRewardModel(RewardModelType.nsfw.value)
            )

            self.masking_functions = [
                self.blacklist,
                # relevance_model, 
                # self.diversity_model,
                nsfw_model,
            ]

            self.penalty_functions = [
                TaskValidationPenaltyModel(max_penalty=0.6),
                ContentMatchPenaltyModel(max_penalty=0.2),
                KeywordMatchPenaltyModel(max_penalty=1),
            ]

            bt.logging.debug(str(self.reward_functions))
            bt.logging.debug(str(self.masking_functions))
            bt.logging.debug(str(self.penalty_functions))

    def __init__(self):
        self.config = neuron.config()
        self.check_config(self.config)
        bt.logging(config=self.config, logging_dir=self.config.neuron.full_path)
        print(self.config)
        bt.logging.info("neuron.__init__()")

        # Init device.
        bt.logging.debug("loading", "device")
        self.device = torch.device(self.config.neuron.device)
        bt.logging.debug(str(self.device))

        # Init subtensor
        bt.logging.debug("loading", "subtensor")
        self.subtensor = bt.subtensor(config=self.config)
        bt.logging.debug(str(self.subtensor))

        # Init wallet.
        bt.logging.debug("loading", "wallet")
        self.wallet = bt.wallet(config=self.config)
        self.wallet.create_if_non_existent()
        if not self.config.wallet._mock:
            if not self.subtensor.is_hotkey_registered_on_subnet(
                hotkey_ss58=self.wallet.hotkey.ss58_address, netuid=self.config.netuid
            ):
                raise Exception(
                    f"Wallet not currently registered on netuid {self.config.netuid}, please first register wallet before running"
                )

        bt.logging.debug(str(self.wallet))

        # Init metagraph.
        bt.logging.debug("loading", "metagraph")
        self.metagraph = bt.metagraph(
            netuid=self.config.netuid, network=self.subtensor.network, sync=False
        )  # Make sure not to sync without passing subtensor
        self.metagraph.sync(subtensor=self.subtensor)  # Sync metagraph with subtensor.
        self.hotkeys = copy.deepcopy(self.metagraph.hotkeys)
        bt.logging.debug(str(self.metagraph))

        # Init Weights.
        bt.logging.debug("loading", "moving_averaged_scores")
        self.moving_averaged_scores = torch.zeros((self.metagraph.n)).to(self.device)
        bt.logging.debug(str(self.moving_averaged_scores))

        self.init_characterset()

        # Init the gating model which learns which miners to select for each query.
        bt.logging.debug("loading", "gating_model")
        if not self.config.gating.num_uids:
            self.config.gating.num_uids = self.subtensor.max_n(self.config.netuid)

        if self.config.neuron.mock_gating_model:
            self.gating_model = MockGatingModel(self.metagraph.n.item())
        elif self.config.neuron.use_custom_gating_model:
            self.gating_model = SentenceEmbedGatingModel(
                metagraph=self.metagraph, config=self.config
            ).to(self.device)
        else:
            self.gating_model = GatingModel(
                metagraph=self.metagraph, config=self.config
            ).to(self.device)
        bt.logging.debug(str(self.gating_model))

        if not self.config.neuron.axon_off:
            bt.logging.debug("serving ip to chain...")
            try:
                axon = bt.axon(wallet=self.wallet, config=self.config)

                try:
                    self.subtensor.serve_axon(
                        netuid=self.config.netuid,
                        axon=axon,
                    )
                except Exception as e:
                    bt.logging.error(f"Failed to serve Axon with exception: {e}")
                    pass

                del axon
            except Exception as e:
                bt.logging.error(
                    f"Failed to create Axon initialize with exception: {e}"
                )
                pass

        else:
            bt.logging.debug("axon off, not serving ip to chain.")

        # Dendrite pool for querying the network during  training.
        bt.logging.debug("loading", "dendrite_pool")
        if self.config.neuron.mock_dendrite_pool:
            self.dendrite = MockDendrite()
        else:
            self.dendrite = bt.dendrite(wallet=self.wallet)
        bt.logging.debug(str(self.dendrite))

        self.init_reward_models()

        # Init the event loop.
        self.loop = asyncio.get_event_loop()

        # Init wandb.
        if not self.config.wandb.off:
            bt.logging.debug("loading", "wandb")
            init_wandb(self)

        if self.config.neuron.epoch_length_override:
            self.config.neuron.epoch_length = self.config.neuron.epoch_length_override
        else:
            self.config.neuron.epoch_length = 100

        self.prev_block = ttl_get_block(self)
        self.step = 0

    def should_update(self):
        cur_block = ttl_get_block(self)
        return (
            cur_block - self.prev_block > self.config.neuron.epoch_length
        )

    def run(self):
        bt.logging.info("run()")
        load_state(self)
        checkpoint(self)
        try:
            while True:
                if not self.wallet.hotkey.ss58_address in self.metagraph.hotkeys:
                    raise Exception(
                        f"Validator is not registered - hotkey {self.wallet.hotkey.ss58_address} not in metagraph"
                    )

                bt.logging.info(f"step({self.step}) block({ttl_get_block( self )})")

                # Run multiple forwards.
                async def run_forward():
                    coroutines = [
                        forward(self)
                        for _ in range(self.config.neuron.num_concurrent_forwards)
                    ]
                    await asyncio.gather(*coroutines)

                self.loop.run_until_complete(run_forward())

                
                if self.should_update():
                    # Resync the network state
                    checkpoint(self)
                    if should_set_weights(self):
                        # Set the weights on chain.
                        set_weights(self)
                        save_state(self)
                        
                    self.prev_block = ttl_get_block(self)
                    
                    

                # Rollover wandb to a new run.
                if should_reinit_wandb(self):
                    reinit_wandb(self)
                self.step += 1
        except Exception as err:
            bt.logging.error("Error in training loop", str(err))
            bt.logging.debug(print_exception(type(err), err, err.__traceback__))


def main():
    neuron().run()


if __name__ == "__main__":
    main()
