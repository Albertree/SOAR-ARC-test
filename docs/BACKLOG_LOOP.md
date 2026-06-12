# BACKLOG LOOP — 역량 래더 (무인 자율 개발, Slice 박스 대체)

> 이 문서는 `PROMPT.md` 와 **함께** 읽는다. PROMPT.md = 불변 철학 (single
> ultimate goal, smallest defensible gap, F1–F8 / P1–P6 — *절대 안 바뀐다*).
> 이 문서 = *현재 활성 타겟*. 단, 이전의 `SLICE_N_LOOP.md` 와 달리 **하나의
> 과제 박스가 아니라 역량 래더(capability ladder)** 다. 루프는 사람의 다음
> 슬라이스 문서를 **기다리지 않고**, 가장 낮은 미완 rung 을 스스로 채우고
> 증명되면 다음 rung 으로 **자율 등반**한다.
>
> **활성 (2026-06-12)** — 은퇴한 `docs/SLICE_1_LOOP.md` 를 대체한다 (그 파일은
> 삭제됨; R0 의 산물은 §3 R0 에 요약). PROMPT.md §2 Step0 / §3 Step1.A 가 이
> 파일을 가리킨다.
>
> **압축 경고**: 요약본이 아니다. 각 iteration 은 §0 의 원본을 *정독* 한 뒤
> 작업한다 — 이 문서만 보고 "그럴싸하게" 구현하지 말 것.

---

## 0. 매 iteration 시작 전 반드시 정독 (압축본 아닌 원본)

이전과 동일하게 매번 읽는다. 이 문서는 그 요약이 아니라 *실행 맥락* 이다.

1. **`docs/arbor_context/arbor.md`** — 캐노니컬 허브. 단일 목표, Fast/Slow path,
   6 진단 실패, 다음 과제 backlog. *여기서 시작.*
2. **`docs/arbor_context/arbor-flow-three-task-description.md`** — 사용자 raw
   prose. easy000a / easy000b / 08ed6ac7 풀이 시나리오. *왜* 가 여기 있다.
3. **`docs/arbor_context/arbor-execution-trace.md`** — 11 모듈 + 7 원리 + spec-gap.
4. **`docs/arbor_context/arbor-modules.md`** — 모듈 인벤토리. **Gap 열 = 이
   래더의 출처.** 각 rung 은 이 표의 Gap 한 줄을 닫는다.
5. **`docs/arbor_context/arbor-dsl-taxonomy.md`** — DSL 4분리 (transformation 은
   `make_grid`/`coloring` 2개로 영구 동결; property/relation/util 은 손으로 허용).
6. **`docs/arbor_context/arbor-open-questions.md`** — 아직 답 없는 11개. rung 이
   여기에 닿으면 *조용히 답을 지어내지 말고* 로그에 띄운다.
7. **`CLAUDE.md` + `docs/INVARIANTS.md`** — 아키텍처 불변 + F1–F8 / P1–P6.

`data/` 의 실제 grid 는 추측 말고 직접 열어 확인.

---

## 1. 슬라이스 모델 → 래더 모델 (무엇이 바뀌었나)

이전 `SLICE_1_LOOP.md` 는 *한 과제류*(constant-output easy000a/a2)를 끝까지
풀게 한 **vertical slice** 였고, 통과하면 `§10` 에 따라 **멈추고 사람이
`SLICE_2_LOOP.md` 를 써줄 때까지 대기**했다. 그게 iter8 종료의 직접 원인이며,
그 결과 *큰 틀*(object-level, anti-unification, 모듈 E–J)이 전부 `OUT` 으로
묶여 손도 못 댔다.

이 문서는 그 박스를 제거한다:

- **타겟 = 단일 과제가 아니라 "가장 낮은 미완 rung"** (§3 래더).
- **human-gate 제거**: rung 이 4 관찰 기준으로 증명되면 루프가 *스스로* 다음
  rung 으로 올라간다 (§5). 사람의 다음 문서를 기다리지 않는다.
- **이전 슬라이스의 OUT 금지는 해제**: object/pixel property, anti-unification
  와이어링, 모듈 E–J 는 이제 *전부 IN* — 단계적으로, 아래 순서로.
- **PROMPT.md 의 철학·금지 신호(F1–F8)는 그대로 적용**된다. 큰 틀을 짓는
  것과 누적-디텍터(`_try_*`)를 막는 것은 충돌하지 않는다. 래더의 모든 rung 은
  *일반 메커니즘*을 늘리는 것이지 과제별 특수처리를 늘리는 게 아니다.

핵심 한 줄: **"한 과제를 더 푸는" 게 아니라 "한 역량을 더 갖추는" 것이 rung 의
단위다.** 점수는 여전히 현미경이지 목표가 아니다 (PROMPT.md §1).

---

## 2. 7 원리 (모든 rung 이 위반하면 안 되는 설계 제약 — 불변)

`SLICE_1_LOOP.md §2` 와 동일. 원본: `arbor-execution-trace §7원리`.

| P# | 원리 | 함의 |
|----|------|------|
| **P1** | 계층 깊이는 *필요* 에 의해 | descent 는 막혔을 때만. 강제 하강 금지 |
| **P2** | 비교는 *동일 레벨* 끼리 | GRID↔GRID, OBJECT↔OBJECT. 레벨 교차 금지 |
| **P3** | 정답에는 *근거* 가 (값보다 이유) | brute 값 제출 금지. 모든 예측은 논리적 근거 |
| **P4** | 근거는 *비교의 결과* 에서 | COMM/DIFF 가 유일한 정보원 |
| **P5** | 변수의 출처는 **G0** (test 엔 G1 없음) | 예측 program 이 G1 을 입력받으면 안 됨 |
| **P6** | *2개씩* 짝지어 비교 | 3-way 없음. N개면 pairwise |
| **P7** | 모든 정보는 *symbolic dict + json* | 벡터·임베딩 금지. 사람이 읽는 symbolic |

---

## 2.5 조립 원칙 (★ 이 래더의 *방향*. task-overfit 규칙 누적 금지)

> 이 절이 래더 전체를 지배한다. 어떤 rung 도 이 원칙을 우회해 "그 task 만 푸는
> 규칙"을 찍어내는 쪽으로 흘러가면 안 된다. ARBOR 의 이름(Bottom-up Organized
> Rules)이 곧 이 원칙이다.

**1. 두 면을 구분하라 — 변환(RHS)은 동결, 인자·선택(LHS)은 성장.**
`arbor-dsl-taxonomy` 의 4종 분리가 이 원칙의 뼈대다. 헷갈리면 안 되는 핵심:
*frozen 은 transformation 카테고리뿐*이고, 인자를 만드는 어휘는 *비어 있으면
안 되고 자라야* 한다.

- **transformation (action/RHS) = `make_grid`·`coloring` 둘뿐, 영구 frozen (F3).**
  `rotate`·`flip`·`move`·`translate`·`scale`·`copy`·`recolor` … 그 외 전부는
  새 primitive 가 아니라 이 둘의 **순차 조합** + **인자 표현식**으로 *표현*된다.
- **property / relation / util / selection (인자·LHS) = 손코딩 *허용·권장*, 자라는
  어휘.** transformation 의 *인자* 와 condition 의 *술어* 를 만드는 재료다.
  `position-of`·`color-of`·`size-of`(property), `same-color`·`adjacent`(relation),
  `objects-of`·`unique`·`argmax`·`filter`·`select`(util/selection).

> **F3 의 정확한 범위 (taxonomy §3, arbor-signals 정정):** F3 는
> **transformation 디렉토리(`procedural_memory/DSL/*.py`)에만** 적용된다 —
> 체커(`scripts/check_invariants.sh:188`)가 거기 새 `def`/`@register` 를 리버트.
> property/relation/util/selection 함수는 **그 디렉토리에 두지 말 것**(리버트됨);
> `agent/` 아래(예: `agent/dsl_expr/` 또는 `agent/conditions/` 술어) PROMPT.md §3
> 허용 위치에 둔다. ⚠️ `CLAUDE.md §6.1`("DSL/ 에 새 def 금지")과
> `arbor-dsl-taxonomy §3`("property/relation/util 은 허용")은 *충돌*한다 —
> PROMPT.md §3 Step1.C 대로 **이 충돌을 session_log 에 surface** 하고, 코드 동결
> 계약(transformation 2개)은 지키되 인자 어휘는 `agent/` 에서 키운다.

표현 예 (인자가 *표현식 트리* 임에 주목 — AU 의 진짜 입력):
- `move` = `coloring(position-of(unique-object(in)), background-color(in))`
  ∘ `coloring(target-position(...), color-of(unique-object(in)))`.
- `flip_h` = source 각 셀에 `coloring((r, W-1-c), color)` — 좌표 변환식.

즉 새 변환 = **두 frozen primitive + 인자에 끼운 (좌표/색/선택) 표현식**. 절대 새
`def rotate(...)` 가 아니다 (F3 위반·auto-revert).

**2. AU 의 입력은 transformation 트리가 아니라 argument expression tree.**
`anti_unification.unify()`(R3)는 2개 이상 pair-program 의 *인자 표현식* 에서
공통 골격을 뽑아 **변수화** 한다. raw 좌표(`coloring([(2,3)],4)`)는 task 마다
달라 공통 골격이 안 생긴다 — 168-rule 실패의 진짜 원인(taxonomy §4). 좌표가
`position-of(unique-object(in))` 로 *lift* 돼 있어야 골격이 드러난다. 결과는
`rule_NNN.json` 데이터(`action.dsl`=조합 이름, `action.args`=일반화 변수,
`condition.params`=`$expr` 표현식 트리). CLAUDE.md §6.2 / taxonomy §7 그대로.

**2b. AU 결과는 *미완성* — 변수를 채우는 *선택*이 선행돼야 한다.** *(사용자 조언)*
변수화하면 AU 산물은 *구멍(변수)이 든 불완전한 프로그램*이다. 이를 *완성/인스턴스화*
하려면 각 구멍을 **무엇으로 채울지 고르는 근거·방법**이 필요하다 — 예: "변하는 그
object" 라면 *어느 object 인지* 고르는 법(`unique`? `argmax(_, size)`? `filter(_,
same-color(...))`?)이 transformation 보다 *먼저* 정해져야 한다. 이 선택의 *근거*는
지어내는 게 아니라 **비교 결과(COMM/DIFF)에서** 온다 (P3·P4: 값보다 이유).
→ 그래서 `make_grid`·`coloring` 외에 **`select`/`filter`/`unique`/`argmax` 같은
선택 함수가 단위적으로 자주 등장·재사용**된다 (util/selection 카테고리). 이들은
transformation 이 아니므로 F3 대상이 아니며, 위 §1 의 위치 규칙대로 `agent/` 에서
키운다. selection 어휘 없이는 AU 산물이 영영 미완성으로 남아 결국 task-overfit
리터럴로 되돌아간다 — 즉 selection 재료의 부재가 누적 실패의 뿌리다.

**3. overfit 은 *재료* 로만 허용 — *축적* 은 실패다.**
한 pair 를 리터럴로 푸는 *pair-specific 프로그램* 은 **anti-unification 의
입력 재료로서만** 허용된다 (§5 모듈-통일성의 "program 은 overfit OK" 가 이 뜻).
그 프로그램이 그대로 *영구 규칙* 으로 굳어 task 마다 하나씩 쌓이면 — 그게 바로
사용자가 없애려는 실패(`arbor.md` 진단, 과거 168-rule)다. **모든 overfit
프로그램은 R3 로 lift 되어 `covers>1` 의 *인자-파라미터화된 조합* 으로 수렴해야
한다.** lift 되지 않고 task 전용으로 남는 규칙은 gap 을 닫은 게 아니다.

**4. 진행 방향의 리트머스.** 한 iter 가 규칙 *수* 를 늘렸는데 그 규칙들이 두
primitive 의 *더 일반적인 조합* 으로 묶이지 않는다면 (covers 가 안 늘면), 그건
전진이 아니라 누적이다 — `arbor.md` 의 핵심 진단. P1(rule_coverage)·P2(mean
covers)·P3(au_traced_frac) 가 *함께* 오르는 방향만 진짜 전진이다.

---

## 3. 역량 래더 (rung 별: 역량 · 모듈 · Gap출처 · done-when · 움직이는 신호)

아래로 갈수록 *위 rung 을 전제*한다 (bottom-up). 각 rung 은
`arbor-modules.md` 의 Gap 한 줄을 닫고, 닫히면 다음 rung 의 전제가 된다.

> **이 브랜치(test32)는 test31 의 §2.5 인프라 노드(cffa31f)에서 분기했다.** R0 의
> 산물(DSL substrate·`constant_output`·규칙)은 *아직 트리에 없다* — 이전 test30
> 의 iter 1~8 이 만든 것을 의도적으로 버리고 새 프롬프트로 다시 짓는 중이다.
> **따라서 현재 상태 = R0 미구축. R0 가 첫 타겟이다.** (R0 가 *달성 가능*함은
> test30 이 이미 증명했다 — 다만 그 구현 코드는 가져오지 않는다.)
>
> **개발 순서(2026-06-12 개정, PROMPT.md §2.1)**: 구 `data/ARC_easy/` 슬라이스는
> 은퇴(일부 ill-posed)했고, 루프는 이제 3단계 커리큘럼 `easy_a → madeup →
> training` 을 걷는다. 래더 rung(R0..R6)은 그대로지만, **`madeup` 단계에서 루프가
> §2.1 의 초급 개념(객체 size≠1, count≠1, 다객체 선택, 그리드 resize, in/out 크기
> 불일치, 크기↔객체속성, 예시쌍≠2)을 *직접 저작* 해 R1/R3 의 선택-lift 를
> 개념확장·손코딩 없이 구조만으로 풀어내는 것이 training 도전의 전제**다.

### R0 — GRID-level COMM-copy (첫 rung — 지금 (재)구축 대상)

- 역량: 모든 example G1 이 동일 → Inter-Grid role==G1 COMM → test G1 = 공통값.
  → easy000a/b (constant-output) 를 *값-agnostic* 하게. (구 `data/ARC_easy/` 의
  easy0001/5/9/13 은 슬라이스 은퇴로 삭제됨 — 이제 supplied 초급 suite 는
  `data/ARC_easy_a/` 뿐; constant-output 변종이 더 필요하면 §6 의 `madeup` 단계에서
  `data/ARC_madeup/` 에 직접 저작한다.)
- 빌드: `make_grid`+`coloring` 정적 DSL (F3 — 이 둘뿐, 영구), `constant_output`
  condition matcher, covers-무결성 게이트, COMM-copy 예측 경로. transformation
  은 두 primitive 의 *합성*으로만.
- done-when: easy000a 와 *다른* 고정 출력(easy000b, 다른 셀+색)이 **같은 모듈**로
  풀림 (값-agnostic 증명). 4 관찰 기준(§5) 충족.
- 신호: P1(rule_coverage) > 1 로 시작, P5(condition_matchers) +1.
- 주의: test30 이 R0 를 푼 *방식*(COMM-copy)을 참고는 하되, `_try_*` 누적이나
  리터럴 하드코딩으로 되돌아가지 말 것 (F2/§6). 이미 증명된 길이니 빠르게 통과한 뒤
  R1 로 올라간다 — R0 를 무한정 닦지 말 것(spinning).

### R1 — Object-level 분석 (easy000c–i 를 *의도된 방식*으로)

- 역량: G0 의 객체를 검출·기술하고, "입력 객체를 고정/상대 위치에 색 보존
  배치" 류를 푼다. `easy000c` = (r,c) 단일 픽셀 → (5,5) 로 이동, 색 유지.
- 모듈: `ARCKG/object.py`(존재) + **property/relation/util/selection 씨앗 어휘
  구축** (`position-of`·`color-of`·`size-of`·`objects-of`·`unique`·`argmax`·
  `filter`·`select` — taxonomy §8 씨앗 set) + **C(compare) 를 OBJECT level 로**.
  새 condition matcher 1종. **위치: 이 어휘는 `procedural_memory/DSL/` 가 아니라
  `agent/` 아래** (F3 리버트 회피, §2.5-1).
- 핵심(§2.5-2b): 이 rung 의 진짜 산물은 *선택의 lift* 다. raw 좌표 대신 객체를
  `unique`/`argmax`/`filter` 로 *고르고* `position-of`/`color-of` 로 *읽어*
  `coloring` 인자에 끼운다 — 그래야 R3 의 AU 가 공통 골격을 뽑을 수 있다.
- Gap 출처: `arbor-modules §2`("anti-unification 이 객체 수준에서 동작 미검증"),
  `§6 Gap`(property 의 condition 분리), `arbor-dsl-taxonomy §4`(재료 부재 진단).
- 제약: transformation DSL 은 여전히 `make_grid`/`coloring` 둘뿐 — 이동/배치는
  `coloring(position-of(unique-object(in)), bg)` ∘
  `coloring(target-position(...), color-of(unique-object(in)))` 처럼 **인자에
  선택·좌표·색 표현식을 끼운 조합**으로 (§2.5-1, F3).
- done-when: easy000c–i 가 4 관찰 기준으로 풀림 + easy_a 100% 도달 (graduation
  교착의 해소 지점). easy000c–i 의 pair-program 들은 같은 골격(코너 이동)을
  공유하므로 **R3 로 lift 되어 covers>1 의 `place_object` 조합 1개로 수렴**해야
  한다 — 과제마다 규칙 하나씩 쌓는 게 아니다 (§2.5-3).
- 신호: easy_a 정답수 ↑, P5(condition_matchers) +1.

### R2 — Episodic writer 검증·확정

- 역량: 모든 solve 가 `episodic_memory/<task>/attempt_NNN/` 를 남긴다 (성공·실패).
- 모듈: solve 루프에서 writer 호출 (frozen `cycle.py` 는 *수정 금지* — 우회 배선).
- Gap 출처: `arbor-modules §1`("episodic 0 entries"), `§3`("cycle.py writer 미호출").
- done-when: run_learn 후 attempt 폴더가 과제마다 정확히 1개. P4 가 *진짜* 증가.
- 신호: P4(episodic_entries) 가 실측으로 증가.

### R3 — Anti-unification 와이어링 (★ 최우선 큰-틀 보상)

- 역량: skeleton 공유 규칙 2+개를 `unify()` 가 `covers>1` 추상 규칙으로 lift.
  첫 타깃: `rule_004`+`rule_005` → 단일 `copy_common_output`; 이어 R1 의 object
  규칙들.
- 모듈: **`agent/memory.py:save_rule()` 단일 호출 지점** (CLAUDE.md §8) +
  `program/anti_unification.py`. 필요 시 `object_level_lift()`.
- Gap 출처: `arbor-modules §3`("memory.py 에 anti-unification 통합"),
  `§5`("호출되는지 미확인 — KCC 진단 핵심"). *Slice 1 §9 가 명시적으로 금지했던 것.*
- 제약: 호출 지점은 `save_rule()` *하나뿐* (다른 곳에서 부르면 아키텍처 위반).
- done-when: 최소 한 쌍이 lift 되어 `covers>1` + `anti_unification_trace` 기록.
- 신호: P1(rule_coverage)·P2(mean covers)·P3(au_traced_frac) 동시 상승.

### R4 — 2차 relation (edge-of-edge 비교)

- 역량: 비교 receipt 끼리 비교 → "가장 긴/많은" 류 derived/ranking 속성.
- 모듈: `ARCKG/comparison.py` 의 `compare(edge1, edge2)` (node 클래스 아님 →
  확장 허용; node-identity 계약은 안 건드림).
- Gap 출처: `arbor-modules §2`("2차 relation 미지원", "ranking 표현 미해결").
- done-when: 2차 비교가 필요한 madeup/training 과제 1개를 그 메커니즘으로 해결.
- 신호: 새 compare 역량으로 푼 과제가 *다음* 과제에도 재사용됨.

### R5 — Fast path / skill 재사용 (모듈 E–J)

- 역량: 학습된 추상(R3 산물)을 새 과제에 *활성화*해 재사용. activation rule(E),
  synthesizer(F), per-pair program(G), variable-origin(I), skill library(J).
- 모듈: `agent/` 신규 파일 + 추상 규칙 데이터 레이어 (DSL 정적층은 안 키움, §6.2).
- Gap 출처: `arbor.md` Fast/Slow path, `arbor-modules §4 과제`.
- done-when: stored-rule hit 가 *구조가 다른* 과제로 일반화 (단순 리터럴 재사용 X).
- 신호: P1 지속 상승 + stored hit 의 과제 다양성 ↑.

### R6 — Training escalation & 자작 ladder

- 역량: 위 기계장치를 ARC-AGI-2 training 에 적용; 막히면 `data/ARC_madeup/` 에
  *실패하도록 설계된* 최소 과제를 지어 다음 Gap 을 노출 (PROMPT.md §2.2).
- done-when: training 과제를 *일반화되는* 메커니즘으로 해결 (bespoke `_try_*` ✗).
- 신호: training 정답이 새 역량으로 설명됨 + madeup ladder 가 push 되어 누적.

---

## 4. 각 iter 가 rung 을 고르는 법

매 iter = "현재 *가장 낮은 미완 rung* 을 향한 가장 작은 한 걸음."

1. probe 와 직접 실행을 현미경으로 진단 → 어느 rung 에서 막혀 있나.
2. 그 rung 안에서 *가장 작은 defensible* gap 하나만 채운다 (PROMPT.md §3).
3. rung 을 둘로 쪼갤 수 있으면 작은 쪽 (PROMPT.md §2 "smallest").

낮은 rung 이 미완인데 높은 rung 을 손대지 말 것 (depth-first 금지, R0 의 교훈).
단, 진단 결과 낮은 rung 이 *증명됨*(§5)이면 다음으로 올라간다.

---

## 5. rung 자율 등반 (human-gate 대체)

이전 §10 의 "멈추고 사람을 기다린다" 를 다음으로 대체한다:

- rung 이 **4 관찰 기준**으로 충족되면 — (1) **작동**: 모듈/비교가 에러 없이
  돈다; (2) **모듈 통일성**: 같은 종류 작업이 같은 모듈로 (모듈 안 task 전용
  분기 ✗; pair-specific program 의 overfit 은 *anti-unification 의 입력 재료로서만*
  OK — §2.5-3); (3) **정답 접근**: 풀이가 정답
  *방향* 으로 간다 (우회·실패 거쳐도); (4) **탐색 건전성**: brute-force 가
  있어도 *의미있는 범위* 안 — `logs/session_log.md` 에 **`RUNG R<k> CLEARED`** 블록을
  쓴다: 무엇이 이제 의도된 방식으로 되는가 · 어떤 신호가 움직였나 · 다음 rung 의
  전제가 충족됐는가.
- 그리고 **즉시 다음 rung 으로** 진단을 옮긴다. 사람 승인 대기 없음.
- 단, **open-question 에 닿으면 멈춘다**: rung 의 진행이 `arbor-open-questions.md`
  의 미해결 항목에 대한 *설계 결정*을 요구하면, 답을 지어내지 말고 그 질문을
  session_log 에 올리고 그 rung 은 보류, 가능한 다른 rung 으로 우회한다.

---

## 6. 가드레일

### 그대로 유지 (PROMPT.md / INVARIANTS.md 에서 승계 — 큰 틀과 무관하게 불변)

- **F3 (정확한 범위)**: *transformation* DSL 만 `make_grid`/`coloring` 둘로 영구
  동결 — 체커는 `procedural_memory/DSL/*.py` 의 새 `def`/`@register` 만 리버트.
  `rotate`/`flip`/`move` 등은 두 primitive 의 *순차 조합 + 인자 표현식* 으로만
  표현·발견된다 (**§2.5**). **property/relation/util/selection 어휘는 F3 대상이
  아니며 — 오히려 키워야 한다 — `procedural_memory/DSL/` 가 아니라 `agent/` 아래에
  둔다** (§2.5-1; CLAUDE.md §6.1 ↔ taxonomy §3 충돌은 session_log 에 surface).
- **task-overfit 규칙 누적 금지 (§2.5-3/4)**: pair-specific 리터럴 프로그램이
  lift 없이 영구 규칙으로 task 마다 쌓이면 전진이 아니라 과거의 168-rule 실패다.
  규칙 *수* 증가는 covers(P1/P2) 증가를 *동반*할 때만 진짜 전진.
- **F2**: 새 `_try_<name>`/`_apply_<name>` 추가 금지. 새 category 의 답은
  anti-unification(R3)이지 새 디텍터가 아니다.
- **anti-unification 은 `save_rule()` 단일 호출 지점**에서만 (CLAUDE.md §8).
- **F1**: frozen 파일(`data/`(단 `ARC_madeup/` 예외), `cycle.py`, `wm.py`,
  `ARCKG/*.py` node 클래스, `docs/arbor_context/`) 수정 금지.
- **score-maximize 금지**: 점수는 현미경. 보상은 INVARIANTS §2 의 P1–P6.
- **spinning 금지**: 모든 commit 은 real gap 을 닫거나, commit 안 함 (no-op iter OK).
- rule 은 `condition` 없이 저장 금지; `TF_GRID` 를 `semantic_memory/` 에 쓰지 말 것.

### 이전 Slice 1 가드레일 중 **해제됨** (이제 IN)

- ~~object/pixel-level property DSL 금지~~ → **R1 에서 허용·우선**.
- ~~모듈 E/F/G/H/I/J / anti-unification 와이어링 금지~~ → **R3·R5 에서 허용·우선**.
- ~~GRID 에서 멈춤~~ → **필요에 의해 OBJECT/PIXEL 하강 허용** (P1).
- ~~Slice 2 자율 시작 금지 / 사람 대기~~ → **§5 자율 등반으로 대체**.

(단 `make_grid`/`coloring` 동결과 `_try_*` 금지는 *해제되지 않는다* — 이건
Slice 제약이 아니라 영구 아키텍처 불변이다.)

---

## 7. 정직한 종료 (재정의)

이전엔 *한 슬라이스* 끝에서 종료 신호를 냈다 (iter8 이 그랬다). 이제 종료는
**래더 전체**가 기준이다. `logs/_LOOP_COMPLETE.md` 는 다음 *전부* 일 때만:

- R1–R6 의 미완 rung 에서 *이름 붙일 수 있는* gap 이 더는 없고,
- 그 gap 을 노출할 `data/ARC_madeup/` 과제도 더는 defensible 하게 못 짓고,
- 남은 미완이 전부 `arbor-open-questions.md` 의 *사람 설계 결정* 대기라서
  자율로는 진행 불가 — 그 질문들을 명시.

한 rung 을 끝냈다고 종료하지 말 것. rung 을 끝냈으면 §5 대로 다음으로 올라간다.
의심되면 종료가 아니라 escalate (PROMPT.md §2.2 / §5).
