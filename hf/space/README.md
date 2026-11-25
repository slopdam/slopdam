---
title: slopdam
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Strip em dashes, emoji and markdown from log messages
tags:
  - logging
  - text-cleaning
  - korean
---

# slopdam

Paste a log message and see what [slopdam](https://github.com/slopdam/slopdam) does with it: the `reader` output for people, the `dev` output for log files and tools, and every trace with its rule ID and position. It runs the `slopdam` package from PyPI; no model is involved.

Dataset with 22,000 labeled examples: [slopdam/log-slop](https://huggingface.co/datasets/slopdam/log-slop).
