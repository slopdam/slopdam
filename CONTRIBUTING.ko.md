# 기여 가이드

[English](CONTRIBUTING.md) | [한국어](CONTRIBUTING.ko.md)

도와주셔서 고맙습니다. 이 문서는 개발 환경, 모든 커밋에 필요한 서명, 규칙을 바꿀 때 갖춰야 할 것을 설명합니다.

## 시작하기

```bash
pip install -e . pytest
python -m pytest
```

## 커밋 서명 (DCO)

slopdam은 CLA 대신 [Developer Certificate of Origin 1.1](https://developercertificate.org/)을 씁니다. 모든 커밋에 `Signed-off-by` 줄이 필요하며, `git commit -s`가 자동으로 붙여 줍니다.

```bash
git commit -s -m "dash: 반각 ㅡ(U+FFDA) 탐지"
```

서명은 "이 변경을 MIT 라이선스로 제출할 권리가 나에게 있다"는 확인입니다. AI 도구로 작성한 코드도 마찬가지로, 제출한 내용에 대한 책임은 제출한 사람에게 있습니다.

## 규칙 추가와 변경

규칙 PR에는 다음이 모두 있어야 합니다([docs/RULES.ko.md](docs/RULES.ko.md)의 체크리스트 참고).

1. **반드시 걸려야 하는 입력**
2. **걸리면 안 되는 입력**: 날짜, 명령줄 옵션, 한자와 가나 본문, `ㅋㅋ` 등
3. **두 프로필의 기대 결과**: `reader`와 `dev`
4. **레벨**(`basic`, `strong`, `strict`)과 그 이유
5. **멱등성 사례**: 두 번 정리해도 결과가 같아야 합니다.
6. **ReDoS에 안전한 정규식**: `(a+)+` 같은 중첩 수량자와 `(a|a)*` 같은 겹치는 선택지 반복을 쓰지 않습니다. [SECURITY.ko.md](SECURITY.ko.md) 참고
7. **출처**: 다른 프로젝트에서 가져온 목록이면 출처를 밝히고, 아래 허용 목록의 라이선스여야 합니다. 다른 도구에서 아이디어를 얻는 것은 환영하지만 목록을 그대로 옮기지는 않습니다.

## 출력이 바뀌는 변경

slopdam의 출력은 사용자의 로그 형식 그 자체입니다. 그래서 출력이 바뀌면 호환성이 바뀝니다.

- PR 제목에 `[output-change]`를 붙입니다.
- [CHANGELOG.md](CHANGELOG.md)의 "Output changes"에 바뀌기 전과 후의 예시를 적습니다.
- 버전은 [GOVERNANCE.ko.md](GOVERNANCE.ko.md)의 출력 안정성 정책을 따릅니다.

## 의존성과 데이터

slopdam은 실행에 필요한 의존성이 없고, 앞으로도 그렇게 유지하려 합니다.

| 종류 | 허용 라이선스 (SPDX) |
|---|---|
| 선택적 실행 의존성 | `MIT`, `BSD-2-Clause`, `BSD-3-Clause`, `Apache-2.0`, `ISC`, `PSF-2.0`, `CNRI-Python` |
| 포함하는 데이터 | `Unicode-3.0`, `MIT`, `CC0-1.0` |
| 받지 않음 | `GPL-*`, `AGPL-*`, `LGPL-*`, `SSPL-*`, 라이선스가 없는 것 |

의존성이나 데이터를 추가하는 PR은 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)도 함께 고칩니다.

## 커밋과 PR

- 커밋 제목은 `<규칙 군 또는 영역>: <요약>` 형식입니다. 예: `emoji: 국기 시퀀스 처리`, `cli: json 출력 추가`
- PR 하나에는 주제 하나만 담습니다.
- 이 저장소도 자기 린터를 통과해야 합니다. `src/`의 로그 문자열과 커밋 메시지에 긴 대시, 장식 이모지, 구분선을 쓰지 않습니다(`slopdam check src/`). 규칙 정의, 테스트, 문서의 예시는 예외입니다.
- 문서는 영어판이 기준입니다. 한국어판(`*.ko.md`)이 있는 문서를 고치면 같은 PR에서 함께 고치거나, 번역이 필요하다고 PR 설명에 적어 주세요.

## 행동 강령

모든 참여자는 [행동 강령](CODE_OF_CONDUCT.ko.md)을 따릅니다.
