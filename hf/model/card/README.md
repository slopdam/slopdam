---
license: apache-2.0
language:
  - en
  - ko
  - ja
  - zh
base_model: distilbert/distilbert-base-multilingual-cased
datasets:
  - slopdam/log-slop
pipeline_tag: token-classification
library_name: transformers
tags:
  - logging
  - text-cleaning
  - korean
  - japanese
  - chinese
  - slopdam
metrics:
  - exact_match
---

# slopdam chatter tagger

Removes the chatty openers AI assistants put at the start of log and console messages, in English, Korean, Japanese and Chinese, after [slopdam](https://github.com/slopdam/slopdam)'s rules have done the rest.

```
input  : ✅ Great news! **Deployed** api — 3 pods 🎉
slopdam: Great news! Deployed api: 3 pods
tagger : Deployed api: 3 pods

input  : 좋은 소식입니다! 배포 완료
slopdam: 좋은 소식입니다. 배포 완료
tagger : 배포 완료

input  : 🚀 さて、バックアップが完了しました
slopdam: さて、バックアップが完了しました
tagger : バックアップが完了しました

input  : 好的，已将42条记录保存到orders
tagger : 已将42条记录保存到orders
```

slopdam's rules are deterministic and fix dashes, emoji, markdown and the like. Openers are different: there are too many ways to say "Great news!" or "살펴보겠습니다." for a word list, and slopdam's `tone.chatty` rule only reports the few it knows. This model handles that one job.

## How it works

- It never writes text. It tags each word piece KEEP, DELETE or UPPER (keep it with a capital letter), so it can delete words and capitalize the next one, nothing else. Numbers, IDs, URLs and paths cannot be changed, only kept or deleted.
- Every deletion then has to pass a fixed guard (`chatter.py`), or the line is left exactly as it was. A deletion is applied only if it is one run of whole words at the start of a line (after a list or heading marker), ends in punctuation or a Korean connective ending (`-면`, `-로`, `-히`, ...), leaves something behind, and contains no digits, paths, file names, `key=value`, a mix of Latin with Hangul, kana or CJK ideographs, or a log level or label at its start (`panic:`, `ERROR:`, `Caused by:`, `ValueError:`, `경고:`, `エラー：`, `错误：`).
- Japanese and Chinese have no spaces between words, so full-width punctuation (`、，！？。`) also ends a word there. A Japanese or Chinese span ending in a full-width colon is never deleted: there `状態：` or `来源：` is a label far more often than `お知らせです：` is an opener, and the model cannot tell unseen ones apart.
- Filler adverbs (`Successfully`, `성공적으로`) are out of scope. An unseen one cannot be told from content (Java's `finally` block), so slopdam handles them with a word list.

## Use

```bash
pip install "slopdam[chatter]"
tail -f app.log | slopdam clean --chatter
```

```python
from slopdam.chatter import strip

strip(["Heads up: cache warmed for orders", "Finally block ran in auth", "🚀 さて、バックアップが完了しました"])
# ['Cache warmed for orders', 'Finally block ran in auth', 'バックアップが完了しました']
```

`strip` and `--chatter` run slopdam's rules (reader profile) first, since the model was trained on their output, then the model with its guard. They load this repository at a pinned revision. Calling the model without the guard is not supported. `chatter.py` here is the same module as `slopdam.chatter`, for use without installing slopdam: `ChatterTagger()(lines)` runs the model and guard on lines you have already cleaned.

### In the browser

`onnx/model_int8.onnx` (129 MB) is an int8 export for [onnxruntime-web](https://www.npmjs.com/package/onnxruntime-web). The [slopdam Space](https://huggingface.co/spaces/slopdam/slopdam) runs it in the page, with `chatter.js` there as the tokenizer, guard and rebuild; nothing is sent to a server. On log-slop `test` it gives the same output as the PyTorch model on 4,551 of 4,552 lines and the same handwritten-set scores; see the table below. `hf/model/export_onnx.py` makes it, and `hf/model/js_parity.py` checks that `chatter.js` turns the same labels into the same text as `chatter.py` (5,337 lines, all equal).

## Evaluation

Scored on log-slop v6, which adds Japanese and Chinese (20% of rows each) to v5. v6 is generated from slopdam's main branch, which keeps full-width punctuation on Chinese and Japanese lines; it goes on the Hub with the next slopdam release. The `test` split uses message templates, openers, labels, look-alike lines and log shapes that never appear in training. Rows with filler adverbs are excluded, since fillers are not this model's job. The handwritten sets are 44 lines each, written by hand with words that are in none of the generator's lists; sets 3 and 4 are English and Korean, sets 5 to 7 Japanese and Chinese. Set 7 is the gate for this release.

| | Result | Release bar |
|---|---:|---:|
| `test`: unseen openers removed (exact match), openers ending in `：` left out | 90.7% (343 of 378) | 90% |
| `test`: same, English / Korean / Japanese / Chinese | 99.3% / 87.8% / 77.3% / 91.7% | |
| `test`: unseen openers removed, all | 84.3% (343 of 407) | |
| `test`: other rows left unchanged | 100% (4,145) | 99.5% |
| `test`: hard negatives left unchanged | 100% (1,130) | 100% |
| Handwritten set 7 (ja, zh): content lines left unchanged | 20 of 20 | 20 of 20 |
| Handwritten set 7 (ja, zh): openers removed | 21 of 24 | 18 of 24 |
| Handwritten set 6 (ja, zh): content / openers | 20 of 20 / 22 of 24 | |
| Handwritten set 5 (ja, zh): content / openers | 20 of 20 / 18 of 24 | |
| Handwritten set 4 (en, ko): content / openers | 20 of 20 / 21 of 24 | |
| Handwritten set 3 (en, ko): content / openers | 20 of 20 / 23 of 24 | |
| int8 ONNX: `test` unseen openers, `：` left out / all | 90.5% (342 of 378) / 84.0% | 90% |
| int8 ONNX: other rows / hard negatives / set 7 | 100% / 100% / 20 of 20, 21 of 24 | |
| int8 ONNX: per line on CPU (onnxruntime), median / p99 | 2.5 ms / 7.3 ms | |

The three openers set 7 misses all end in `：` (`報告いたします：`, `郑重通知：`, `划重点：`), which the guard keeps by design.

How the bar was met, in full. This is the second training round on v6. The first release (trained on v4), scored on set 5 as a baseline, removed 21 of 24 Japanese and Chinese openers but deleted 4 content labels (`結果：`, `总计：`, `要確認：`). Round 1 on v6 still deleted them, so the generator gained Japanese and Chinese label lines (`状態：OK`) and set 6 was written as the next gate. Round 2 then deleted unseen labels (`来源：`, `优先级：`, `宛先：`) on the test split and 2 of 20 content lines in set 6, so the full-width colon rule was added to the guard and set 7 was written before any candidate was scored on it. Between the two rounds' models, round 2 was picked on the test split and sets 3 to 6 (English 99.3% against 89.1%); set 7 was used once, on that model. The bar of 90% is met only with openers ending in `：` left out of the count, the same way fillers are; counting them, 84.3% of unseen openers are removed. Earlier: the first release was the fourth round on v4, gated by set 3, with guard rules for `-서` endings, mixed Latin and Hangul and log levels added after seeing test failures; a model retrained on v5 scored lower and was not released; a character model trained from scratch removed 55% of the rewrites and changed 4% of the lines it should have left alone, and was not released either.

## Limits

- Trained only on synthetic log messages from [log-slop](https://huggingface.co/datasets/slopdam/log-slop). Long prose, chat transcripts and languages other than English, Korean, Japanese and Chinese are out of scope.
- It misses openers that look like content or have no punctuation (`Plot twist:` was kept, `Right, so ...` was kept). When unsure it keeps the line, by design.
- Japanese and Chinese openers that end in `：` are never removed. Japanese is the weakest language (77.3% of unseen openers), then Korean (87.8%).
- It is not an AI-text detector and says nothing about who wrote a line.

## Training

- Base: [distilbert-base-multilingual-cased](https://huggingface.co/distilbert/distilbert-base-multilingual-cased) (Apache-2.0, pretrained on Wikipedia in 104 languages).
- Data: 90,268 rows of log-slop v6 `train` without filler rows, labels derived from `reader` and `target`; 3 epochs, AdamW, learning rate 5e-5 with a one-cycle schedule, batch 32, on an Apple M-series GPU (61 minutes).
- Code: `hf/model/finetune.py` and `hf/model/chatter.py` in the slopdam repository.
- int8 ONNX: dynamic quantization with one scale per output channel. One scale per tensor was tried first and scored 89.9% of unseen openers on `test`, under the bar; per channel was picked after seeing that.

## License

Apache-2.0, the license of the base model. The training data and the slopdam code are MIT.

## 한국어 요약

AI 도구가 로그 맨 앞에 붙이는 인사말(`좋은 소식입니다!`, `Heads up:`, `さて、`, `好的，`)을 영어, 한국어, 일본어, 중국어에서 지우는 모델입니다. slopdam 규칙으로 먼저 정리한 텍스트에 씁니다. 글자를 새로 쓰지 않고 단어를 지우거나 첫 글자를 대문자로 바꾸기만 하며, 줄 맨 앞의 한 덩어리이고 문장 부호나 연결 어미로 끝나고 숫자, 경로, 파일 이름이 없을 때만 지웁니다. 조건이 맞지 않으면 그 줄은 원문 그대로 둡니다. `panic:`, `경고:`, `エラー：` 같은 로그 레벨과 라벨은 지우지 않고, 일본어와 중국어에서 `：`로 끝나는 구간은 라벨일 때가 많아 지우지 않습니다. log-slop v6 test에서 학습에 없던 인사말의 90.7%를 지웠고(`：`로 끝나는 인사말 제외, 전부 세면 84.3%), 그대로 둬야 할 줄은 하나도 바꾸지 않았습니다. 일본어가 가장 약합니다(77.3%). 브라우저용 int8 ONNX(`onnx/model_int8.onnx`, 129 MB)도 있으며, test 4,552줄 중 4,551줄에서 PyTorch 모델과 같은 결과를 냅니다. [데모](https://huggingface.co/spaces/slopdam/slopdam)에서 써 볼 수 있습니다. 기준을 맞추기까지의 과정(평가 세트를 새로 쓴 이유, 가드 규칙을 더한 시점)은 위 Evaluation에 모두 적었습니다.
