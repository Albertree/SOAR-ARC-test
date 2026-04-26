# TEMP — Messed-up Experimental State Record (test12, 2026-04-27)

이 파일은 현재 로컬 실험 상태가 어떻게 어그러져 있는지를 기록한 임시 문서입니다.
논문 실험 5회를 새로 돌릴지, 현재 결과로 정리할지 판단할 때 참고용으로 작성했습니다.

---

## 1. 핵심 원인: `procedural_memory/`가 .gitignore에 들어있음

`.gitignore` 정책이 브랜치별로 다릅니다.

| 정책 | 적용 브랜치 | 결과 |
|---|---|---|
| `procedural_memory/*` 전체 무시 (`!.gitkeep`만 허용) | `main`, `ez-main`, `ez-test1`, `test1`, `test2`, `test3`, `test5`, **`test12`** | 누적된 학습 규칙(`rule_NNN.json`)이 git에 한 번도 push 안 됨 → 브랜치 사이에서 보존되지 않음 |
| `procedural_memory/concepts/`, `procedural_memory/base_rules/` 허용 | `test6`, `test7`, `test8`, `test9` | 규칙이 `concepts/*.json` 형태로 git에 커밋됨 → 보존됨 |

→ 결국 test5 이전 브랜치들과 test12에서 학습된 규칙은 **물리적으로 git remote에 올라가 본 적이 없습니다.** 로컬 워킹 디렉토리에서만 존재했고, 브랜치를 옮겨다니는 사이에 의도적/비의도적으로 덮어쓰기/삭제될 수 있었습니다.

---

## 2. 현재 워킹 디렉토리 (test12) 상태

| 항목 | 값 |
|---|---|
| 파일 수 (`procedural_memory/*.json`) | **438** |
| 학습 규칙 크기 | 2.1 MB |
| 가장 최근 파일 timestamp | 2026-04-23 20:02 |

이 438개는 **test12에서 누적된 것이 거의 확실**합니다. 근거:

- `run_learn_test12_training_20260423_195011.txt` (1000문제 평가 결과 로그):
  - 시작 시점 stored rules: **363**
  - 종료 시점 stored rules: **438** (+75 신규)
  - 결과: **149 / 1000 (14.9%)** correct
- 363개는 test12의 43회 세션 동안 `run_loop.sh`가 누적시킨 규칙으로 추정.
- 1000문제 실험 직후 +1 가량의 후속 동작이 있어 현재 438→실제 디렉토리 상 438 (정확히 일치).

⚠️ 단 **확정적이진 않음**: `run_loop.sh`는 매 invocation 시작에 procedural_memory를 wipe하지만, 사용자가 `--resume` 플래그를 줬거나 `run_learn.py`만 직접 호출했다면 wipe가 일어나지 않아 이전 브랜치의 규칙이 남아있었을 수 있음. 하지만 commit log + 보고서의 363→438 흐름은 test12 단독 누적과 일치.

---

## 3. 브랜치 옮기면 무슨 일이 벌어지나?

`procedural_memory/*.json`는 gitignore라 **branch checkout으로는 사라지지 않습니다.** 즉 지금 그대로 다른 브랜치로 가면:

- test12의 438개 `rule_*.json`이 그대로 남음
- test6/7/8/9로 가면, 그 브랜치의 git-tracked `concepts/*.json` (test7=70+개, test9=84개)이 추가됨 → **test12 규칙 + test7 컨셉 규칙이 한 폴더에 섞임**
- test12로 다시 돌아오면 test7의 컨셉 규칙은 untracked로 남아 계속 따라다님

→ 브랜치 간 경계가 무너진 상태. 한 번이라도 다른 브랜치에서 학습 코드를 돌렸다면 비교 실험으로서의 의미가 흐려짐.

---

## 4. 다른 브랜치들의 현재 누적 규칙 (git에 있는 것만)

| 브랜치 | git에 커밋된 procedural_memory 항목 | 마지막 batch 결과 (commit 메시지에서) |
|---|---|---|
| main | 0 | (Mission Complete만, 점수 없음) |
| ez-main | 0 | 0 / 16 (0%) |
| ez-test1 | 0 | 16 / 16 (100%) |
| test1 | 0 | 0 / 20 (0%) |
| test2 | 0 | 20 / 20 (100%) |
| test3 | 0 | 17 / 20 (85%) |
| test5 | 0 | 55 / 80 (68.8%) |
| test6 | base_rules/ + 개념 일부 (38 file) | 20 / 20 (100%) |
| test7 | base_rules/ + concepts/ ~70+ JSON | 72 / 80 (90%) |
| test8 | base_rules/ + 개념 일부 (30 file) | 15 / 20 (75%) |
| test9 | base_rules/ + concepts/ ~84 JSON | 72 / 80 (90%) |
| **test12** | 0 (gitignore), 워킹디렉토리에 438 | **149 / 1000 (14.9%)** ← 1000문제 평가 완료 |

→ test6/7/8/9는 git에서 규칙 데이터를 복구 가능. 나머지는 학습 결과가 사실상 손실.

---

## 5. 무엇이 보존되어 있는가?

| 자산 | 위치 | 보존 여부 |
|---|---|---|
| test12 누적 438개 규칙 | `procedural_memory/rule_*.json` | 로컬에만 (gitignore) |
| test12 1000문제 결과 로그 | `run_learn_test12_training_20260423_195011.txt` (89KB) | 로컬에만 (gitignore) |
| test12 1000문제 결과 HTML | `run_learn_test12_training_20260423_195011.html` (59MB) | 로컬에만 (용량으로 git push 비추) |
| test12 episodic_memory | `episodic_memory/episode_*.json` (90개, 360KB) | 로컬에만 |
| test6/7/8/9 컨셉 규칙 | git tracked | 보존됨 |
| 그 외 모든 브랜치 학습 규칙 | — | **손실** |

---

## 6. 백업 조치

이 커밋에 다음 압축본을 추가:

- **`backup_test12_rules_20260427.tar.gz`** (183KB) ─ 다음을 포함:
  - `procedural_memory/` 폴더 전체 (438 rule JSON + base_rules 코드)
  - `episodic_memory/` 폴더 전체 (90 episode JSON)
  - `run_learn_test12_training_20260423_195011.txt` (1000문제 결과 로그)

HTML 리포트 (59MB)는 용량으로 인해 git에 포함하지 않음. 필요시 로컬에서 별도 보관.

---

## 7. 결론 (2026-04-27 기준)

- 현재 논문에 쓸 수 있는 **신뢰 가능한 단일 데이터포인트**: **test12 → 149/1000 (14.9%)**
- test6/7/8/9의 컨셉 규칙은 git에 살아있으므로 깨끗한 폴더에 옮겨놓고 1000문제를 다시 돌리면 추가 데이터포인트 확보 가능
- 그 외 브랜치(main, ez-*, test1-3, test5)의 학습 결과는 복구 불가
