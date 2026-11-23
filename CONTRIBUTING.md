# Contributing

[English](CONTRIBUTING.md) | [한국어](CONTRIBUTING.ko.md)

Thank you for helping. This guide covers setup, the sign-off every commit needs, and what a rule change has to include.

## Getting started

```bash
pip install -e ".[test]"
python -m pytest
```

## Sign your commits (DCO)

slopdam uses the [Developer Certificate of Origin 1.1](https://developercertificate.org/) instead of a CLA. Every commit needs a `Signed-off-by` line, which `git commit -s` adds for you.

```bash
git commit -s -m "dash: detect halfwidth eu (U+FFDA)"
```

By signing off you confirm that you have the right to submit the change under the MIT license. The same applies to code written with AI tools: you are responsible for what you submit.

## Adding or changing a rule

A rule pull request needs all of the following (see the checklist in [docs/RULES.md](docs/RULES.md)):

1. **Inputs that must be caught.**
2. **Inputs that must not be caught**, such as dates, command line flags, CJK text or `ㅋㅋ`.
3. **Expected output for both profiles**, `reader` and `dev`.
4. **A level** (`basic`, `strong` or `strict`) and why.
5. **An idempotency case**: running the cleaner twice must give the same result.
6. **A ReDoS-safe pattern.** No nested quantifiers such as `(a+)+` and no overlapping alternatives inside a repetition such as `(a|a)*`. See [SECURITY.md](SECURITY.md).
7. **Provenance** for any list taken from another project, with a license on the allowlist below. Ideas from other tools are welcome; copied lists are not.
8. **Conformance cases.** Add the inputs from 1 and 2 to [spec/conformance.json](spec/conformance.json), run `python scripts/gen_spec.py`, and check the generated outputs in the diff. Ports in other languages pick up the rule from these cases.

## Changes to output

slopdam's output is the user's log format, so a change in output is a compatibility change.

- Add `[output-change]` to the pull request title.
- Add a before and after example under "Output changes" in [CHANGELOG.md](CHANGELOG.md).
- Versioning follows the output stability policy in [GOVERNANCE.md](GOVERNANCE.md).

## Dependencies and data

slopdam has no runtime dependencies, and we want to keep it that way.

| Kind | Allowed licenses (SPDX) |
|---|---|
| Optional runtime dependency | `MIT`, `BSD-2-Clause`, `BSD-3-Clause`, `Apache-2.0`, `ISC`, `PSF-2.0`, `CNRI-Python` |
| Bundled data | `Unicode-3.0`, `MIT`, `CC0-1.0` |
| Not accepted | `GPL-*`, `AGPL-*`, `LGPL-*`, `SSPL-*`, or no stated license |

A pull request that adds a dependency or data file also updates [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Commits and pull requests

- Commit subjects follow `<rule group or area>: <summary>`, for example `emoji: handle flag sequences` or `cli: add json output`.
- One topic per pull request.
- The repository has to pass its own linter: no em dashes, decorative emoji or separator lines in log strings under `src/` or in commit messages (`slopdam check src/`). Rule definitions, tests and examples in the docs are the exception.
- Documentation is written in English first. If you change a document that has a Korean version (`*.ko.md`), update it in the same pull request or say in the description that it needs a translation.

## Code of Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
