# SPDX-License-Identifier: MIT
"""Record the README demo from real slopdam runs.

    python scripts/demo/make_demo.py            # writes docs/assets/demo*.gif and *-en.png / *-ko.png

Every scene creates a small sample project in a temporary folder, runs the shown
command there with the slopdam installed in the current environment, and records
the real output. Frames are drawn as a terminal page by headless Chrome (so Hangul
and emoji render as they do on a Mac) and joined into a GIF with Pillow.

Needs Google Chrome or Chromium and Pillow (pip install pillow). Not part of the package.
"""
from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
CHROME = next(
    (p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium",
                 shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and Path(p).exists()),
    None,
)
WIDTH, HEIGHT = 980, 560

# Sample project per language. The traces are the kind AI coding tools leave in log calls.
FILES = {
    "en": {
        "src/sync.py": '''\
            import logging

            log = logging.getLogger(__name__)


            def sync(rows):
                log.info("🚀 Starting sync — %d rows", len(rows))
                log.info("✅ **Synced** %d rows for 2024–2025!", len(rows))
                log.warning("⚠️ Retrying… “db-01” is slow")
            ''',
        "src/server.js": '''\
            console.log("🎉 Server started — listening on port 8080");
            ''',
        "app.py": '''\
            import logging
            from slopdam import PlainFilter, PlainFormatter

            console = logging.StreamHandler()
            console.setFormatter(PlainFormatter("%(message)s"))
            console.addFilter(PlainFilter())
            file = logging.FileHandler("app.log")
            file.setFormatter(PlainFormatter("%(levelname)s %(message)s", profile="dev"))
            file.addFilter(PlainFilter(profile="dev"))
            logging.basicConfig(level=logging.INFO, handlers=[console, file])

            logging.info("✅ **Saved** 3 rows — done! 🎉")
            logging.info("==========")
            logging.error("❌ Upload failed — see https://example.com/runs/42")
            ''',
    },
    "ko": {
        "src/sync.py": '''\
            import logging

            log = logging.getLogger(__name__)


            def sync(rows):
                log.info("🚀 동기화 시작 ㅡ %d건", len(rows))
                log.info("✅ **동기화 완료** 2024–2025년 데이터 %d건 처리했습니다!", len(rows))
                log.warning("⚠️ 재시도 중… “db-01” 응답이 느립니다")
            ''',
        "src/server.js": '''\
            console.log("🎉 서버 시작 — 8080 포트에서 대기 중");
            ''',
        "app.py": '''\
            import logging
            from slopdam import PlainFilter, PlainFormatter

            console = logging.StreamHandler()
            console.setFormatter(PlainFormatter("%(message)s"))
            console.addFilter(PlainFilter())
            file = logging.FileHandler("app.log")
            file.setFormatter(PlainFormatter("%(levelname)s %(message)s", profile="dev"))
            file.addFilter(PlainFilter(profile="dev"))
            logging.basicConfig(level=logging.INFO, handlers=[console, file])

            logging.info("✅ **저장 완료** ㅡ 3건 처리했습니다! 🎉")
            logging.info("ㅡㅡㅡㅡㅡㅡㅡㅡ")
            logging.error("❌ 업로드 실패 — https://example.com/runs/42 참고")
            ''',
    },
}

# (asset name, title, commands). Each command runs for real, in order, in one sample project.
SCENES = {
    "en": [
        ("logging", "Clean log output: reader on the console, dev in the file",
         ["tail -n 3 app.py", "python app.py", "cat app.log"]),
        ("check", "Find traces in log calls, in Python and JavaScript",
         ["slopdam check src/"]),
        ("fix", "Fix Python string literals, previewed as a diff",
         ["slopdam fix --diff src/"]),
        ("pipe", "Clean any program's output through a pipe",
         ["echo '✅ **Deployed** v2 — all checks passed! 🚀' | slopdam clean",
          "echo '✅ **Deployed** v2 — all checks passed! 🚀' | slopdam --profile dev clean"]),
    ],
    "ko": [
        ("logging", "로그 출력 정리: 화면은 reader, 파일은 dev",
         ["tail -n 3 app.py", "python app.py", "cat app.log"]),
        ("check", "Python과 JavaScript의 로그 호출에서 흔적 찾기",
         ["slopdam check src/"]),
        ("fix", "Python 문자열 리터럴 수정, diff로 미리 보기",
         ["slopdam fix --diff src/"]),
        ("pipe", "파이프로 어떤 프로그램의 출력이든 정리",
         ["echo '✅ **배포 완료** ㅡ v2 모든 검사 통과! 🚀' | slopdam clean",
          "echo '✅ **배포 완료** ㅡ v2 모든 검사 통과! 🚀' | slopdam --profile dev clean"]),
    ],
}


def run_scene(lang: str, commands: list) -> list:
    """Run the commands in a fresh sample project; return (command, output) pairs."""
    with tempfile.TemporaryDirectory(prefix="slopdam-demo-") as tmp:
        for name, body in FILES[lang].items():
            path = Path(tmp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(body), encoding="utf-8")
        env = dict(os.environ, PYTHONUNBUFFERED="1", PATH=f"{Path(sys.executable).parent}:{os.environ['PATH']}")
        steps = []
        for cmd in commands:
            out = subprocess.run(["bash", "-c", cmd], cwd=tmp, env=env, capture_output=True, text=True)
            text = (out.stdout + out.stderr).replace(tmp + "/", "").rstrip("\n")
            steps.append((cmd, text))
        return steps


PAGE = """<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:#e9edf2}}
.win{{margin:18px;height:{inner}px;border-radius:10px;background:#1e2430;box-shadow:0 8px 24px rgba(0,0,0,.25);overflow:hidden;display:flex;flex-direction:column}}
.bar{{height:34px;background:#2b3240;display:flex;align-items:center;padding:0 14px;gap:8px;font:13px -apple-system,"Apple SD Gothic Neo",sans-serif;color:#aab4c3}}
.dot{{width:12px;height:12px;border-radius:50%}}
.title{{margin-left:12px}}
.term{{flex:1;padding:16px 20px;overflow:hidden;display:flex;flex-direction:column;justify-content:flex-end}}
pre{{margin:0;font:15px/1.5 Menlo,"Apple SD Gothic Neo","Apple Color Emoji",monospace;color:#d8dee9;white-space:pre-wrap;word-break:break-all}}
.p{{color:#8fbcbb}} .c{{color:#eceff4}} .add{{color:#a3be8c}} .del{{color:#bf616a}} .dim{{color:#7b8696}} .cur{{background:#d8dee9;color:#1e2430}}
</style><div class="win"><div class="bar"><span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span><span class="title">{title}</span></div><div class="term"><pre>{body}</pre></div></div>"""


def color(line: str) -> str:
    e = html.escape(line)
    if line.startswith(("+++", "---")):
        return f'<span class="dim">{e}</span>'
    if line.startswith("+"):
        return f'<span class="add">{e}</span>'
    if line.startswith("-"):
        return f'<span class="del">{e}</span>'
    return e


def screen(title: str, steps: list, typing: str = None, cursor: bool = False, height: int = HEIGHT) -> str:
    rows = []
    for cmd, out in steps:
        rows.append(f'<span class="p">$</span> <span class="c">{html.escape(cmd)}</span>')
        rows += [color(x) for x in out.splitlines()] if out else []
    if typing is not None:
        rows.append(f'<span class="p">$</span> <span class="c">{html.escape(typing)}</span>' + ('<span class="cur"> </span>' if cursor else ""))
    return PAGE.format(title=html.escape(title), body="\n".join(rows), inner=height - 36)


def shoot(page: str, out: Path, scale: int, work: Path, height: int = HEIGHT) -> None:
    src = work / "frame.html"
    src.write_text(page, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                    f"--window-size={WIDTH},{height}", f"--screenshot={out}", src.as_uri()],
                   check=True, capture_output=True)


def build(lang: str, work: Path) -> None:
    frames, durations = [], []

    def frame(page: str, ms: int) -> None:
        path = work / f"{lang}-{len(frames):04d}.png"
        shoot(page, path, 1, work)
        frames.append(path)
        durations.append(ms)

    for name, title, commands in SCENES[lang]:
        steps = run_scene(lang, commands)
        done = []
        for cmd, out in steps:
            for i in range(0, len(cmd) + 1, max(1, len(cmd) // 12)):
                frame(screen(title, done, cmd[:i], cursor=True), 60)
            frame(screen(title, done, cmd, cursor=True), 350)
            done.append((cmd, out))
            frame(screen(title, done, "", cursor=True), 1400 + 60 * out.count("\n"))
        durations[-1] += 1600
        # Still image for the README table, cut to the height of its text (lines are 22.5px).
        lines = sum(1 + len(out.splitlines()) for _, out in done)
        height = min(HEIGHT, int(36 + 34 + 32 + 22.5 * lines + 8))
        shoot(screen(title, done, height=height), ASSETS / f"{name}-{lang}.png", 2, work, height)  # still image for the README table
        print(f"  {name}-{lang}.png")

    images = [Image.open(p).convert("RGB") for p in frames]
    palette = images[-1].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    gif = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
    target = ASSETS / ("demo.gif" if lang == "en" else f"demo-{lang}.gif")
    gif[0].save(target, save_all=True, append_images=gif[1:], duration=durations, loop=0, optimize=True, disposal=1)
    print(f"  {target.name}: {len(frames)} frames, {target.stat().st_size // 1024} KB")


def main() -> int:
    if not CHROME:
        print("Google Chrome or Chromium is required", file=sys.stderr)
        return 1
    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="slopdam-frames-") as work:
        for lang in SCENES:
            print(lang)
            build(lang, Path(work))
    return 0


if __name__ == "__main__":
    sys.exit(main())
