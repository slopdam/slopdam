## 무엇을 바꾸나요

## 체크리스트

- [ ] 모든 커밋에 DCO 서명 (`git commit -s`)
- [ ] 테스트 추가 또는 갱신, `python -m pytest` 통과
- [ ] 출력이 바뀌면 제목에 `[output-change]`, CHANGELOG "출력 변경"에 before/after 추가
- [ ] 새 규칙이면 탐지 예, 오탐 방지 예, reader/dev 기대 결과, 레벨, 멱등성 테스트 (CONTRIBUTING 3장)
- [ ] 새 정규식에 중첩 수량자 없음 (ReDoS)
