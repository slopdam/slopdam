# Roadmap

[English](ROADMAP.md) | [한국어](ROADMAP.ko.md)

slopdam keeps AI-generated traces out of logs and screens, in every language a team uses. This page says where the project is going and in what order. Dates are not promised; milestones ship when their checklist is done. Discussion and proposals are welcome in issues.

## The concept, in every language

Every implementation keeps the same four ideas:

1. **One engine, two profiles.** Detection is shared; `reader` writes plain text for people, `dev` writes text that is easy to grep and parse.
2. **Two places to stop slop.** At runtime, a formatter for the language's loggers cleans what is printed. Before merge, a linter finds traces in source code and fixes what it safely can.
3. **Deterministic and conservative.** The same input and settings always give the same output, cleaning twice changes nothing, and dates, flags, URLs, paths, code and CJK text are left alone. No model, no network.
4. **No runtime dependencies** in the core package of each language.

## How other languages stay consistent

```
spec/                      rule catalog + conformance cases (this repository)
  ├── Python   slopdam            reference implementation, CLI, pre-commit, GitHub Action
  ├── JS/TS    @slopdam/core      planned
  ├── Go       slopdam-go         planned
  ├── JVM      slopdam-java       planned
  └── Rust     slopdam (crate)    planned
```

- [spec/](spec/README.md) defines the behavior without reference to Python. A port is correct when it passes every case in `spec/conformance.json`, and its CI runs those cases.
- Each port lives in its own repository under the slopdam organization, so it uses its ecosystem's own build, test and release tools. It pins the spec version it implements.
- New rules land in the spec first, with conformance cases. Ports follow by passing the new cases.
- Until a native package exists, any language can use the CLI: `slopdam check` for source code, `slopdam clean` in a pipe for output, plus the pre-commit hook and GitHub Action.

## Planned packages

| Language | Package | Runtime integration | Lint integration |
|---|---|---|---|
| Python | `slopdam` (PyPI) | `logging`; structlog and loguru next | `slopdam check` and `fix`, pre-commit, GitHub Action |
| JavaScript, TypeScript | `@slopdam/core` (npm) | pino, winston, `console` wrapper | ESLint plugin |
| Go | `github.com/slopdam/slopdam-go` | `slog.Handler`, zap core | `go vet` analyzer |
| Java, Kotlin | Maven Central | Logback converter, Log4j2 rewrite policy | CLI |
| Rust | `slopdam` (crates.io) | `tracing` layer, `log` | CLI |
| Any | CLI | `slopdam clean` in a pipe | CLI, pre-commit, GitHub Action |

## Milestones

### 0.3: language-neutral foundation (released)

- [x] Spec: rule catalog and conformance cases generated from the reference implementation and checked in CI
- [x] GitHub Action (`uses: slopdam/slopdam@v0.3.0`)
- [x] `check --format github` (pull request annotations) and `--format sarif` (code scanning)
- [x] Type information (`py.typed`) and package build checks in CI

### 0.4: Python integrations and rule quality (released)

- [x] structlog and loguru adapters
- [x] Property-based tests (idempotency, protected spans) and a benchmark in CI
- [x] `slopdam check -` to lint text from stdin, for editors and other tools

### 0.5: JavaScript and TypeScript

- [ ] `@slopdam/core` passing every conformance case, in Node.js and browsers
- [ ] pino and winston formatters
- [ ] `eslint-plugin-slopdam`: string arguments of log calls, with autofix

### 0.6: Go and the JVM

- [ ] Go module with an `slog.Handler` and a `go vet` analyzer
- [ ] Java library with a Logback converter and a Log4j2 rewrite policy

### 0.7: Rust and editors

- [ ] Rust crate with a `tracing` layer
- [ ] Editor support on top of `check --format json` (VS Code first)

### 1.0: stable

- [ ] Emoji ranges generated from Unicode `emoji-data.txt` instead of a hand-written table, so the spec is complete before it is frozen
- [ ] Spec version 1 frozen; output changes only in major versions
- [ ] Every port passes the full conformance suite in CI
- [ ] Documentation site with a rule reference generated from the spec

## Out of scope

- Deciding whether a text was written by AI. That cannot be done reliably, and slopdam does not need to know.
- Rewriting sentences with a language model. slopdam only applies deterministic rules.

## How to help

- Report a trace slopdam misses, or a change it should not have made, with the issue templates. Each confirmed case becomes a conformance case.
- Start a port: open an issue to claim a language, then implement the spec until `conformance.json` passes. Maintainers will create the repository under the organization.
- Read [CONTRIBUTING.md](CONTRIBUTING.md) first; every commit needs a DCO sign-off.
