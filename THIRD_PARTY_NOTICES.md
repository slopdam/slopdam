# Third-Party Notices

External components that slopdam includes or uses, and their licenses. The policy for adding new ones is in [CONTRIBUTING.md](CONTRIBUTING.md#dependencies-and-data).

## Current state (0.7.0)

- **Runtime dependencies: none.** slopdam uses only the Python standard library.
- **Bundled third-party code or data: none.**

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
