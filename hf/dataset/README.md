---
license: mit
language:
  - en
  - ko
  - ja
  - zh
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
  - japanese
  - chinese
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

Log and console messages in English, Korean, Japanese and Chinese with the traces AI coding tools tend to leave in them (em dashes and the Hangul `ㅡ`, emoji, markdown bold, headings and code fences, curly quotes, separator lines, invisible characters, full-width punctuation, chatty openers), alone or inside JSON lines, logfmt and timestamped log lines, each paired with the cleaned text in two styles, a rewrite target, and the exact position of every trace.

```
input : ✅ **Saved** 3 rows — done! 🎉
reader: Saved 3 rows: done!
dev   : [OK] Saved 3 rows - done!

input : Great news! Successfully rolled back auth (2–7)
reader: Great news! Successfully rolled back auth (2~7)
target: Rolled back auth (2~7)

input : {"level":"info","msg":"✅ Synced 3 records from “cdn” — done"}
reader: {"level":"info","msg":"Synced 3 records from \"cdn\": done"}

input : 🎉 要するに、1591行をCSVに書き出しました
reader: 要するに、1591行をCSVに書き出しました
target: 1591行をCSVに書き出しました
```

The `reader`, `dev` and `findings` labels are produced by [slopdam](https://github.com/slopdam/slopdam) 0.9.0, a deterministic cleaner with the same output in Python, JavaScript, Go and Java. They are what slopdam does, not human judgments. `target` goes one step further: it also drops the chatty openers and filler adverbs the generator inserted, which slopdam's rules only report or do not see at all.

## Subsets

| Subset | Split | Rows | What it is |
|---|---|---|---|
| `default` | train | 100,000 | Generated messages, 30% English, 30% Korean, 20% Japanese, 20% Chinese, from 192 templates |
| `default` | validation | 5,000 | Same templates as train |
| `default` | test | 5,000 | 48 held-out templates, and chatty openers, filler words and labels, that never appear in train or validation |
| `conformance` | test | 133 | slopdam's language-neutral conformance cases, hand-written edge cases |

No input appears twice, within or across splits. Because the test templates, openers (`FYI:`, `Excellent!`, `완벽합니다!`, `実は、`, `说实话，`), fillers (`Finally`, `순조롭게`) and labels (`宛先：`, `来源：`) are held out, a model scored on `test` has to generalize to phrases it has not seen, not recall them.

```python
from datasets import load_dataset

ds = load_dataset("slopdam/log-slop")                   # train, validation, test
edge = load_dataset("slopdam/log-slop", "conformance")  # the spec's cases
```

## Fields (`default`)

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `train-000042`, `test-000007` |
| `lang` | string | `en`, `ko`, `ja` or `zh` |
| `template_id` | string | Which message template the row came from (`en-012`, `ko-044`, `ja-007`); multi-line rows use the first item's |
| `input` | string | The message as an AI assistant might write it |
| `reader` | string | Cleaned for people: dashes become `: ` or `~`, emoji and markdown go, `!` after Hangul becomes `.` |
| `dev` | string | Cleaned for tools: dashes become ` - `, status emoji become `[OK]`, `[FAIL]`, `[WARN]` |
| `reader_strong` | string | `reader` at the `strong` level, which also drops Korean filler words such as `성공적으로` and about 80 known openers at the start of a line (`Great news!`, `Heads up:`, `살펴보겠습니다.`) |
| `target` | string | `reader`, minus the chatty openers (`Great news!`, `Heads up:`, `살펴보겠습니다.`) and filler adverbs (`Successfully`, `성공적으로`) that were inserted; equal to `reader` on the 80% of rows without them. Always `reader` with some characters deleted and at most one letter upper-cased |
| `changed` | bool | Whether `reader` differs from `input` |
| `injected` | list of strings | Which kinds of trace the generator inserted (`inline_dash`, `pictograph`, `bold`, `chatty`, `block`, ...); empty for clean messages and hard negatives |
| `rule_ids` | list of strings | slopdam rule IDs found in `input` (`dash.run`, `emoji.pictograph`, ...) |
| `findings` | list of objects | One per trace, with `rule_id`, `start`, `end` (code point offsets into `input`), `text` and `fix` (`null` when the rule only reports) |

23% of the rows have no trace at all. Most of those are hard negatives: text that looks risky but must stay as it is, such as `--dry-run`, `-> name`, `user_id=42`, `--since=2024-01-01`, URLs and file paths, and lines that start with a word that only looks like an opener (`Finally block ran in auth`, `결론 필드가 비어 있습니다`, `最後のハートビートは120ms前です`). A cleaner that touches them is wrong.

English openers that end in a comma or colon are sometimes followed by a lowercase word (`Great, saved 3 rows`); `target` capitalizes it again.

Japanese and Chinese keep their full-width punctuation (`、，：！（）`), which is correct there; slopdam only turns it into ASCII on lines without kana or CJK ideographs. Their openers usually run straight into the message (`さて、バックアップが完了しました`). 15% of their messages start with a label (`状態：`, `耗时：`), sometimes after an opener, and many of their hard negatives are a bare label and value (`状態：OK`): the label ends in `：` like many openers, but it is content.

4% of the rows are output that must come out byte for byte: Python tracebacks, ASCII and markdown tables, diff hunks and JSON data in `train` and `validation`; Java stack traces, Go panics, box-drawing tables and `kubectl` columns only in `test`. Their `template_id` starts with `shape-`.

About 10% are a traced message inside a log format, marked `json_line`, `logfmt` or `log_prefix` in `injected`: only the message changes, the structure stays valid (a curly quote inside a JSON string becomes `\"`). Openers and fillers are not used there, since they are judged at the start of a line.

About 8% of the rows are multi-line summaries of two to four items under an optional title (`## Summary`, `**상태**`), the way assistants write them.

The `conformance` subset has `id`, `group`, `input`, `options` (JSON text: `level`, `dash_inline`, `log_level`), `reader` and `dev`.

## How it was made

`hf/dataset/generate.py` in the slopdam repository writes every file from a fixed seed (`20261125`): it fills 80 English, 80 Korean, 40 Japanese and 40 Chinese message templates (deployments, databases, CI, model training, payments, queues, containers) with names, numbers, versions, branches, paths, URLs and `key=value` pairs, injects one to four of 20 kinds of trace at random, sometimes wraps the message in a log format, and labels the result with slopdam. It builds each message twice, with and without the chatty and filler insertions, and the second copy cleaned by slopdam is `target`. Running it again gives byte-identical files; `stats.json` records the SHA-256 of each one. No text was collected from people, websites or code repositories.

| Rule (in `train`) | Rows |
|---|---:|
| `dash.run` | 22,939 |
| `emoji.pictograph` | 21,911 |
| `punct.arrow` | 11,583 |
| `md.emphasis` | 11,530 |
| `dash.hyphen` | 11,508 |
| `dash.wave` | 11,039 |
| `punct.ellipsis` | 10,850 |
| `md.heading` | 10,698 |
| `space.invisible` | 10,112 |
| `punct.bullet` | 8,342 |
| `md.fence` | 6,765 |
| `width.fullwidth` | 6,644 |
| `quote.single`, `quote.double` | 11,682 |
| `tone.exclaim` | 2,104 |
| `md.hr`, `dash.cjk-run`, `dash.ascii-run` | 4,265 |
| `tone.chatty` (report only) | 250 |

Most openers are ones no rule knows, which is why `tone.chatty` is rare here while `target` differs from `reader` on 18% of rows.

## Uses

- Evaluate a cleaner, formatter or prompt that removes AI-style traces from short operational text: compare its output with `reader` or `dev`, and check that hard negatives stay unchanged.
- Train or test span detection with `findings`.
- Train or test a rewriter that goes past the rules: compare its output with `target` on the held-out `test` split, especially the rows where `target` and `reader` differ.
- Regression tests for slopdam ports and integrations.

## Limits

- The messages are synthetic and short. Real logs have more variety, longer lines and other languages. Japanese and Chinese have half as many templates as English and Korean.
- slopdam drops empty lines, so multi-line output with blank lines (a Go panic, a paragraph break) is not in the hard negatives.
- "Correct" means "what slopdam outputs". Where slopdam is conservative (it keeps an English `!`, it leaves `**` around a URL, path or `key=value` alone, and a character glued to the end of a URL counts as part of the URL), the labels are too.
- `target` only knows the chatty phrases and filler words in the generator's lists. It is a narrow, synthetic rewrite task, not general copy editing.
- This dataset is not for detecting whether text was written by AI. None of these traces proves that, and slopdam does not try to decide it.

## Baselines

slopdam's own rules at the `strong` level (`reader_strong`), and taggers trained on `train` to turn `reader` into `target` by deleting words (code in `hf/model/` of the slopdam repository). Rows with filler adverbs are left out of the opener rows:

| | slopdam 0.9.0 rules, `strong` | Character tagger, from scratch | DistilBERT, first try | [slopdam/chatter-tagger](https://huggingface.co/slopdam/chatter-tagger) |
|---|---:|---:|---:|---:|
| Job | about 80 listed openers | openers and fillers | openers and fillers | openers only, with a guard |
| `test`: unseen openers removed | 22.1% (90 of 407) | | 90.6% | 90.7% (84.3% counting openers ending in `：`) |
| `test`: other rows left unchanged | 100% | 96.0% | 99.8% | 100% |
| `test`: hard negatives left unchanged | 100% | 96.8% | 100% | 100% |
| Handwritten content lines left unchanged | | 4 of 12 | 10 of 12 | 20 of 20 |

The rule list was written from this dataset's opener lists, held-out ones included (`Voila!`, `FYI:`, `Excellent!`), so its test figure is not a measure of generalization; it shows what a fixed list covers, mostly English (76 of the 90).

The first two were scored on v3 (English and Korean, fewer openers, no look-alike lines), the released model (v2) on this version (v6). Its guard never deletes a Japanese or Chinese span ending in `：`, since unseen labels and unseen openers cannot be told apart, so openers like `お知らせです：` are kept; the first figure leaves them out of the count. Japanese is its weakest language (77.3% of unseen openers). Pretraining is what makes the difference: the small model learned the phrase lists and cut words in half on anything new. Filler adverbs turned out not to be learnable from a few examples, and some are real content (Java's `finally` block), so slopdam handles them with a word list and the released model only removes openers. Its card has the full evaluation.

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

AI 코딩 도구가 로그 메시지에 남기는 흔적(긴 대시와 한글 `ㅡ`, 이모지, 마크다운, 둥근 따옴표, 구분선, 보이지 않는 문자, 전각 문장 부호, 군더더기 인사말)이 들어간 영어, 한국어, 일본어, 중국어 메시지 110,000개입니다. 메시지마다 사람용(`reader`)과 도구용(`dev`)으로 정리한 결과, 흔적마다의 위치와 규칙 ID가 함께 있습니다. `target`은 규칙이 고치지 못하는 인사말(`좋은 소식입니다!`, `Heads up:`, `さて、`, `好的，`)과 부사(`성공적으로`, `Successfully`)까지 뺀 결과이고, test 분할은 학습에 쓰지 않은 템플릿 48개와 처음 보는 인사말, 부사, 라벨로만 만들어 모델의 일반화를 잴 수 있습니다. 일본어와 중국어는 전각 문장 부호를 그대로 두며, `状態：OK`처럼 `：`로 끝나는 라벨은 지우면 안 되는 내용으로 들어 있습니다. 이 데이터로 학습한 인사말 제거 모델 [slopdam/chatter-tagger](https://huggingface.co/slopdam/chatter-tagger) v2는 처음 보는 인사말의 90.7%를 지우고(`：`로 끝나는 인사말 제외, 전부 세면 84.3%), 그대로 둬야 할 줄은 하나도 바꾸지 않았습니다. 자세한 결과는 Baselines와 모델 카드에 있습니다. JSON lines, logfmt, 시각이 붙은 로그 줄 안의 메시지도 있어 구조는 그대로 두고 메시지만 정리하는지 볼 수 있습니다. 라벨은 slopdam 0.9.0이 만든 결정적 결과이고, 바뀌면 안 되는 문장(옵션, URL, 경로, `key=value`, 스택 트레이스, 표, diff)도 섞여 있어 잘못 고치는지도 확인할 수 있습니다. 문장은 모두 이 데이터셋을 위해 생성했으며, AI가 쓴 글인지 판별하는 용도는 아닙니다.
