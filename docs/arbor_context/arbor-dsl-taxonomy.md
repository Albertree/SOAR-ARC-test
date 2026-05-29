---
title: ARBOR DSL Taxonomy — 4종 분리
aliases: [DSL 4종, ARBOR DSL design, DSL taxonomy]
tags: [#topic/system, #project/active, #status/draft]
created: 2026-05-18
updated: 2026-05-18
sources:
  - raw/claude-arbor-dsl-4종-설계-결정-2026-05-18.md
  - raw/notion-task-kcc2026.md
  - raw/notion-idea-test-time-solving-process-analysis-2026-05-04.md
---

# ARBOR DSL Taxonomy — 4종 분리

## 한 줄 정의
[[arbor|ARBOR]] 의 DSL 은 4 카테고리로 분리된다 — *transformation* (frozen) + *property* / *relation* / *util* (합성의 재료, 손코딩 허용). 이 분리는 ARC 풀이의 search 공간을 *transformation 의 조합* 이 아니라 **transformation 의 인자를 만드는 표현식의 합성 공간** 으로 정의한다.

## 위치
- [[arbor]] 의 핵심 설계 결정 중 하나 — *옵션 D* (operator 의미 재정의) 의 구체화.
- [[arbor-signals|F3 forbidden signal]] 의 정정 근거.
- [[anti-unification]] 의 실질 입력이 무엇인지 정의.
- [[arckg-research|ARCKG]] 의 노드/엣지가 *property + relation 의 storage* 라는 정렬 명시.

## 1. 핵심 통찰 — Function 은 적게, Expression 은 풍부하게

ARC 의 모든 grid 변형은 두 transformation 으로 표현 가능:
- `make_grid(height, width, color)` — 크기 조절
- `coloring(selection, color)` — 선택 영역 색칠

그러나 *transformation 의 조합 자체에 의미가 있는 게 아니다*. 의미는 **각 transformation 호출의 *인자* 가 어떤 표현식이냐** 에 있다.

### 예 — "1픽셀 객체를 이동" 의 형식 표현

```
coloring(arg_a, arg_b) ∘ coloring(arg_c, arg_d)

  arg_a = position-of(unique-object(input))                  ; "이전 객체 좌표"
  arg_b = background-color(input)                            ; "배경색"
  arg_c = target-position(arg_a, displacement(input, output)); "목표 좌표"
  arg_d = color-of(unique-object(input))                     ; "객체색"
```

이 표현식이 *다른 task 에서도 같은 골격으로 등장* 한다는 게 의미 있는 발견. 즉:

> **[[anti-unification]] 의 진짜 입력은 transformation tree 가 아니라 argument expression tree.**

## 2. 4종 DSL 의 역할

| 구분 | 역할 | 예시 | 손코딩? | F-signal 적용 |
|------|------|------|---------|---------------|
| **transformation** | grid 변형 — RHS 위치 | `make_grid`, `coloring` | ❌ — 정확히 2개로 영구 frozen | F3 그대로 |
| **property** | 한 노드의 속성 추출 | `color-of(obj)`, `size-of(obj)`, `position-of(obj)`, `bounding-box(grid)`, `shape-signature(obj)` | ⭕ 허용 (씨앗 + 합성 확장) | F3 적용 안 됨 |
| **relation** | 두 노드 간 관계 | `adjacent(a,b)`, `same-color(a,b)`, `same-shape(a,b)`, `inside(a,b)`, `aligned(a,b,axis)` | ⭕ 허용 | F3 적용 안 됨 |
| **util** | 집합·계산 도구 | `objects-of(grid)`, `count(set)`, `unique(set)`, `argmax(set,prop)`, `background-color(grid)`, `pair-by(set,prop)` | ⭕ 허용 | F3 적용 안 됨 |

핵심: **transformation 만 frozen**, 나머지 3종은 합성의 *재료* 라 손코딩이 허용 (오히려 권장).

## 3. F3 (forbidden signal) 의 정정

기존 [[arbor-signals|F3]] 정의:
> "Hand-coded DSL primitive Added — `coloring` / `make_grid` 외 새 `@register("...")` 금지"

이 정의는 *모든* DSL 카테고리에 적용되는 것처럼 읽힘 → **재료의 *종류* 자체를 비워두는 부작용**.

정정안:
> F3 는 **transformation 카테고리에만** 적용. property / relation / util 의 신규 entry 추가는 허용. 단 각 entry 는 *어떤 카테고리의 등록인지* 명시 필수.

## 4. "Lack of material" 의 더 깊은 원인 진단

[[arbor]] 의 1k iter 실험 결과 *"AU initiation haven't even started due to lack of material"* 의 본질이 정정됨:

| 이전 진단 | 정정된 진단 |
|---|---|
| anti-unification 의 입력 *재료가 부족* | 재료의 **종류 자체가 없다** — property/relation/util 카테고리가 비어 있어 합성 가능한 인자 표현식이 raw 좌표·색상값뿐 |

168 fast-path rule 이 모두 `coloring([(2,3)], 4)` 같은 *raw 좌표 호출* 이었던 게 자연스러웠던 이유: 좌표 자체가 task 별로 달라 anti-unification 의 *공통 골격* 이 형성될 자리가 없었음. 만약 raw 좌표가 `position-of(unique-object(...))` 로 *lift* 되어 있었다면 공통 골격이 자연스럽게 드러났을 것. → [[object-level-lifting]] 의 정확한 주제이지만 lifting 의 *재료* 부재로 lifting 자체가 불가능.

## 5. SOAR 와의 정렬 — 더 정확해짐

이 통찰은 ARBOR 를 [[soar|SOAR]] 와 *더 가깝게* 정렬시킨다.

SOAR production rule 의 구조:
```
sp { name
     (state <s> ^block <a> ^block <b>)        ← LHS = condition
     (<a> ^clear true ^name X)
     (<b> ^clear true ^name Y)
     -->
     (<s> ^operator <o> +)                     ← RHS = action
     (<o> ^name move ^source <a> ^dest <b>) }
```

| SOAR | ARBOR |
|------|-------|
| LHS (condition) = WM 의 패턴 표현식 — property + relation 의 합성 | rule.condition = property + relation + util 표현식 |
| RHS (action) = operator 발사·WME 추가 | rule.action = transformation DSL 호출 (make_grid / coloring) |

즉 ARBOR 의 4종 DSL 분리가 SOAR 의 LHS/RHS 구분의 자연 표현. ARBOR 가 옵션 D (operator 의미 재정의) 로 가도 SOAR 사용 패턴을 *잃지 않음*, 오히려 *명료해짐*.

## 6. ARCKG 와의 정렬

[[arckg-research|ARCKG]] 의 노드/엣지 구조가 정확히 *property + relation 의 storage*:

| ARCKG | ARBOR DSL 카테고리 |
|---|---|
| Node 의 `property.json` (0차 edge) | property DSL 의 evaluated 결과 |
| 1차 edge (두 노드 비교 receipt) | relation DSL 의 evaluated 결과 |
| 2차 edge (edge 의 edge, [[arckg-node-edge]]) | relation-of-relation — util DSL 로 표현 가능 |

즉 *ARCKG = property/relation/util 식의 evaluated 결과 저장소*. 풀이 시 ARCKG 를 query 한다는 것은 *DSL 표현식의 결과 캐시* 를 보는 것과 동치.

## 7. Rule schema 의 함의

기존 [[arbor-prompt-spec|rule.json schema]] 의 `condition.params` 는 *flat key-value* 였음. 4종 DSL 분리 후엔 *표현식 트리* 를 담을 수 있어야:

```json
"condition": {
  "type": "object-displacement-pattern",
  "params": {
    "object": {"$expr": "unique-object(input)"},
    "displacement": {"$expr": "subtract(position-of(obj_out), position-of(obj_in))"}
  },
  "min_evidence": 2
}
```

`$expr` 키는 *DSL 표현식 트리* 의 직렬화. anti-unification 의 입력이 정확히 이 트리.

## 8. 씨앗 set — 첫 출발점

최소 출발 set (4종 × 5-7개씩):

### Property
- `color-of(obj | pixel) → color`
- `size-of(obj) → int` (픽셀 수)
- `position-of(obj | pixel) → (row, col)` (객체의 중심 또는 좌상단)
- `bounding-box(obj) → (min_row, min_col, max_row, max_col)`
- `shape-signature(obj) → hash` (translation·color invariant)

**2026-05-21 추가 — 암묵 property 14개 (현 ARCKG 코드의 to_json() 키 그대로)**:
3-task 분해 결과, 현 ARCKG 노드 클래스의 `to_json()` 키들이 *암묵적 property DSL* 역할을 하고 있음을 확인. 함수형 wrapper 로 명시 노출 필요. 목록:
- TASK: `example_pair_count`, `test_pair_count`
- PAIR: `grid_count`
- GRID: `size`, `color`, `contents` (3)
- OBJECT: `area`, `color`, `coordinate`, `method`, `position`, `shape`, `size`, `symmetry` (8)
- PIXEL: `color`, `coordinate` (2)

→ Slice 1 의 D 모듈에서 모두 함수형으로 노출. wiki 의 *합성* 가능 property 5종 + 암묵 property 14종 = **총 19종**.

### Relation
- `adjacent(a, b) → bool`
- `same-color(a, b) → bool`
- `same-shape(a, b) → bool` (translation 무시)
- `inside(a, b) → bool` (a 가 b 의 bbox 내부)
- `aligned(a, b, axis) → bool` (같은 row/col)

### Util
- `objects-of(grid) → set<obj>` (Hodel 객체 검출)
- `count(set) → int`
- `unique(set) → element | fail` (단일 원소면 그것)
- `argmax(set, prop) → element` (property 값 최대)
- `argmin(set, prop) → element`
- `background-color(grid) → color` (가장 많은 색)
- `pair-by(set_a, set_b, prop) → list<(a,b)>` (property 값으로 매칭)
- `nth-by(set, n, prop, desc=True) → element` ← **2026-05-21 추가** (08ed6ac7 분해 결과: largest 다음, 2nd 등 *순위 기반 selection* 필요)
- `sort-by(set, prop, desc=True) → list<elem>` ← **2026-05-21 추가**
- `filter(set, predicate) → set` ← **2026-05-21 추가** (var origin chain 의 핵심 building block)

## 9. 적용 작업 순서

1. **F3 정정** + 4종 카테고리 명시 — `CLAUDE.md §6`, [[arbor-signals]] 의 F3 항목.
2. **씨앗 set 인터페이스 명세** — `docs/DSL_TAXONOMY.md` 또는 `docs/RULE_FORMAT.md §5` 확장.
3. **씨앗 set 의 첫 구현** — `procedural_memory/DSL/{property,relation,util}/*.py` + `__init__.py` 의 4 registry.
4. **Rule schema 확장** — `condition.params` 가 `$expr` 표현식 트리 담을 수 있게.
5. **Anti-unification wiring** — 입력이 argument expression tree 가 되도록.

5번을 먼저 하면 input 이 비어있어 동작 안 함 — 순서 엄수.

## 관련
- [[arbor]] — 시스템 허브 (이 결정의 요약은 거기)
- [[arbor-execution-trace]] — D 모듈의 spec gap + 3-task 분해 결과 (2026-05-21 추가, 본 페이지의 ranking util / 암묵 property 추가의 입력)
- [[arbor-open-questions]] — Q-C1 (합성 깊이) / Q-C3 (ranking util 적정 set) 의 진척 추적
- [[arbor-signals]] — F3 정정 근거
- [[arbor-modules]] — DSL 디렉토리 구조의 입력
- [[arbor-prompt-spec]] — Rule schema 확장의 입력
- [[anti-unification]] — 실질 입력 정의
- [[arckg-research]] — property/relation/util 의 storage 로서
- [[arckg-node-edge]] — 2차 relation (= relation-of-relation 의 util)
- [[object-level-lifting]] — lifting 의 *재료* 가 4종 DSL
- [[soar]] — LHS/RHS 구분과의 정렬

## 열린 질문
- **씨앗 set 의 적정 크기** — 너무 적으면 합성 불능, 너무 많으면 search 폭발. 위 17개가 적절한가?
- **표현식의 *깊이 제한*** — `argmax(objects-of(input), size-of)` 처럼 중첩이 깊어지면 anti-unification 비용 폭증. 최대 깊이 제한 필요?
- **표현식 *cache* 정책** — 같은 표현식이 여러 rule 에서 평가되면 ARCKG 에 저장해 재사용. 캐시 무효화 시점?
- **property 와 util 의 경계** — `background-color(grid)` 가 property 인가 util 인가? 두 카테고리의 형식 정의가 필요.
- **Self-introduced primitive** — agent 가 *스스로* 새 property/relation 을 *발명* 할 수 있는가? (anti-unification 이 추출한 골격을 새 primitive 로 등록) — 이게 가능하면 진정한 self-extending.
