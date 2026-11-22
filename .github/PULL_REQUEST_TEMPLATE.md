## What does this change?

## Checklist

- [ ] Every commit is signed off (`git commit -s`)
- [ ] Tests added or updated, and `python -m pytest` passes
- [ ] If output changes: `[output-change]` in the title, and a before and after example in CHANGELOG under "Output changes"
- [ ] If this is a new rule: inputs that must and must not match, expected `reader` and `dev` output, level, and an idempotency case (see CONTRIBUTING)
- [ ] No nested quantifiers in new regular expressions (ReDoS)
- [ ] If a document with a Korean version (`*.ko.md`) changed, it is updated too or the description says a translation is needed
