# Hugging Face

Four repositories on the Hub, all built from this folder:

| Hub repo | Type | Source |
|---|---|---|
| [`slopdam/log-slop`](https://huggingface.co/datasets/slopdam/log-slop) | Dataset | `dataset/generate.py` writes it, `dataset/README.md` is its card |
| [`slopdam/slopdam`](https://huggingface.co/spaces/slopdam/slopdam) | Space (static) | `space/` as is |
| [`slopdam/chatter-tagger`](https://huggingface.co/slopdam/chatter-tagger) | Model | `model/finetune.py` trains it, `model/card/README.md` is its card, `model/chatter.py` runs it |
| [`slopdam/README`](https://huggingface.co/spaces/slopdam/README) | Space (static) | `org-card/README.md`, shown as the card on [huggingface.co/slopdam](https://huggingface.co/slopdam) |

slopdam's rules are deterministic, so the only model is for what they cannot list: chatty openers such as `Great news!` or `살펴보겠습니다.`. It is optional, runs after the rules, only deletes, and every deletion passes a fixed guard. Deciding whether text was written by AI is out of scope.

## Build the dataset

```bash
python hf/dataset/generate.py            # writes hf/dataset/out/
python hf/dataset/generate.py --check    # builds twice, fails if the bytes differ
```

`out/stats.json` lists the slopdam version, row counts and a SHA-256 for each file. Rebuild after a slopdam release that changes output, and update the version and the rule counts in `dataset/README.md`.

## Upload

Needs `pip install -U huggingface_hub` and a write token for the `slopdam` organization (`hf auth login`).

```bash
hf repos create slopdam/log-slop --type dataset
cp hf/dataset/README.md hf/dataset/out/README.md
hf upload slopdam/log-slop hf/dataset/out . --type dataset --commit-message "log-slop from slopdam 0.6.0"
```

```bash
hf repos create slopdam/slopdam --type space --sdk static
hf upload slopdam/slopdam hf/space . --type space --commit-message "slopdam 0.6.0"
```

```bash
hf upload slopdam/README hf/org-card/README.md README.md --type space --commit-message "Organization card"
```

The card Space must hold only `README.md`: a static Space with an `index.html` shows that page as the card instead.

The Space is one HTML page that loads `@slopdam/core` from jsDelivr at the version written in `space/index.html`; bump it after each npm release. It is static because Gradio and Docker Spaces under an organization need a paid plan, while static Spaces are free.

## Train and upload the model

Needs `torch` and `transformers`, and downloads the base model (about 540MB). On an Apple M-series GPU the release run takes about 50 minutes.

```bash
python hf/model/finetune.py --rows 100000 --epochs 3 --hand handwritten3.jsonl   # writes hf/model/out/
```

```bash
hf repos create slopdam/chatter-tagger --type model
hf upload slopdam/chatter-tagger hf/model/out/distilbert-tagger . --commit-message "chatter-tagger"
hf upload slopdam/chatter-tagger hf/model/card/README.md README.md
hf upload slopdam/chatter-tagger hf/model/chatter.py chatter.py
```

Set `id2label` in `config.json` to `KEEP`, `DELETE`, `UPPER` before uploading. A new version is released only if it meets the bar in the model card on a handwritten set written before its training run.

## Run the Space locally

```bash
python3 -m http.server 7860 -d hf/space   # http://localhost:7860
```

## 한국어

- `slopdam/log-slop` 데이터셋과 `slopdam/slopdam` Space(브라우저에서 도는 정적 데모)를 올립니다. 규칙이 결정적이라 학습 모델은 만들지 않습니다.
- 데이터셋은 `python hf/dataset/generate.py`로 매번 같은 바이트로 생성됩니다. 카드(`dataset/README.md`)를 `out/`에 복사한 뒤 `hf upload`로 올립니다.
- 업로드에는 `slopdam` 조직의 쓰기 토큰이 필요합니다(`hf auth login`).
