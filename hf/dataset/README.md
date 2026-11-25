---
license: mit
language:
  - en
  - ko
pretty_name: "log-slop: AI-style traces in log messages, with clean outputs"
size_categories:
  - 100K<n<1M
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
      - split: validation
        path: data/validation.jsonl
      - split: test
        path: data/test.jsonl
  - config_name: conformance
    data_files:
      - split: test
        path: conformance/test.jsonl
---

# log-slop

Log and console messages in English and Korean with the traces AI coding tools tend to leave in them (em dashes and the Hangul `ㅡ`, emoji, markdown bold, headings and code fences, curly quotes, separator lines, invisible characters, full-width punctuation, chatty openers), each paired with the cleaned text in two styles, a rewrite target, and the exact position of every trace.

```
input : ✅ **Saved** 3 rows — done! 🎉
reader: Saved 3 rows: done!
dev   : [OK] Saved 3 rows - done!

input : Great news! Successfully rolled back auth (2–7)
reader: Great news! Successfully rolled back auth (2~7)
target: Rolled back auth (2~7)
```

The `reader`, `dev` and `findings` labels are produced by [slopdam](https://github.com/slopdam/slopdam) 0.6.0, a deterministic cleaner with the same output in Python, JavaScript, Go and Java. They are what slopdam does, not human judgments. `target` goes one step further: it also drops the chatty openers and filler adverbs the generator inserted, which slopdam's rules only report or do not see at all.

## Subsets

| Subset | Split | Rows | What it is |
|---|---|---|---|
| `default` | train | 100,000 | Generated messages, half English, half Korean, from 128 templates |
| `default` | validation | 5,000 | Same templates as train |
| `default` | test | 5,000 | 32 held-out templates that never appear in train or validation |
| `conformance` | test | 101 | slopdam's language-neutral conformance cases, hand-written edge cases |

No input appears twice, within or across splits. Because the test templates are held out, a model scored on `test` has to generalize to sentences it has not seen, not recall them.

```python
from datasets import load_dataset

ds = load_dataset("slopdam/log-slop")                   # train, validation, test
edge = load_dataset("slopdam/log-slop", "conformance")  # the spec's cases
```

## Fields (`default`)

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `train-000042`, `test-000007` |
| `lang` | string | `en` or `ko` |
| `template_id` | string | Which message template the row came from (`en-012`, `ko-044`); multi-line rows use the first item's |
| `input` | string | The message as an AI assistant might write it |
| `reader` | string | Cleaned for people: dashes become `: ` or `~`, emoji and markdown go, `!` after Hangul becomes `.` |
| `dev` | string | Cleaned for tools: dashes become ` - `, status emoji become `[OK]`, `[FAIL]`, `[WARN]` |
| `reader_strong` | string | `reader` at the `strong` level, which also drops Korean filler words such as `성공적으로` |
| `target` | string | `reader`, minus the chatty openers (`Great news!`, `Heads up:`, `살펴보겠습니다.`) and filler adverbs (`Successfully`, `성공적으로`) that were inserted; equal to `reader` on the 80% of rows without them |
| `changed` | bool | Whether `reader` differs from `input` |
| `injected` | list of strings | Which kinds of trace the generator inserted (`inline_dash`, `pictograph`, `bold`, `chatty`, `block`, ...); empty for clean messages and hard negatives |
| `rule_ids` | list of strings | slopdam rule IDs found in `input` (`dash.run`, `emoji.pictograph`, ...) |
| `findings` | list of objects | One per trace, with `rule_id`, `start`, `end` (code point offsets into `input`), `text` and `fix` (`null` when the rule only reports) |

18% of the rows have no trace at all. About half of those are hard negatives: text that looks risky but must stay as it is, such as `--dry-run`, `-> name`, `user_id=42`, `--since=2024-01-01`, URLs and file paths. A cleaner that touches them is wrong.

About 8% of the rows are multi-line summaries of two to four items under an optional title (`## Summary`, `**상태**`), the way assistants write them.

The `conformance` subset has `id`, `group`, `input`, `options` (JSON text: `level`, `dash_inline`, `log_level`), `reader` and `dev`.

## How it was made

`hf/dataset/generate.py` in the slopdam repository writes every file from a fixed seed (`20261125`): it fills 80 English and 80 Korean message templates (deployments, databases, CI, model training, payments, queues, containers) with names, numbers, versions, branches, paths, URLs and `key=value` pairs, injects one to four of 20 kinds of trace at random, and labels the result with slopdam. It builds each message twice, with and without the chatty and filler insertions, and the second copy cleaned by slopdam is `target`. Running it again gives byte-identical files; `stats.json` records the SHA-256 of each one. No text was collected from people, websites or code repositories.

| Rule (in `train`) | Rows |
|---|---:|
| `dash.run` | 22,536 |
| `emoji.pictograph` | 20,200 |
| `md.heading` | 11,754 |
| `md.emphasis` | 11,725 |
| `width.fullwidth` | 10,977 |
| `punct.arrow` | 10,958 |
| `dash.wave` | 10,939 |
| `dash.hyphen` | 10,825 |
| `punct.ellipsis` | 10,264 |
| `space.invisible` | 10,221 |
| `punct.bullet` | 9,457 |
| `md.fence` | 7,752 |
| `quote.single`, `quote.double` | 11,046 |
| `tone.exclaim` | 3,530 |
| `tone.chatty` (report only) | 3,228 |
| `md.hr`, `dash.cjk-run`, `dash.ascii-run` | 5,132 |

## Uses

- Evaluate a cleaner, formatter or prompt that removes AI-style traces from short operational text: compare its output with `reader` or `dev`, and check that hard negatives stay unchanged.
- Train or test span detection with `findings`.
- Train or test a rewriter that goes past the rules: compare its output with `target` on the held-out `test` split, especially the rows where `target` and `reader` differ.
- Regression tests for slopdam ports and integrations.

## Limits

- The messages are synthetic and short. Real logs have more variety, longer lines and other languages.
- "Correct" means "what slopdam outputs". Where slopdam is conservative (it keeps an English `!`, it leaves `**` around a URL, path or `key=value` alone, and a character glued to the end of a URL counts as part of the URL), the labels are too.
- `target` only knows the chatty phrases and filler words in the generator's lists. It is a narrow, synthetic rewrite task, not general copy editing.
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

AI 코딩 도구가 로그 메시지에 남기는 흔적(긴 대시와 한글 `ㅡ`, 이모지, 마크다운, 둥근 따옴표, 구분선, 보이지 않는 문자, 전각 문장 부호, 군더더기 인사말)이 들어간 한국어와 영어 메시지 110,000개입니다. 메시지마다 사람용(`reader`)과 도구용(`dev`)으로 정리한 결과, 흔적마다의 위치와 규칙 ID가 함께 있습니다. `target`은 규칙이 고치지 못하는 인사말(`좋은 소식입니다!`, `Heads up:`)과 부사(`성공적으로`, `Successfully`)까지 뺀 결과이고, test 분할은 학습에 쓰지 않은 템플릿 32개로만 만들어 모델의 일반화를 잴 수 있습니다. 라벨은 slopdam 0.6.0이 만든 결정적 결과이고, 바뀌면 안 되는 문장(옵션, URL, 경로, `key=value`)도 섞여 있어 잘못 고치는지도 확인할 수 있습니다. 문장은 모두 이 데이터셋을 위해 생성했으며, AI가 쓴 글인지 판별하는 용도는 아닙니다.
