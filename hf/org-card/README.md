---
title: README
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: static
pinned: false
---

<p align="center">
  <img src="https://raw.githubusercontent.com/slopdam/slopdam/main/docs/assets/logo.png" alt="slopdam logo" width="96">
</p>

<p align="center"><b>Em dashes, emoji and markdown stay out of your logs.</b><br>
AI 코딩 도구가 로그에 남기는 흔적을 걷어냅니다.</p>

```
input : ✅ **Saved** 3 rows — done! 🎉
reader: Saved 3 rows: done!
dev   : [OK] Saved 3 rows - done!
```

slopdam is an open-source logger formatter and linter. It removes the traces AI coding tools leave in log messages and console output (em dashes and the Korean `ㅡ`, decorative emoji, separator lines, markdown bold, curly quotes, invisible characters) with deterministic rules, not a model. Python, JavaScript, Go and Java give the same output, checked against one shared spec.

| | |
|---|---|
| [Try it](https://huggingface.co/spaces/slopdam/slopdam) | Paste a log message and see the cleaned text in your browser |
| [log-slop](https://huggingface.co/datasets/slopdam/log-slop) | 110,000 English and Korean log messages with traces, clean outputs, rewrite targets and spans |
| [GitHub](https://github.com/slopdam/slopdam) | Source, rules and docs (MIT) |

```bash
pip install slopdam          # Python, with logging, loguru and structlog
npm install @slopdam/core    # JavaScript, with pino, winston and ESLint
```
