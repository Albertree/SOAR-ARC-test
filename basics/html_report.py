"""
html_report.py — Generate a self-contained HTML report of run_learn results.

Produces a single .html file with:
  - Session header (split, score, rules)
  - Per-task sections: result badge + colored grid comparison (input | predicted | answer)
"""

# ARC color palette (matches viz.py)
_PALETTE = {
    0:  (0,   0,   0),
    1:  (0,   116, 217),
    2:  (255, 65,  54),
    3:  (46,  204, 64),
    4:  (255, 220, 0),
    5:  (170, 170, 170),
    6:  (240, 18,  190),
    7:  (255, 133, 27),
    8:  (127, 219, 255),
    9:  (135, 12,  37),
}
_FALLBACK = (180, 180, 180)

CELL_PX = 28   # pixels per grid cell


def _rgb(color: int) -> str:
    r, g, b = _PALETTE.get(color, _FALLBACK)
    return f"rgb({r},{g},{b})"


def _grid_html(grid: list, label: str) -> str:
    """Render one grid as an HTML table with colored cells."""
    rows_html = ""
    for row in grid:
        cells = "".join(
            f'<td style="width:{CELL_PX}px;height:{CELL_PX}px;'
            f'background:{_rgb(v)};border:1px solid #111;"></td>'
            for v in row
        )
        rows_html += f"<tr>{cells}</tr>"

    return (
        f'<div style="display:inline-block;margin:0 16px 12px 0;vertical-align:top;">'
        f'<div style="font-size:11px;font-weight:600;color:#aaa;'
        f'margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;">{label}</div>'
        f'<table style="border-collapse:collapse;">{rows_html}</table>'
        f"</div>"
    )


def _task_section(task_id: str, result: str, rule: str, method: str,
                  test_pairs_data: list) -> str:
    """Build HTML block for one task."""
    is_correct = result == "CORRECT"
    badge_color = "#2ecc40" if is_correct else "#ff4136"
    badge_text  = "✓ CORRECT" if is_correct else "✗ INCORRECT"

    grids_html = ""
    for pair_data in test_pairs_data:
        for label, grid in pair_data:
            if grid:
                grids_html += _grid_html(grid, label)

    return f"""
<div style="background:#1a1a1a;border-radius:8px;padding:16px 20px;margin-bottom:20px;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
    <span style="font-family:monospace;font-size:15px;color:#eee;">{task_id}</span>
    <span style="background:{badge_color};color:#fff;padding:2px 10px;
                 border-radius:4px;font-size:12px;font-weight:700;">{badge_text}</span>
    <span style="color:#888;font-size:12px;">rule: <code style="color:#aef">{rule}</code>
      &nbsp;·&nbsp; via: <code style="color:#fea">{method}</code></span>
  </div>
  <div style="overflow-x:auto;">
    {grids_html}
  </div>
</div>
"""


def _page(split: str, timestamp: str, summary: dict, task_sections: str) -> str:
    correct = summary.get("correct", 0)
    total   = summary.get("total", 0)
    pct     = f"{correct / max(total, 1) * 100:.1f}"
    rules_b = summary.get("rules_before", "?")
    rules_a = summary.get("rules_after", "?")
    elapsed = summary.get("elapsed", "?")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOAR-ARC — {split} — {timestamp}</title>
<style>
  body {{background:#111;color:#ddd;font-family:system-ui,sans-serif;
        margin:0;padding:24px 32px;}}
  h1   {{color:#fff;margin:0 0 4px;font-size:22px;}}
  .sub {{color:#888;font-size:13px;margin-bottom:24px;}}
  .stat-row {{display:flex;gap:24px;margin-bottom:28px;flex-wrap:wrap;}}
  .stat {{background:#1a1a1a;border-radius:6px;padding:12px 20px;}}
  .stat-label {{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;}}
  .stat-value {{font-size:26px;font-weight:700;color:#fff;margin-top:2px;}}
  code {{font-family:monospace;}}
</style>
</head>
<body>
<h1>SOAR-ARC &mdash; {split}</h1>
<div class="sub">{timestamp}</div>

<div class="stat-row">
  <div class="stat"><div class="stat-label">Score</div>
    <div class="stat-value">{correct} / {total} <span style="font-size:16px;color:#aaa;">({pct}%)</span></div></div>
  <div class="stat"><div class="stat-label">Rules</div>
    <div class="stat-value">{rules_b} <span style="font-size:16px;color:#888;">→</span> {rules_a}</div></div>
  <div class="stat"><div class="stat-label">Time</div>
    <div class="stat-value" style="font-size:20px;">{elapsed}s</div></div>
</div>

{task_sections}
</body>
</html>"""


class HTMLReport:
    """Accumulate task results then write a single HTML file."""

    def __init__(self, split: str, timestamp: str):
        self.split     = split
        self.timestamp = timestamp
        self._sections = []
        self.summary   = {}

    def add_task(self, task_id: str, result: str, rule: str, method: str,
                 task_obj, predicted):
        """Add one task result. task_obj is the loaded Task, predicted is list-of-grids."""
        pairs_data = []
        pred_grids = predicted
        if pred_grids and not isinstance(pred_grids[0], list):
            pred_grids = [pred_grids]

        for i, test_pair in enumerate(task_obj.test_pairs):
            pair_panels = []
            pair_panels.append(("input", test_pair.input_grid.raw))

            if pred_grids and i < len(pred_grids):
                pair_panels.append(("predicted", pred_grids[i]))

            if hasattr(test_pair, "output") and test_pair.output is not None:
                pair_panels.append(("answer", test_pair.output.contents))

            pairs_data.append(pair_panels)

        self._sections.append(
            _task_section(task_id, result, rule, method, pairs_data)
        )

    def write(self, path: str):
        html = _page(
            split=self.split,
            timestamp=self.timestamp,
            summary=self.summary,
            task_sections="\n".join(self._sections),
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
