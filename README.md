
<div align="center">

# **Bittensor: Roleplay Subnet #32** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/bittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

---

### Frontier of Gaming and Roleplay <!-- omit in toc -->

[Bittensor Discord](https://discord.gg/bittensor) • [Taostats Explorer](https://taostats.io/) • [Bittensor Whitepaper](https://bittensor.com/whitepaper)

</div>

---

This place is all about making roleplaying in games way cooler. Our subnet is specifically tailored for roleplaying applications, leveraging the power of large language models to create immersive, character-driven experiences. This technology holds enormous potential for integration into video games, offering a new dimension to GameFi. We think this could really change the way we play games.
# What's This All About?
The Bittensor network introduces specialized subnets, each with its unique value proposition. The Roleplay Subnet is a niche within this ecosystem, focusing on creating interactive, AI-driven characters for various applications, including gaming and virtual interactions. Our technology enables dynamic, responsive character interactions, enhancing the roleplay experience in gaming environments.


In this project, we've got everything you need to get these AI characters up and running. It's not just us working on it, either. Everyone who mines and validates in our subnet helps make these characters seem even more real. We're all about creating a cool experience that everyone can enjoy.</div>

---

# Installation
This repository requires python3.8 or higher. To install, simply clone this repository and install the requirements.
```bash
git clone https://github.com/RoyalTensor/roleplay.git
cd roleplay
python -m pip install -r requirements.txt
python -m pip install -e .
```

If you are running a specific miner or validator, you might need install its specific requirements. For example, the Mistral Open-Orca miner may require you to run:

```bash
cd neurons/miners/mistral7b-openorca
python -m pip install -r requirements.txt
```



---

Prior to running a miner or validator, you must [create a wallet](https://github.com/opentensor/docs/blob/main/reference/btcli.md) and [register the wallet to netuid 32](https://github.com/opentensor/docs/blob/main/subnetworks/registration.md). Once you have done so, you can run the miner and validator with the following commands from the project root.
``` bash
# Mistral Open Orca miner (Requires A6000 or better)
python -m neurons.miners.vicuna.miner --netuid 32 --wallet.name <wallet name>  --wallet.hotkey <wallet hotkey> --logging.debug --logging.trace --axon.port <open port>

# If you have PM2, we recommend this instead:
pm2 start neurons/miners/mistral7b-openorca/miner.py --name roleplayMiner --interpreter python3 --max-restarts 100 -- --netuid 32 --wallet.name <wallet name>  --wallet.hotkey <wallet hotkey> --logging.debug --logging.trace --axon.port <open port>
```

``` bash
# Open AI Miner (API mining, requires OpenAI account)
python -m neurons.miners.openai.miner --openai.api_key "openai key" --netuid 32 --wallet.name <miner wallet>  --wallet.hotkey <miner hotkey> --logging.debug --logging.trace --axon.port <open port>

# If you have PM2, we recommend this instead:
pm2 start neurons/miners/openai/miner.py --name openaiMiner --interpreter python3 --max-restarts 100 -- --netuid 32  --wallet.name <miner wallet>  --wallet.hotkey <miner hotkey> --logging.debug --logging.trace --axon.port <an open port> --openai.api_key "sk-your API key"
```

``` bash
# OpenRouter Miner (API mining, requires Openrouter account)
python -m neurons.miners.openrouter.miner --openrouter.api_key "openrouter key" --netuid 32 --wallet.name <wallet name>  --wallet.hotkey <hotkey name> --logging.debug --logging.trace --axon.port <open port>

# If you have PM2, we recommend this instead:
pm2 start neurons/miners/openrouter/miner.py --name openrouterMiner --interpreter python3 --max-restarts 100 -- --netuid 32  --wallet.name <wallet name>  --wallet.hotkey <hotkey name> --logging.debug --logging.trace --axon.port <open port> --openrouter.api_key "openrouter key"
```

``` bash
# To run the validator
python -m neurons.validators.validator --netuid 32 --wallet.name <wallet name>  --wallet.hotkey <wallet hotkey> --logging.debug --logging.trace --axon.port <open port>

# If you have PM2, we recommend this instead:
pm2 start neurons/validators/validator.py  --name roleplayValidator --interpreter python3 --max-restarts 100 -- --netuid 32 --wallet.name <wallet name>  --wallet.hotkey <wallet hotkey> --logging.debug --logging.trace --axon.port <open port>
```


---

## Potential and Future Developments

Our Roleplay Subnet is more than just tech; it's a new way to play and tell stories in games. We're really excited to see how it can fit into different games and help grow GameFi as well as the broad gaming industry. This is a project for everyone who loves gaming, and we can't wait to see what we can all create together. Special thanks to Opentensor team and SN1 text-prompting team for making this all possible.


---


## License
This repository is licensed under the MIT License.
```text
# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

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
```
