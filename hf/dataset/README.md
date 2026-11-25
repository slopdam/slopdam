---
license: mit
language:
  - en
  - ko
pretty_name: "log-slop: AI-style traces in log messages, with clean outputs"
size_categories:
  - 10K<n<100K
task_categories:
  - text-generation
  - token-classification
tags:
  - logging
  - text-cleaning
  - em-dash
  - emoji
  - korean
  - slopdam
  - synthetic
configs:
  - config_name: default
    default: true
    data_files:
      - split: train
        path: data/train.jsonl
      - split: test
        path: data/test.jsonl
  - config_name: conformance
    data_files:
      - split: test
        path: conformance/test.jsonl
---

# log-slop

Log and console messages in English and Korean with the traces AI coding tools tend to leave in them (em dashes and the Hangul `ㅡ`, emoji, markdown bold and headings, curly quotes, separator lines, invisible characters, full-width punctuation), each paired with the cleaned text in two styles and the exact position of every trace.

```
input : ✅ **Saved** 3 rows — done! 🎉
reader: Saved 3 rows: done!
dev   : [OK] Saved 3 rows - done!
```

The labels are produced by [slopdam](https://github.com/slopdam/slopdam) 0.6.0, a deterministic cleaner with the same output in Python, JavaScript, Go and Java. They are what slopdam does, not human judgments.

## Subsets

| Subset | Split | Rows | What it is |
|---|---|---|---|
| `default` | train | 20,000 | Generated messages, half English, half Korean |
| `default` | test | 2,000 | Same distribution; no input appears in both splits |
| `conformance` | test | 101 | slopdam's language-neutral conformance cases, hand-written edge cases |

```python
from datasets import load_dataset

ds = load_dataset("slopdam/log-slop")                   # train and test
edge = load_dataset("slopdam/log-slop", "conformance")  # the spec's cases
```

## Fields (`default`)

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `train-00042`, `test-00007` |
| `lang` | string | `en` or `ko` |
| `input` | string | The message as an AI assistant might write it |
| `reader` | string | Cleaned for people: dashes become `: ` or `~`, emoji and markdown go, `!` after Hangul becomes `.` |
| `dev` | string | Cleaned for tools: dashes become ` - `, status emoji become `[OK]`, `[FAIL]`, `[WARN]` |
| `reader_strong` | string | `reader` at the `strong` level, which also drops filler words such as `성공적으로` |
| `changed` | bool | Whether `reader` differs from `input` |
| `injected` | list of strings | Which kinds of trace the generator inserted (`inline_dash`, `pictograph`, `bold`, ...); empty for clean messages and hard negatives |
| `rule_ids` | list of strings | slopdam rule IDs found in `input` (`dash.run`, `emoji.pictograph`, ...) |
| `findings` | list of objects | One per trace, with `rule_id`, `start`, `end` (code point offsets into `input`), `text` and `fix` (`null` when the rule only reports) |

About 21% of the rows need no change. Half of those are hard negatives: text that looks risky but must stay as it is, such as `--dry-run`, `user_id=42`, URLs and file paths. A cleaner that touches them is wrong.

The `conformance` subset has `id`, `group`, `input`, `options` (JSON text: `level`, `dash_inline`, `log_level`), `reader` and `dev`.

## How it was made

`hf/dataset/generate.py` in the slopdam repository writes every file from a fixed seed (`20261125`): it fills 27 English and 27 Korean message templates (deployments, databases, payments, jobs, caches) with names, numbers, paths, URLs and `key=value` pairs, injects one to four kinds of trace at random, and labels the result with slopdam. Running it again gives byte-identical files; `stats.json` records the SHA-256 of each one. No text was collected from people, websites or code repositories.

| Rule (in `train`) | Rows |
|---|---:|
| `dash.run` | 4,906 |
| `emoji.pictograph` | 4,215 |
| `punct.arrow` | 2,176 |
| `punct.bullet` | 2,147 |
| `tone.chatty` (report only) | 2,129 |
| `width.fullwidth` | 2,065 |
| `punct.ellipsis` | 2,061 |
| `md.emphasis` | 1,983 |
| `space.invisible` | 1,882 |
| `md.heading` | 1,811 |
| `quote.single`, `quote.double` | 2,179 |
| `md.hr`, `dash.ascii-run` | 1,071 |
| `tone.exclaim` | 544 |

## Uses

- Evaluate a cleaner, formatter or prompt that removes AI-style traces from short operational text: compare its output with `reader` or `dev`, and check that hard negatives stay unchanged.
- Train or test span detection with `findings`.
- Regression tests for slopdam ports and integrations.

## Limits

- The messages are synthetic and short. Real logs have more variety, longer lines and other languages.
- "Correct" means "what slopdam outputs". Where slopdam is conservative (it keeps an English `!`, and a character glued to the end of a URL counts as part of the URL), the labels are too.
- This dataset is not for detecting whether text was written by AI. None of these traces proves that, and slopdam does not try to decide it.

## License and citation

MIT, like slopdam. The text was written for this dataset.

```bibtex
@misc{slopdam_log_slop_2026,
  title  = {log-slop: AI-style traces in log messages, with clean outputs},
  author = {The slopdam Authors},
  year   = {2026},
  url    = {https://huggingface.co/datasets/slopdam/log-slop}
}
```

## 한국어 요약

AI 코딩 도구가 로그 메시지에 남기는 흔적(긴 대시와 한글 `ㅡ`, 이모지, 마크다운, 둥근 따옴표, 구분선, 보이지 않는 문자, 전각 문장 부호)이 들어간 한국어와 영어 메시지 22,000개입니다. 메시지마다 사람용(`reader`)과 도구용(`dev`)으로 정리한 결과, 흔적마다의 위치와 규칙 ID가 함께 있습니다. 라벨은 slopdam 0.6.0이 만든 결정적 결과이고, 바뀌면 안 되는 문장(옵션, URL, 경로, `key=value`)도 섞여 있어 잘못 고치는지도 확인할 수 있습니다. 문장은 모두 이 데이터셋을 위해 생성했으며, AI가 쓴 글인지 판별하는 용도는 아닙니다.
