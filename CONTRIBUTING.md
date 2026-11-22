# 기여 가이드

## 1. 시작하기

```bash
pip install -e .
pip install pytest
python -m pytest
```

## 2. DCO 서명 (필수)

이 프로젝트는 CLA 대신 [Developer Certificate of Origin 1.1](https://developercertificate.org/) 을 사용합니다.
모든 커밋에 `Signed-off-by` 줄이 있어야 하며, `-s` 옵션으로 자동 추가됩니다.

```bash
git commit -s -m "dash: 반각 ㅡ(U+FFDA) 탐지 추가"
```

서명은 "이 기여를 MIT 라이선스로 제출할 권리가 나에게 있다"는 확인입니다. AI 도구로 작성한 코드도 같습니다 ([docs/LICENSING.md](docs/LICENSING.md) 5장).

## 3. 새 규칙 추가

규칙 PR에는 다음이 모두 있어야 합니다. ([docs/RULES.md](docs/RULES.md) 체크리스트)

1. **탐지 예**: 반드시 걸려야 하는 입력
2. **오탐 방지 예**: 걸리면 안 되는 입력 (날짜, CLI 옵션, 한자, 가나, `ㅋㅋ` 등)
3. **`reader` / `dev` 기대 결과**
4. **레벨** (`basic` / `strong` / `strict`) 과 그 이유
5. **멱등성 테스트**에 입력 추가
6. 정규식은 **ReDoS 안전**해야 합니다. 중첩 수량자(`(a+)+`), 겹치는 선택지 반복(`(a|a)*`)을 쓰지 않습니다 ([SECURITY.md](SECURITY.md))
7. 다른 프로젝트에서 가져온 목록이면 출처와 라이선스 ([docs/LICENSING.md](docs/LICENSING.md) 4장)

## 4. 출력이 바뀌는 변경

이 도구의 출력은 사용자의 로그 형식 그 자체입니다. 기존 규칙의 결과가 바뀌는 PR은 다음을 지킵니다.

- PR 제목에 `[output-change]` 를 붙입니다.
- [CHANGELOG.md](CHANGELOG.md) 의 "출력 변경" 절에 before/after 예시를 적습니다.
- 버전 정책은 [GOVERNANCE.md](GOVERNANCE.md) 4장을 따릅니다.

## 5. 커밋과 PR

- 커밋 제목은 `<규칙군 또는 영역>: <요약>` 형식 (예: `emoji: 국기 지역 표시자 처리`, `cli: json 출력 추가`)
- 하나의 PR에는 하나의 주제만 담습니다.
- **이 저장소 자체도 도구의 린터를 통과해야 합니다.** `src/` 의 로그 문자열과 커밋 메시지에 `—`, 장식 이모지, 구분선을 쓰지 않습니다 (`slopdam check src/`). 규칙 정의와 테스트, 문서의 예시 문자는 예외입니다.

## 6. 행동 강령

모든 참여자는 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 를 따릅니다.
