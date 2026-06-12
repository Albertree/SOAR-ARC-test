# Independent Eval — test30-eval (claude 루프 없이 재현)

**Date:** 2026-06-12
**Branch:** test30-eval (분기 기준: test30 @ 0bfad4a8)
**Runner:** `python run_learn.py` 직접 실행 — claude infinite loop 미개입
**Python:** 3.10.9

---

## 1. 재현 결과 — 로그 주장과 100% 일치

| Slice | 명령 | 결과 | iter8 로그 주장 | 일치 |
|---|---|---|---|---|
| easy_a (9) | `run_learn.py --task-dir data/ARC_easy_a` | **2 / 9 (22.2%)** | 2 / 9 | ✅ |
| easy (16) | `run_learn.py --task-dir data/ARC_easy` | **4 / 16 (25.0%)** | 4 / 16 | ✅ |

`_LOOP_COMPLETE.md`의 standings는 과장이 아니라 독립 실행에서 그대로 재현됨.

### 풀리는 과제 (6개, 모두 constant-output)

- `easy000a`, `easy000b` — `rule=constant_output via=stored(...)`
- `easy0001/0005/0009/0013` — **단일 규칙 `rule_004`(source=easy000a)를 4개 과제에 재사용**
  (`via=stored(easy000a)`). 값 비의존 모듈이 서로 다른 과제에 1:N으로 재사용됨을
  독립 실행이 확인 — `times_reused` 21→26 (이번 런에서 +5).

## 2. 실패 과제의 성격 — 전부 Slice 2 (G0/object-level)

실패 과제는 `identity`/`color_mapping` fallback으로 떨어지며, 공통적으로
**입력(G0)을 읽어야** 풀린다 → Slice 1 범위 밖.

근거 예시 `easy000c` (identity로 오답):
```
in : (1,1)=2  → out: (5,5)=2
in : (1,4)=1  → out: (5,5)=1
```
출력 색이 **입력 픽셀 색에 의존**(2→2, 1→1)하고 위치는 우하단 코너로 이동.
상수출력이 아니라 **object detection + 코너 이동 + 색 보존** 필요 = Slice 2.
`easy000d–i`, easy 슬라이스의 12개 비-constant 과제도 동일 부류.

## 3. iter7 covers-integrity 게이트 동작 확인

easy 런에서 `Discovered: 4 new rules from pipeline` 이지만 `Rules: 2 -> 2 (+0 learned)`.
→ 파이프라인이 후보 규칙 4개를 만들었으나 **훈련을 재현하지 못해 1개도 저장 안 됨**.
iter7이 추가한 "느린 경로는 training을 reproduce하는 규칙만 저장" 게이트가
독립 실행에서도 허위 커버리지 유입을 막고 있음.

## 4. 결론

- **개발은 실제로 일어났다**: iter6에서 0 → 6 constant-output 과제를, 단일 인식
  모듈 + `make_grid/coloring` 프로그램으로 의도된 방식대로 해결. 독립 검증 통과.
- **iter8 종료는 정직했다**: 남은 모든 과제는 G0/object-level(Slice 2)이고
  `SLICE_1_LOOP.md`가 human-gated로 막아둔 영역. Slice 1 범위는 소진됨.
- **단, graduation은 Slice 1 안에서 구조적으로 불가능**: `easy_a` 100% 기준은
  `easy000c–i`가 Slice 2라서 사람이 Slice 2를 열어주기 전엔 달성 불가.
  → "개발이 안 된 것"이 아니라 "다음 단계가 사람 승인 대기" 상태.

## 5. 다음 한 수 (사람 결정 필요)

Slice 2를 열려면 `docs/SLICE_2_LOOP.md`를 작성하고 `logs/_LOOP_COMPLETE.md`를
삭제. 첫 Slice-2 승리이자 가장 깨끗한 P1/P2/P3 개선은 `rule_004`+`rule_005`를
`anti_unification.unify()`로 `covers>1` 단일 규칙으로 병합하는 것 (CLAUDE.md §8).
