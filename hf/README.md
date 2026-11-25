# Hugging Face

Two repositories on the Hub, both built from this folder:

| Hub repo | Type | Source |
|---|---|---|
| [`slopdam/log-slop`](https://huggingface.co/datasets/slopdam/log-slop) | Dataset | `dataset/generate.py` writes it, `dataset/README.md` is its card |
| [`slopdam/slopdam`](https://huggingface.co/spaces/slopdam/slopdam) | Space (Gradio) | `space/` as is |

There is no model. slopdam's rules are deterministic, so a trained model would only approximate them, and deciding whether text was written by AI is out of scope.

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
hf repos create slopdam/slopdam --type space --sdk gradio
hf upload slopdam/slopdam hf/space . --type space --commit-message "slopdam 0.6.0"
```

The Space installs the slopdam version pinned in `space/requirements.txt`; bump it after each PyPI release.

## Run the Space locally

```bash
pip install gradio slopdam
python hf/space/app.py                   # http://127.0.0.1:7860
```

## 한국어

- `slopdam/log-slop` 데이터셋과 `slopdam/slopdam` Space(Gradio 데모)를 올립니다. 규칙이 결정적이라 학습 모델은 만들지 않습니다.
- 데이터셋은 `python hf/dataset/generate.py`로 매번 같은 바이트로 생성됩니다. 카드(`dataset/README.md`)를 `out/`에 복사한 뒤 `hf upload`로 올립니다.
- 업로드에는 `slopdam` 조직의 쓰기 토큰이 필요합니다(`hf auth login`).
