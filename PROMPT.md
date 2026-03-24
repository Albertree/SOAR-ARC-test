# SOAR-ARC Inner Loop — Claude Code 자율 개발 지시문

> 이 파일은 매 세션 시작 시 Claude Code가 읽는 유일한 지시문이다.
> 세션을 시작하면 반드시 이 파일 전체를 읽고 시작하라.

---

## 레포지토리

- **GitHub**: https://github.com/Albertree/SOAR-ARC-test.git
- **로컬 루트**: 현재 작업 디렉토리

---

## 미션 (변하지 않음)

```
python run_task.py 실행 시 "CORRECT" 출력
```

대상 태스크: `08ed6ac7`
성공 = 이 태스크의 test output grid를 정확히 예측.

이것이 inner loop 1단계의 완성 기준이다.
CORRECT가 출력될 때까지 매 세션 코드를 개선한다.

---

## 절대 수정 금지

```
data/          ← ARC 데이터 원본 (read-only)
PROMPT.md      ← 이 파일 자체
```

그 외 모든 파일은 수정 가능하다.

---

## 현재 구현 상태

### 완성된 것
| 레이어 | 파일 | 상태 |
|--------|------|------|
| ARCKG 기반층 | `ARCKG/*.py` | ✅ 완료 |
| DSL 도구 | `procedural_memory/DSL/*.py` | ✅ 완료 |
| 태스크 로드 | `managers/arc_manager.py` | ✅ 완료 |
| 평가 환경 | `arc2_env/arc_environment.py` | ✅ 완료 |
| SOAR 구조 | `agent/*.py` | ✅ 뼈대 완료 |
| 진입점 | `run_task.py` | ✅ 완료 |

### 미완성인 것 (이게 이번 미션의 대상)
| 레이어 | 문제 |
|--------|------|
| SOAR operator 구현 | `substate-progress`가 placeholder — 실제 아무것도 안 함 |
| WM 슬롯 | `^focus-level`, `^focus-parent-id` 등 핵심 슬롯 미사용 |
| compare 연동 | `ARCKG/comparison.py`의 `compare()`가 agent loop에서 호출 안 됨 |
| predict/submit | 예측 결과를 output-link에 쓰는 로직 없음 |

---

## 시스템 설계 원칙

### ARCKG 5계층

```
TASK (T{hex})
 └── PAIR (P{n} / Pa for test)
      └── GRID (G0=input, G1=output)
           └── OBJECT (O{n})
                └── PIXEL (X{n})
```

- 노드 = 폴더, 엣지 = JSON 파일
- 관계(Relation)는 lazy 생성 — 필요할 때만 `compare()` 호출
- `semantic_memory/` 아래에 비교 결과 저장

### SOAR 결정 사이클

```
매 사이클:
  ① Elaborate  — ElaborationRule들을 fixed-point까지 반복
  ② Propose    — ProductionRule들이 operator 후보 수집
  ③ Select     — PREFERENCE_ORDER 기준 하나 선택
  ④ Apply      — operator.effect(wm) 호출

impasse 조건:
  - WM 무변화 (no-change) → substate 생성
  - operator 실패         → substate 생성
  - 후보 없음             → substate 생성
```

### Operator 의도 설계 (구현 목표)

| Operator | 의도 | WM에 써야 하는 것 |
|----------|------|-------------------|
| `solve-task` | 최상위 목표 표상. WM 무변화 → no-change impasse 유도 | 없음 (의도적) |
| `deepen` | 포커스를 한 레벨 아래로 | `^focus-level`, `^focus-ids` |
| `compare-within-parent` | 한 PAIR 안의 G0 vs G1 비교 | `^last-comparison` |
| `compare-siblings` | 같은 레벨 형제들 비교 (ex: P0 vs P1) | `^last-comparison` |
| `note-imbalance` | 구조적 불균형 탐지 | `^imbalance`, `^imbalance-kind` |
| `extract-invariants` | 비교 결과에서 공통 패턴 추출 | `^invariant-chunk` |
| `generalize` | 추상 규칙 생성 | `procedural_memory` 저장 |
| `predict` | test input에 규칙 적용 | output-link에 예측 그리드 |
| `submit` | 예측 제출 → goal 완료 | `^goal-satisfied true` |

**금지**: Operator 이름/docstring에 TASK, PAIR, GRID, OBJECT, PIXEL 직접 사용 금지.
레벨은 `^focus-level` WM 슬롯 값으로만 표현한다.

---

## Agent가 문제를 푸는 흐름 (구현 참조)

아래는 `08ed6ac7` 태스크를 기준으로 한 구체적인 탐색 흐름이다.
이를 참고하여 operator들이 실제로 이 흐름을 수행하도록 구현하라.

### 단계 1 — TASK 수신
- `ARCManager`로 태스크 로드 → ARCKG 구성 (이미 동작함)
- `inject_arc_task(task, wm)` 로 WM input-link 주입 (이미 동작함)
- `solve-task` operator 제안 → WM 무변화 → no-change impasse → S2 생성

### 단계 2 — TASK property 확인
- S2에서 `deepen` operator 제안
- `^focus-level = "TASK"` WM에 기록
- `E_T{hex}.json` 읽어 TASK property 확인 (`number_of_pairs` 등)

### 단계 3 — semantic_memory 내 다른 TASK와 비교
- 처음 실행 시 다른 TASK 없음 → 이 단계 skip 가능
- semantic_memory에 다른 TASK가 있으면 `compare-siblings` 실행

### 단계 4 — PAIR 레벨로 descent
- TASK property만으로 목표 달성 불가 → impasse
- `deepen` → `^focus-level = "PAIR"`
- 모든 PAIR의 property 확인 (`number_of_grids`, example vs test 구분)

### 단계 5 — PAIR 간 비교
- `compare-siblings` (P0 vs Pa)
- 결과: Pa의 grid_count = 1 ≠ P0의 grid_count = 2
- `note-imbalance` → `^imbalance-kind = "grid_count"`
- 목표 설정: Pa의 grid_count를 2로 만들기 = output GRID 생성

### 단계 6 — GRID 레벨로 descent
- `deepen` → `^focus-level = "GRID"`
- P0 내 G0(input) vs G1(output) 비교: `compare-within-parent`
- `compare()` 호출 → `E_P0G0-P0G1.json` 생성
- GRID property (color, size, contents) 차이/공통 확인

### 단계 7 — 다른 PAIR GRID와 비교
- `compare-siblings` (P0G0 vs P1G0, P0G1 vs P1G1)
- 발견: 모든 GRID size 동일, input끼리 color 동일, output끼리 color 동일
- 결론: Pa의 output GRID size = example output size, color = example output color
- 단, contents는 아직 예측 불가 → 새 목표: contents 예측

### 단계 8 — OBJECT 레벨로 descent
- `deepen` → `^focus-level = "OBJECT"`
- P0G0 내 모든 Object property 확인
- P0G1 내 모든 Object property 확인
- `compare-within-parent` (P0G0 objects vs P0G1 objects, 1:1 매핑)
- 결과: area=9 color=5인 Object → area=9 color=1로 변환 (score 7/8)
- 임시 프로그램 생성 → P0G0에 적용 → P0G1과 대조

### 단계 9 — 다른 PAIR OBJECT 비교
- P1G0, P1G1에서 동일 과정 반복
- 발견: P1에서도 color=5 → color=1 패턴 존재
- 단, 두 PAIR에서 어떤 Object가 선택되는지 기준이 필요

### 단계 10 — Object 선택 기준 추출
- P0G0와 P1G0에서 변환된 Object들의 공통 내부 관계 탐색
- 발견: 변환된 Object는 같은 color를 가진 다른 Object들 중 area가 가장 큰 것
- 이것이 선택 기준 → `extract-invariants`
- `^invariant-chunk = "select object where color=X and area=max among siblings"`

### 단계 11 — 규칙 생성
- `generalize` operator
- 규칙: "color=X인 Object 중 area 최대인 것의 color를 Y로 변환"
- X, Y는 PAIR 비교에서 추출한 값

### 단계 12 — test input에 적용
- `predict` operator
- Pa의 G0 (input only) 에 규칙 적용
- output GRID 생성

### 단계 13 — 제출
- `submit` operator
- `^goal-satisfied true`
- `run_task.py` → "CORRECT" 확인

---

## 매 세션 수행 절차

### 세션 시작 시

```bash
# 1. 이전 세션 로그 확인
cat logs/session_log.md | tail -50

# 2. 현재 상태 확인
python run_task.py

# 3. 에러/출력 분석 후 이번 세션 목표 설정
```

### 세션 중

- 한 번에 하나의 operator 또는 rule을 구현한다
- 구현 후 반드시 `python run_task.py` 실행해서 방향 확인
- 에러가 나면 에러 메시지를 분석해서 원인 파악 후 수정

### 세션 종료 시 (반드시 이 순서로)

```bash
# 1. 최종 run_task.py 실행 및 결과 캡처
python run_task.py 2>&1 | tee /tmp/session_result.txt

# 2. 세션 로그 작성 (아래 형식)
# logs/session_log.md 에 append

# 3. git add & commit & push
git add -A
git commit -m "Session N: <한 줄 요약>"
git push origin main
```

---

## 세션 로그 형식

`logs/session_log.md` 파일에 아래 형식으로 **append** 하라.
(파일이 없으면 생성)

```markdown
---
## Session N — YYYY-MM-DD HH:MM

### 이번 세션 목표
(무엇을 하려 했는가)

### 수정한 파일
- `agent/active_operators.py` — deepen operator 구현 (이유: ...)
- `agent/rules.py` — siblings-ready rule 추가 (이유: ...)

### run_task.py 결과
(실행 출력 핵심 부분 붙여넣기)

### 발견한 것 / Gotcha
(예상 못한 것, 주의사항, 막힌 이유)

### 다음 세션 시작점
(여기서 멈췄고, 다음엔 이걸 해야 함)
```

---

## 구현 우선순위 (막힌 곳 모를 때 참고)

1. `agent/active_operators.py` — `DeepenOperator` 구현
   - `^focus-level` WM 슬롯을 한 단계 내림
   - `^focus-ids` 해당 레벨 node ID 목록 기록

2. `agent/rules.py` — `top-scope-no-detail` rule 구현
   - 조건: `^focus-level` 없음, `^current-task` 있음
   - 제안: `deepen`

3. `agent/active_operators.py` — `CompareWithinParentOperator` 구현
   - `ARCKG/comparison.py`의 `compare()` 호출
   - 결과를 WM `^last-comparison`에 기록

4. `agent/active_operators.py` — `CompareSiblingsOperator` 구현
   - 같은 부모 아래 형제 노드들 순차 비교

5. `agent/active_operators.py` — `NoteImbalanceOperator` 구현
   - `^last-comparison`에서 DIFF 항목 탐지
   - `^imbalance-kind` WM에 기록

6. `agent/active_operators.py` — `ExtractInvariantsOperator` 구현
   - COMM 패턴 추출 → `^invariant-chunk`

7. `agent/active_operators.py` — `PredictOperator` 구현
   - invariant + diff 패턴을 test input에 적용

8. `agent/active_operators.py` — `SubmitOperator` 구현
   - output-link에 결과 기록
   - `^goal-satisfied true`

---

## 주요 파일 구조

```
agent/
  cycle.py          ← run_cycle() — 수정 주의
  wm.py             ← WorkingMemory — 수정 주의
  active_operators.py ← 핵심 구현 대상
  rules.py            ← 핵심 구현 대상
  elaboration_rules.py← 보조 구현 대상
  preferences.py      ← PREFERENCE_ORDER (operator 우선순위)

ARCKG/
  comparison.py     ← compare() — 이미 완성, 호출만 하면 됨
  task.py, pair.py, grid.py, object.py, pixel.py

managers/
  arc_manager.py    ← ARCManager — 이미 완성

run_task.py         ← 성공 기준 판정 스크립트 (수정 금지)
```

---

## 완료 조건

```bash
python run_task.py
# 출력에 "CORRECT" 포함 시 inner loop 1단계 완성
# → logs/session_log.md에 "MISSION COMPLETE" 기록
# → git push
# → 루프 종료
```
