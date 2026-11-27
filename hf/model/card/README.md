---
license: apache-2.0
language:
  - en
  - ko
base_model: distilbert/distilbert-base-multilingual-cased
datasets:
  - slopdam/log-slop
pipeline_tag: token-classification
library_name: transformers
tags:
  - logging
  - text-cleaning
  - korean
  - slopdam
metrics:
  - exact_match
---

# slopdam chatter tagger

Removes the chatty openers AI assistants put at the start of log and console messages, in English and Korean, after [slopdam](https://github.com/slopdam/slopdam)'s rules have done the rest.

```
input  : ✅ Great news! **Deployed** api — 3 pods 🎉
slopdam: Great news! Deployed api: 3 pods
tagger : Deployed api: 3 pods

input  : 좋은 소식입니다! 배포 완료
slopdam: 좋은 소식입니다. 배포 완료
tagger : 배포 완료
```

slopdam's rules are deterministic and fix dashes, emoji, markdown and the like. Openers are different: there are too many ways to say "Great news!" or "살펴보겠습니다." for a word list, and slopdam's `tone.chatty` rule only reports the few it knows. This model handles that one job.

## How it works

- It never writes text. It tags each word piece KEEP, DELETE or UPPER (keep it with a capital letter), so it can delete words and capitalize the next one, nothing else. Numbers, IDs, URLs and paths cannot be changed, only kept or deleted.
- Every deletion then has to pass a fixed guard (`chatter.py`), or the line is left exactly as it was. A deletion is applied only if it is one run of whole words at the start of a line (after a list or heading marker), ends in punctuation or a Korean connective ending (`-면`, `-로`, `-히`, ...), leaves something behind, and contains no digits, paths, file names, `key=value`, or a mix of Latin and Hangul.
- Filler adverbs (`Successfully`, `성공적으로`) are out of scope. An unseen one cannot be told from content (Java's `finally` block), so slopdam handles them with a word list.

## Use

```bash
pip install slopdam transformers torch
```

```python
from huggingface_hub import hf_hub_download
import importlib.util, sys
from slopdam import clean

path = hf_hub_download("slopdam/chatter-tagger", "chatter.py")
spec = importlib.util.spec_from_file_location("chatter", path)
chatter = importlib.util.module_from_spec(spec); spec.loader.exec_module(chatter)

tagger = chatter.ChatterTagger("slopdam/chatter-tagger")
tagger([clean("Heads up: cache warmed for orders"), clean("Finally block ran in auth")])
# ['Cache warmed for orders', 'Finally block ran in auth']
```

Run slopdam's `clean` (reader profile) first: the model was trained on its output. Calling the model without the guard is not supported.

## Evaluation

The dataset's `test` split uses message templates, openers and look-alike lines that never appear in training. Rows with filler adverbs are excluded, since fillers are not this model's job. The handwritten sets are 44 lines each, written by hand with words that are in none of the generator's lists; set 3 was written before the final training run and is the release gate.

| | Result | Release bar |
|---|---:|---:|
| `test`: unseen openers removed (exact match) | 94.4% (422 of 447) | 90% |
| `test`: English / Korean | 98.7% / 89.9% | |
| `test`: other rows left unchanged | 100% (4,050) | 99.5% |
| `test`: hard negatives left unchanged | 100% (1,009) | 100% |
| Handwritten set 3: content lines left unchanged | 20 of 20 | 20 of 20 |
| Handwritten set 3: openers removed | 21 of 24 | 18 of 24 |
| Handwritten set 2: content lines left unchanged | 20 of 20 | |
| Handwritten set 2: openers removed | 17 of 24 | |

How the bar was met, in full: this is the fourth training round. Set 2 was used to steer rounds 2 to 4 and its opener score is below the bar, so set 3 was written blind as the gate. After round 4, two guard rules (no `-서` ending, no Latin and Hangul mixed in one deletion) were added because three test lines like `orders에서 테스트 6458개 실패` lost their first word; the numbers above include that change. An earlier character model trained from scratch, scored on an earlier version of the test split, removed 55% of the rewrites and changed 4% of the lines it should have left alone; it is not released.

## Limits

- Trained only on synthetic log messages from [log-slop](https://huggingface.co/datasets/slopdam/log-slop). Long prose, chat transcripts and other languages are out of scope.
- It misses openers that look like content or have no punctuation (`Plot twist:` was kept, `Right, so ...` was kept). When unsure it keeps the line, by design.
- Korean is weaker than English (89.9% against 98.7% of unseen openers).
- It is not an AI-text detector and says nothing about who wrote a line.

## Training

- Base: [distilbert-base-multilingual-cased](https://huggingface.co/distilbert/distilbert-base-multilingual-cased) (Apache-2.0, pretrained on Wikipedia in 104 languages).
- Data: 89,166 rows of log-slop `train` without filler rows, labels derived from `reader` and `target`; 3 epochs, AdamW, learning rate 5e-5 with a one-cycle schedule, batch 32, on an Apple M-series GPU (50 minutes).
- Code: `hf/model/finetune.py` and `hf/model/chatter.py` in the slopdam repository.

## License

Apache-2.0, the license of the base model. The training data and the slopdam code are MIT.

## 한국어 요약

AI 도구가 로그 맨 앞에 붙이는 인사말(`좋은 소식입니다!`, `Heads up:`)을 지우는 모델입니다. slopdam 규칙으로 먼저 정리한 텍스트에 씁니다. 글자를 새로 쓰지 않고 단어를 지우거나 첫 글자를 대문자로 바꾸기만 하며, 줄 맨 앞의 한 덩어리이고 문장 부호나 연결 어미로 끝나고 숫자, 경로, 파일 이름이 없을 때만 지웁니다. 조건이 맞지 않으면 그 줄은 원문 그대로 둡니다. 학습에 없던 인사말의 94.4%를 지웠고, 그대로 둬야 할 줄은 하나도 바꾸지 않았습니다. 한국어는 영어보다 약합니다(89.9%).
