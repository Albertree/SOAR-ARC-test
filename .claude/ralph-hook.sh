#!/bin/bash
OUTPUT=$(cat)
STATE_FILE=".claude/ralph-state.txt"
MAX_ITER=30

# Don't loop if no PROMPT.md exists
if [ ! -f "PROMPT.md" ]; then
  exit 0
fi

ITER=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
ITER=$((ITER + 1))
echo "$ITER" > "$STATE_FILE"

echo "Ralph iteration: $ITER / $MAX_ITER"

if echo "$OUTPUT" | grep -q "<promise>DONE</promise>" || [ "$ITER" -ge "$MAX_ITER" ]; then
  rm -f "$STATE_FILE"
  exit 0
else
  cat PROMPT.md
  exit 2
fi
