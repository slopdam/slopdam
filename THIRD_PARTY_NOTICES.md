# Third-Party Notices

External components that slopdam includes or uses, and their licenses. The policy for adding new ones is in [CONTRIBUTING.md](CONTRIBUTING.md#dependencies-and-data).

## Current state (0.9.1)

- **Runtime dependencies: none.** slopdam uses only the Python standard library.
- **Bundled third-party code or data: none.**

## Optional extra `slopdam[chatter]` (not installed by default)

| Component | Used for | License (SPDX) |
|---|---|---|
| [transformers](https://pypi.org/project/transformers/) | Loading and running the chatter model | `Apache-2.0` |
| [PyTorch](https://pypi.org/project/torch/) | Running the chatter model | `BSD-3-Clause` |
| [slopdam/chatter-tagger](https://huggingface.co/slopdam/chatter-tagger) | Model weights, downloaded from the Hugging Face Hub on first use, fine-tuned from [distilbert-base-multilingual-cased](https://huggingface.co/distilbert/distilbert-base-multilingual-cased) | `Apache-2.0` |

## Development dependencies (not shipped)

| Component | Used for | License (SPDX) |
|---|---|---|
| [pytest](https://pypi.org/project/pytest/) | Tests | `MIT` |
| [hatchling](https://pypi.org/project/hatchling/) | Build backend | `MIT` |

## Planned data

When any of the following is bundled, its full license text will be added here and the data file will record its source and version.

| Data | Purpose | License (SPDX) | Source |
|---|---|---|---|
| Unicode `emoji-data.txt` | Generate the emoji ranges | `Unicode-3.0` | https://www.unicode.org/Public/UCD/latest/ucd/emoji/ |
| Unicode `confusables.txt` (UTS #39) | Reference for dash look-alikes | `Unicode-3.0` | https://www.unicode.org/Public/security/latest/ |
| Unicode license text | | | https://www.unicode.org/license.txt |
