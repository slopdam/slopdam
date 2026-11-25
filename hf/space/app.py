# SPDX-License-Identifier: MIT
"""slopdam on Hugging Face Spaces: paste a log message, see the reader and dev output and
every trace with its rule ID. Runs the slopdam package from PyPI."""
import gradio as gr

import slopdam
from slopdam import Sanitizer

EXAMPLES = [
    ["✅ **Saved** 3 rows — done! 🎉"],
    ["✅ **저장 완료** ㅡ 2024–2025년 데이터 3건 처리했습니다! 🎉"],
    ["🚀 Server started — listening on https://localhost:8080 (see `--port`)"],
    ["⚠️ 재시도 중… “db-01” 응답이 느립니다\n──────────\n• 다음 단계: 캐시 확인"],
    ["Let's go! Here's the summary: user_id=42 region=ap-northeast-2"],
]


def run(text: str, level: str, dash_inline: str):
    reader = Sanitizer("reader", level, dash_inline=dash_inline)
    dev = Sanitizer("dev", level, dash_inline=dash_inline)
    rows = [
        [f.rule_id, f.text, "(report only)" if f.fix is None else repr(f.fix), f"{f.start}:{f.end}"]
        for f in reader.findings(text or "")
    ]
    return reader.clean(text or ""), dev.clean(text or ""), rows


with gr.Blocks(title="slopdam") as demo:
    gr.Markdown(
        f"# slopdam {slopdam.__version__}\n"
        "Removes the traces AI coding tools leave in log messages: em dashes and the Korean `ㅡ`, "
        "emoji, markdown, curly quotes, separators. Deterministic rules, no model. "
        "[GitHub](https://github.com/slopdam/slopdam) · "
        "[Dataset](https://huggingface.co/datasets/slopdam/log-slop)"
    )
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(label="Log message", lines=6, value=EXAMPLES[1][0])
            with gr.Row():
                level = gr.Radio(["basic", "strong", "strict"], value="basic", label="Level")
                dash_inline = gr.Radio(["colon", "comma", "hyphen", "space"], value="colon", label="Inline dash (reader)")
        with gr.Column():
            reader_out = gr.Textbox(label="reader: for people", lines=3)
            dev_out = gr.Textbox(label="dev: for log files and tools", lines=3)
    findings = gr.Dataframe(headers=["rule", "text", "fix", "span"], label="Findings (reader)", wrap=True)
    gr.Examples(EXAMPLES, inputs=[text])
    inputs = [text, level, dash_inline]
    outputs = [reader_out, dev_out, findings]
    for trigger in (text.change, level.change, dash_inline.change):
        trigger(run, inputs, outputs)
    demo.load(run, inputs, outputs)

if __name__ == "__main__":
    demo.launch()
