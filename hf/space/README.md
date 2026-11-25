---
title: slopdam
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: static
app_file: index.html
pinned: false
license: mit
short_description: Strip em dashes, emoji and markdown from log messages
tags:
  - logging
  - text-cleaning
  - korean
---

# slopdam

Paste a log message and see what [slopdam](https://github.com/slopdam/slopdam) does with it: the `reader` output for people, the `dev` output for log files and tools, and every trace with its rule ID and position. It runs [`@slopdam/core`](https://www.npmjs.com/package/@slopdam/core) from npm in your browser, which gives the same output as the Python package; no model is involved and the text is not sent anywhere.

Dataset with 22,000 labeled examples: [slopdam/log-slop](https://huggingface.co/datasets/slopdam/log-slop).
