# Governance

[English](GOVERNANCE.md) | [한국어](GOVERNANCE.ko.md)

## Roles

| Role | Can | How to become one |
|---|---|---|
| Contributor | Open issues and pull requests, review | Anyone |
| Committer | Approve and merge pull requests, triage issues | Nominated by a maintainer after five or more substantial merged pull requests |
| Maintainer | Release, set the roadmap, handle security reports, grant roles | Chosen from committers by agreement of the maintainers |

The founder is the only maintainer for now. The decision rules below apply in full once there are three maintainers.

## Decisions

- Regular pull requests: one committer approval.
- **Output changes** (`[output-change]`): two approvals, at least one from a maintainer.
- Changes to the license, this document, or the profile and level system: agreement of all maintainers, after a public discussion of at least 7 days.
- If maintainers cannot agree, a majority vote decides; on a tie, the founder decides.

## Versioning and output stability

slopdam changes the format of people's logs, so a change in output is a compatibility change. We follow [Semantic Versioning](https://semver.org/) and treat **the output for existing input** as part of the public API.

| Change | While 0.x | From 1.0 |
|---|---|---|
| Bug fix, including clear false positives | Patch | Patch |
| New rule, off by default or `strict` only | Patch | Minor |
| New rule, on by default in `basic` | Minor | **Major**, or ship it off by default until the next major |
| Different output from an existing rule | Minor | Major |
| Unicode data update | Minor | Minor, listing newly matched characters in the changelog |
| Different default profile or level | Minor | Major |

From 1.0, users who need fixed output will be able to pin a rule set version (for example `ruleset = "1.0"`).

## Releases

- Pushing a tag `vX.Y.Z` publishes to PyPI through GitHub Actions with Trusted Publishing.
- Release notes come from [CHANGELOG.md](CHANGELOG.md).

## Name and trademark

- The maintainers manage the project name and logo.
- Forks and redistribution are free under the MIT license. Please do not publish packages under the same name in a way that could be mistaken for the official release.
