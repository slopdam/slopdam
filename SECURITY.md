# Security Policy

[English](SECURITY.md) | [한국어](SECURITY.ko.md)

## Supported versions

| Version | Security fixes |
|---|---|
| Latest minor release (0.x) | Yes |
| Older releases | No |

## Reporting a vulnerability

Please do not open a public issue. Use **Security > Report a vulnerability** on the [repository page](https://github.com/slopdam/slopdam/security/advisories/new) to report privately. We aim to acknowledge a report within 3 business days and to share a first assessment within 14 days.

## Threats that matter for this project

slopdam runs regular expressions over untrusted input (log messages that may contain user data) on the hot path of a service.

| Threat | What can happen | Mitigation |
|---|---|---|
| ReDoS | A crafted message makes a pattern run in exponential time and stalls the service | No nested quantifiers (see CONTRIBUTING), fuzz tests, an optional message length limit |
| Log forging | Cleaning introduces a newline or control character and creates a fake log line | Replacements never produce newlines; covered by tests |
| Information loss | Cleaning removes something needed to investigate an incident | Tracebacks are never changed, the `dev` profile preserves status, the formatter never modifies the original record |
| Supply chain | A dependency or data file is tampered with | No runtime dependencies; data files are committed with the script that generates them; releases use PyPI Trusted Publishing |

We treat ReDoS, log forging and unintended loss of information as security issues.
