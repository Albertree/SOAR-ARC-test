#!/bin/bash

# ============================================================
# SOAR-ARC Inner Loop Pipeline
# Claude Code가 run_task.py → "CORRECT" 달성까지 반복 실행
# 
# 사용법:
#   ./run_pipeline.sh
#   ./run_pipeline.sh --max-sessions 20
# ============================================================

MAX_SESSIONS=999        # 최대 세션 수 (사실상 무제한)
MAX_DURATION=$((24 * 60 * 60))  # 24시간 상한
LOG_DIR="logs"
SESSION_LOG="${LOG_DIR}/session_log.md"
PIPELINE_LOG="${LOG_DIR}/pipeline.log"
GITHUB_REPO="https://github.com/Albertree/SOAR-ARC-test.git"

# 인자 파싱
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --max-sessions) MAX_SESSIONS="$2"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

mkdir -p "$LOG_DIR"
START_TIME=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$PIPELINE_LOG"
}

get_last_session() {
    if [ -f "$SESSION_LOG" ]; then
        grep -o '## Session [0-9]*' "$SESSION_LOG" | tail -1 | grep -o '[0-9]*' || echo "0"
    else
        echo "0"
    fi
}

check_correct() {
    # run_task.py 실행 후 CORRECT 포함 여부 확인
    # return 0 = CORRECT, 1 = INCORRECT or ERROR
    local output
    output=$(python run_task.py 2>&1)
    echo "$output"
    if echo "$output" | grep -q "RESULT  : CORRECT"; then
        return 0
    else
        return 1
    fi
}

# ============================================================
# 사전 확인
# ============================================================
log "=========================================="
log "SOAR-ARC Inner Loop Pipeline 시작"
log "목표: python run_task.py → CORRECT"
log "최대 세션: $MAX_SESSIONS"
log "최대 시간: 24시간"
log "=========================================="

# git 설정 확인
if ! git remote get-url origin &>/dev/null; then
    log "[!] git remote origin이 없습니다. 설정 후 재실행하세요."
    log "    git remote add origin $GITHUB_REPO"
    exit 1
fi

# 현재 상태 확인
log "현재 상태 확인 중..."
if check_correct > /tmp/initial_check.txt 2>&1; then
    log "이미 CORRECT! 파이프라인 종료."
    cat /tmp/initial_check.txt
    exit 0
fi

SESSION=$(get_last_session)
log "마지막 세션: $SESSION. Session $((SESSION+1)) 부터 시작."

# ============================================================
# 메인 루프
# ============================================================
while true; do

    # 시간 체크
    ELAPSED=$(( $(date +%s) - START_TIME ))
    if [ $ELAPSED -ge $MAX_DURATION ]; then
        log "========== 24시간 제한 도달 — 루프 종료 =========="
        break
    fi

    # 세션 수 체크
    SESSION=$((SESSION + 1))
    if [ $SESSION -gt $MAX_SESSIONS ]; then
        log "========== 최대 세션($MAX_SESSIONS) 도달 — 루프 종료 =========="
        break
    fi

    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    SESSION_DETAIL_LOG="${LOG_DIR}/session_${SESSION}_${TIMESTAMP}.log"

    log ""
    log "========== SESSION $SESSION 시작 =========="
    log "경과 시간: ${ELAPSED}s / ${MAX_DURATION}s"

    # --------------------------------------------------------
    # Claude Code 실행
    # --------------------------------------------------------
    log "Claude Code 실행 중..."

    claude -p "Read PROMPT.md and begin. This is session ${SESSION}." \
        --permission-mode bypassPermissions \
        --output-format stream-json \
        --verbose \
        2>&1 | tee -a "$PIPELINE_LOG" | tee "$SESSION_DETAIL_LOG"

    log "Claude Code 완료."

    # --------------------------------------------------------
    # 결과 판정
    # --------------------------------------------------------
    log "run_task.py 실행 중..."
    RESULT_OUTPUT=$(python run_task.py 2>&1)
    echo "$RESULT_OUTPUT" | tee -a "$PIPELINE_LOG"

    if echo "$RESULT_OUTPUT" | grep -q "RESULT  : CORRECT"; then
        log ""
        log "=========================================="
        log "✅ CORRECT 달성! Inner Loop 완료."
        log "Session: $SESSION"
        log "경과 시간: ${ELAPSED}s"
        log "=========================================="

        # 최종 로그 업데이트
        {
            echo ""
            echo "---"
            echo "## 🎉 MISSION COMPLETE — Session $SESSION ($TIMESTAMP)"
            echo "CORRECT 달성. Inner Loop 종료."
        } >> "$SESSION_LOG"

        # 최종 push
        git add -A
        git commit -m "Session $SESSION: MISSION COMPLETE — CORRECT 달성"
        git push origin main

        exit 0
    fi

    log "INCORRECT — 다음 세션으로 계속."

    # --------------------------------------------------------
    # Git commit & push (세션 종료마다)
    # --------------------------------------------------------
    git add -A

    # 변경사항 있을 때만 commit
    if ! git diff --cached --quiet; then
        COMMIT_MSG="Session $SESSION: progress update ($TIMESTAMP)"
        git commit -m "$COMMIT_MSG" 2>&1 | tee -a "$PIPELINE_LOG"
        git push origin main 2>&1 | tee -a "$PIPELINE_LOG"
        log "Git push 완료: $COMMIT_MSG"
    else
        log "변경사항 없음 — commit 스킵"
    fi

    log "========== SESSION $SESSION 종료 =========="
    sleep 5

done

log ""
log "Pipeline 종료. 총 세션: $SESSION"
log "CORRECT 미달성 상태로 종료됨."
exit 1
