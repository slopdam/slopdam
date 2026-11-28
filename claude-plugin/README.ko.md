# Claude Code용 slopdam

[English](README.md) | [한국어](README.ko.md)

Claude가 쓰는 로그 메시지에 AI 흔적(긴 대시와 한글 `ㅡ`, 이모지, 마크다운 굵게, 둥근 따옴표, 구분선, 군더더기 인사말)이 남지 않게 하는 Claude Code 플러그인입니다.

- **훅.** 소스 파일을 `Write`나 `Edit`로 쓸 때마다 그 파일에 `slopdam check`를 돌리고, 찾은 내용(줄, 규칙, 고칠 내용)을 도구 결과 옆에 Claude에게 전달합니다. 작업을 막거나 파일을 바꾸지 않으며, 메시지는 Claude가 직접 고칩니다. 찾은 것이 없거나 소스 코드가 아닌 파일에는 아무것도 출력하지 않습니다.
- **스킬** `clean-log-messages`. 로그 메시지를 평이하게 쓰는 법과 `slopdam check`, `fix`, `clean` 사용법입니다.

## 설치

Claude Code에서:

```
/plugin marketplace add slopdam/slopdam
/plugin install slopdam@slopdam
```

훅을 돌리려면 slopdam(Python 3.9 이상, 의존성 없음)과 `python3`가 필요합니다.

```bash
pip install slopdam
```

`SLOPDAM_CMD`의 명령, `PATH`의 `slopdam`, 훅을 실행하는 `python3`의 slopdam 패키지, `uvx --from slopdam slopdam` 순서로 찾습니다. 하나도 없으면 프로젝트마다 한 번 Claude에게 알립니다.

## 설정

명령줄과 마찬가지로 프로젝트의 slopdam 설정(`slopdam.toml` 또는 `pyproject.toml`의 `[tool.slopdam]`)을 따릅니다. 예를 들어 `level = "strong"`이면 알려진 인사말(`Great news!`, `Heads up:`)도 보고하고, `disable = ["emoji"]`이면 그 규칙 묶음을 끕니다. `# slopdam: ignore`(또는 `// slopdam: ignore`)가 붙은 줄은 건너뜁니다.

## 파일

| 경로 | 내용 |
|---|---|
| `.claude-plugin/plugin.json` | 매니페스트 |
| `hooks/hooks.json`, `hooks/check.py` | `PostToolUse` 훅 (표준 라이브러리만 사용) |
| `skills/clean-log-messages/SKILL.md` | 스킬 |

이 플러그인을 싣는 마켓플레이스는 저장소 루트의 `.claude-plugin/marketplace.json`입니다.
