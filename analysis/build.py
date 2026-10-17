#!/usr/bin/env python3
"""Export Fletcher's benchmark results and draw the README charts.

Reads a checkout of withmartian/code-review-benchmark in which the harness
has added Fletcher's reviews and the Gemini judge has scored them, plus the
JSON written by Martian's own dashboard script (the leaderboard's numbers:
Core category profile, hidden tools removed). Writes data/ and charts/ in
this repository. Standard library only.

    cd ~/path/to/code-review-benchmark/offline
    uv run python analysis/benchmark_dashboard.py --output /tmp/dash.html
    python3 analysis/build.py --martian ~/path/to/code-review-benchmark --dashboard /tmp/dash.json
"""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = "fletcher-gemini-3.8-flash"
GEMINI = "gemini-3.8-flash"

JUDGES = {
    "anthropic_claude-opus-4-5-20251101": "Opus 4.5",
    "anthropic_claude-sonnet-4-5-20250929": "Sonnet 4.5",
    "openai_gpt-5.2": "GPT-5.2",
    GEMINI: "Gemini 3.8 Flash",
}

NAMES = {
    TOOL: "Fletcher (Gemini 3.8 Flash)",
    "cubic-v2": "Cubic v2",
    "augment": "Augment",
    "qodo-extended-v2": "Qodo extended v2",
    "qodo-v2": "Qodo v2",
    "devin": "Devin",
    "qodo-extended-summary": "Qodo extended summary",
    "gitlab": "GitLab Duo",
    "greptile-v4-1": "Greptile v4.1",
    "greptile-v5": "Greptile v5",
    "bugbot": "Cursor Bugbot",
    "mergemonkey": "MergeMonkey",
    "propel-v2": "Propel v2",
    "qodo-v22": "Qodo v22",
    "macroscope": "Macroscope",
    "gitar": "Gitar",
    "copilot-v2": "Copilot v2",
    "gemini-v2": "Gemini v2",
    "graphite": "Graphite",
    "coderabbit": "CodeRabbit",
}

# The spread between Martian's own judges on the same tool (see README).
JUDGE_ERROR = 5.0

# Light card colours: SVGs in a README are shown as images, so each chart
# carries its own background and reads the same in GitHub's light and dark
# themes.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
QUIET = "#52514e"
MUTED = "#c3c2b7"
GRID = "#e8e7e3"
AXIS = "#9a9890"
ACCENT = "#2a78d6"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def name(tool):
    return NAMES.get(tool, tool)


def pooled(evaluations):
    """Micro-averaged precision, recall and F1 per tool over every PR."""
    totals = {}
    for tools in evaluations.values():
        for tool, result in tools.items():
            if not isinstance(result, dict) or result.get("skipped") or "tp" not in result:
                continue
            t = totals.setdefault(tool, {"tp": 0, "fp": 0, "fn": 0, "prs": 0})
            t["tp"] += result["tp"]
            t["fp"] += result["fp"]
            t["fn"] += result["fn"]
            t["prs"] += 1
    scores = {}
    for tool, t in totals.items():
        p = t["tp"] / (t["tp"] + t["fp"]) if t["tp"] + t["fp"] else 0.0
        r = t["tp"] / (t["tp"] + t["fn"]) if t["tp"] + t["fn"] else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        scores[tool] = {**t, "precision": round(p * 100, 1), "recall": round(r * 100, 1), "f1": round(f1 * 100, 1)}
    return scores


def svg(width, height, title, body):
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' width='{width}' "
        f"height='{height}' role='img' aria-label='{esc(title)}' font-family=\"{FONT}\" font-size='13'>"
        f"<rect width='{width}' height='{height}' rx='8' fill='{SURFACE}'/>{body}</svg>\n"
    )


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;")


def text(x, y, words, size=13, fill=INK, weight=400, anchor="start"):
    return (
        f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{fill}' font-weight='{weight}' "
        f"text-anchor='{anchor}'>{esc(words)}</text>"
    )


LEADERBOARD_JUDGE = "anthropic_claude-opus-4-5-20251101"


def leaderboard_chart(board, fletcher, names):
    """The leaderboard's default view: Core profile, F2, Opus 4.5 judge."""
    rows = sorted([(t, v) for t, v in board.items()] + [(TOOL, fletcher)], key=lambda x: -x[1]["f2"])
    rank = 1 + sum(1 for _, v in board.items() if v["f2"] > fletcher["f2"])
    title = f"On the leaderboard's default view, Fletcher's {fletcher['f2']:.1f}% F2 places {ordinal(rank)} of {len(rows)}"
    x0, scale, y0, step = 230, 7, 96, 26
    X = lambda v: x0 + v * scale
    y_end = y0 + (len(rows) - 1) * step + 18
    out = [text(24, 34, title, 17, INK, 600)]
    out.append(text(24, 56, "F2 (%), Core categories, on all 50 PRs: the 21 tools Martian's leaderboard shows, plus Fletcher", 12, QUIET))
    for v in range(0, 80, 10):
        out.append(f"<line x1='{X(v)}' x2='{X(v)}' y1='78' y2='{y_end}' stroke='{GRID}'/>")
        out.append(text(X(v), y_end + 18, v, 12, QUIET, anchor="middle"))
    out.append(f"<line x1='{X(0)}' x2='{X(70)}' y1='{y_end}' y2='{y_end}' stroke='{AXIS}'/>")
    for i, (tool, v) in enumerate(rows):
        y = y0 + i * step
        mine = tool == TOOL
        out.append(f"<rect x='{X(0)}' y='{y - 8}' width='{X(v['f2']) - X(0)}' height='16' rx='3' fill='{ACCENT if mine else MUTED}'/>")
        out.append(text(x0 - 10, y + 4.5, NAMES[TOOL] if mine else names.get(tool, name(tool)), 13, INK, 600 if mine else 400, "end"))
        end = v["f2"] + JUDGE_ERROR if mine else v["f2"]
        if mine:
            lo, hi = X(v["f2"] - JUDGE_ERROR), X(v["f2"] + JUDGE_ERROR)
            out.append(f"<path d='M{lo} {y}H{hi}M{lo} {y - 6}V{y + 6}M{hi} {y - 6}V{y + 6}' stroke='{INK}' stroke-width='1.25' fill='none'/>")
        out.append(text(X(end) + 7, y + 4.5, f"{v['f2']:.1f}", 12, INK if mine else QUIET, 600 if mine else 400))
    out.append(text(24, y_end + 46, "Others judged by Claude Opus 4.5, the leaderboard's default judge. Fletcher judged by Gemini 3.8 Flash, which scored", 12, QUIET))
    out.append(text(24, y_end + 64, f"CodeRabbit about 2.5 points below Opus on this metric. Whisker: ±{JUDGE_ERROR:.0f} points, the spread between Martian's judges.", 12, QUIET))
    return svg(760, y_end + 86, title, "".join(out))


def ranking_chart(sonnet, fletcher):
    """Top 16 tools under the Sonnet judge, with Fletcher placed by its score."""
    full = [(t, s) for t, s in sonnet.items() if s["prs"] >= 49]
    top = sorted(full, key=lambda x: -x[1]["f1"])[:16]
    rows = sorted(top + [(TOOL, fletcher)], key=lambda x: -x[1]["f1"])
    rank = 1 + sum(1 for _, s in full if s["f1"] > fletcher["f1"])
    title = f"Fletcher ranks {ordinal(rank)} of {len(full) + 1} tools on F1"
    x0, scale, y0, step = 230, 8, 96, 26
    X = lambda v: x0 + v * scale
    y_end = y0 + (len(rows) - 1) * step + 18
    out = [text(24, 34, title, 17, INK, 600)]
    out.append(text(24, 56, "F1 (%) on all 50 PRs of Martian's offline benchmark; top 16 tools plus Fletcher", 12, QUIET))
    for v in range(0, 70, 10):
        out.append(f"<line x1='{X(v)}' x2='{X(v)}' y1='78' y2='{y_end}' stroke='{GRID}'/>")
        out.append(text(X(v), y_end + 18, v, 12, QUIET, anchor="middle"))
    out.append(f"<line x1='{X(0)}' x2='{X(60)}' y1='{y_end}' y2='{y_end}' stroke='{AXIS}'/>")
    for i, (tool, s) in enumerate(rows):
        y = y0 + i * step
        mine = tool == TOOL
        out.append(f"<rect x='{X(0)}' y='{y - 8}' width='{X(s['f1']) - X(0)}' height='16' rx='3' fill='{ACCENT if mine else MUTED}'/>")
        out.append(text(x0 - 10, y + 4.5, name(tool), 13, INK, 600 if mine else 400, "end"))
        end = s["f1"] + JUDGE_ERROR if mine else s["f1"]
        if mine:
            lo, hi = X(s["f1"] - JUDGE_ERROR), X(s["f1"] + JUDGE_ERROR)
            out.append(f"<path d='M{lo} {y}H{hi}M{lo} {y - 6}V{y + 6}M{hi} {y - 6}V{y + 6}' stroke='{INK}' stroke-width='1.25' fill='none'/>")
        out.append(text(X(end) + 7, y + 4.5, f"{s['f1']:.1f}", 12, INK if mine else QUIET, 600 if mine else 400))
    out.append(text(24, y_end + 46, "Others judged by Claude Sonnet 4.5 (Martian's stored results). Fletcher judged by Gemini 3.8 Flash,", 12, QUIET))
    out.append(text(24, y_end + 64, f"which scored two tools within 1.5 points of Sonnet. Whisker: ±{JUDGE_ERROR:.0f} points, the spread between Martian's judges.", 12, QUIET))
    return svg(760, y_end + 86, title, "".join(out))


def calibration_chart(by_judge):
    tools = ["cubic-v2", "copilot-v2", "coderabbit", "greptile-v5", TOOL]
    title = "Judges move F1 by about 5 points; Gemini lands within 1.5 of Sonnet"
    x0, x1, lo, hi = 230, 712, 35, 65
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    y0, step = 132, 46
    y_end = y0 + (len(tools) - 1) * step + 26
    out = [text(24, 34, title, 17, INK, 600)]
    out.append(text(24, 56, "F1 (%) per tool under each judge model; the line is the spread across judges", 12, QUIET))
    legend = [("Opus 4.5", "circle"), ("Sonnet 4.5", "square"), ("GPT-5.2", "diamond"), ("Gemini 3.8 Flash", "dot")]
    for i, (judge, glyph) in enumerate(legend):
        out.append(mark(glyph, 30 + i * 170, 88))
        out.append(text(44 + i * 170, 92.5, f"{judge} judge", 12, QUIET))
    for v in range(lo, hi + 1, 5):
        out.append(f"<line x1='{X(v):.1f}' x2='{X(v):.1f}' y1='112' y2='{y_end}' stroke='{GRID}'/>")
        out.append(text(X(v), y_end + 18, v, 12, QUIET, anchor="middle"))
    out.append(f"<line x1='{x0}' x2='{x1}' y1='{y_end}' y2='{y_end}' stroke='{AXIS}'/>")
    glyphs = dict((j, g) for j, g in legend)
    for i, tool in enumerate(tools):
        y = y0 + i * step
        label = "Fletcher (50 PRs)" if tool == TOOL else name(tool)
        out.append(text(24, y + 4.5, label, 13, INK, 600 if tool == TOOL else 400))
        points = [(JUDGES[d], by_judge[d][tool]["f1"]) for d in JUDGES if tool in by_judge[d] and by_judge[d][tool]["prs"] >= 44]
        values = [v for _, v in points]
        out.append(f"<line x1='{X(min(values)):.1f}' x2='{X(max(values)):.1f}' y1='{y}' y2='{y}' stroke='{MUTED}' stroke-width='2'/>")
        for judge, v in points:
            out.append(mark(glyphs[judge], X(v), y))
            if judge == "Gemini 3.8 Flash":
                out.append(text(X(v), y - 12, f"{v:.1f}", 12, INK, 600, "middle"))
    out.append(text(24, y_end + 46, "Greptile v5 under Gemini: 44 of 50 PRs (the calibration run was stopped early); all others: 50 PRs.", 12, QUIET))
    return svg(760, y_end + 68, title, "".join(out))


def scatter_chart(full, fletcher, names):
    title = "Fletcher finds about half the issues, and about half its findings are real"
    lo = min(10, int(min(min(s["recall"], s["precision"]) for s in full.values()) // 10 * 10))
    hi = 100 if max(max(s["recall"], s["precision"]) for s in full.values()) > 80 else 80
    x0, x1, y_top, y_bot = 70, 724, 76, 476
    X = lambda r: x0 + (r - lo) / (hi - lo) * (x1 - x0)
    Y = lambda p: y_bot - (p - lo) / (hi - lo) * (y_bot - y_top)
    out = [text(24, 34, title, 17, INK, 600)]
    out.append(text(24, 56, f"Precision vs recall (%), Core categories, all 50 PRs; grey = the {len(full)} leaderboard tools under the Opus 4.5 judge", 12, QUIET))
    for v in range(lo, hi + 1, 10):
        out.append(f"<line x1='{X(v):.1f}' x2='{X(v):.1f}' y1='{y_top}' y2='{y_bot}' stroke='{GRID}'/>")
        out.append(f"<line x1='{x0}' x2='{x1}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' stroke='{GRID}'/>")
        out.append(text(X(v), y_bot + 18, v, 12, QUIET, anchor="middle"))
        out.append(text(x0 - 8, Y(v) + 4, v, 12, QUIET, anchor="end"))
    out.append(f"<path d='M{X(lo):.1f} {Y(lo):.1f}L{X(hi):.1f} {Y(hi):.1f}' stroke='{AXIS}' stroke-dasharray='4 4'/>")
    out.append(text(X(hi) - 6, Y(hi) + 16, "precision = recall", 11, QUIET, anchor="end"))
    for tool, s in full.items():
        out.append(f"<circle cx='{X(s['recall']):.1f}' cy='{Y(s['precision']):.1f}' r='5' fill='{MUTED}' stroke='{SURFACE}' stroke-width='2'/>")
    labels = {"devin": (8, -6, "start"), "copilot-v2": (8, 12, "start"), "cubic-v2": (8, -8, "start"),
              "augment": (8, 14, "start"), "coderabbit": (-8, 14, "end"), "graphite": (-8, 4, "end")}
    for tool, (dx, dy, anchor) in labels.items():
        if tool in full:
            s = full[tool]
            out.append(text(X(s["recall"]) + dx, Y(s["precision"]) + dy, names.get(tool, name(tool)), 12, QUIET, anchor=anchor))
    fx, fy = X(fletcher["recall"]), Y(fletcher["precision"])
    out.append(f"<circle cx='{fx:.1f}' cy='{fy:.1f}' r='7' fill='{ACCENT}' stroke='{SURFACE}' stroke-width='2'/>")
    out.append(text(fx - 12, fy + 4.5, "Fletcher", 13, INK, 600, "end"))
    out.append(text((x0 + x1) / 2, y_bot + 40, "Recall (%): share of golden issues found", 12, QUIET, anchor="middle"))
    out.append(f"<text transform='translate(22 {(y_top + y_bot) / 2}) rotate(-90)' font-size='12' fill='{QUIET}' text-anchor='middle'>Precision (%): share of findings that are real</text>")
    return svg(760, y_bot + 62, title, "".join(out))


def mark(glyph, x, y):
    if glyph == "circle":
        return f"<circle cx='{x:.1f}' cy='{y}' r='5' fill='{MUTED}'/>"
    if glyph == "square":
        return f"<rect x='{x - 5:.1f}' y='{y - 5}' width='10' height='10' fill='{MUTED}'/>"
    if glyph == "diamond":
        return f"<path d='M{x:.1f} {y - 6}l6 6l-6 6l-6 -6z' fill='{MUTED}'/>"
    return f"<circle cx='{x:.1f}' cy='{y}' r='6' fill='{ACCENT}'/>"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--martian", required=True, type=Path, help="code-review-benchmark checkout")
    parser.add_argument("--dashboard", required=True, type=Path, help="JSON from Martian's benchmark_dashboard.py")
    args = parser.parse_args()
    results = args.martian.expanduser() / "offline" / "results"

    by_judge = {d: pooled(json.loads((results / d / "evaluations.json").read_text())) for d in JUDGES}
    fletcher = by_judge[GEMINI][TOOL]
    sonnet = by_judge["anthropic_claude-sonnet-4-5-20250929"]

    data, charts = ROOT / "data", ROOT / "charts"
    data.mkdir(exist_ok=True)
    charts.mkdir(exist_ok=True)

    benchmark = json.loads((results / "benchmark_data.json").read_text())
    gemini_evals = json.loads((results / GEMINI / "evaluations.json").read_text())
    reviews = {
        url: {
            "pr_title": entry.get("pr_title"),
            "golden_comments": entry["golden_comments"],
            "fletcher": next(r for r in entry["reviews"] if r["tool"] == TOOL),
            "evaluation": gemini_evals[url][TOOL],
        }
        for url, entry in benchmark.items()
        if any(r["tool"] == TOOL for r in entry["reviews"])
    }
    (data / "fletcher-reviews.json").write_text(json.dumps(reviews, indent=2, ensure_ascii=False) + "\n")
    (data / "scores-by-judge.json").write_text(
        json.dumps({JUDGES[d]: dict(sorted(s.items(), key=lambda x: -x[1]["f1"])) for d, s in by_judge.items()}, indent=2) + "\n"
    )
    with open(data / "fletcher-per-pr.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pr", "golden", "matched", "missed", "not_in_golden", "precision", "recall", "input_tokens", "output_tokens", "cost_usd"])
        for url, r in reviews.items():
            e, meta = r["evaluation"], r["fletcher"]["fletcher"]
            w.writerow([url, e["total_golden"], e["tp"], e["fn"], e["fp"], round(e["precision"], 3), round(e["recall"], 3),
                        meta["input_tokens"], meta["output_tokens"], round(meta["cost_usd"], 4)])

    dashboard = json.loads(args.dashboard.expanduser().read_text())
    names = dashboard.get("tool_display_names", {})
    core = {
        JUDGES[j]: {t: v["core"] for t, v in m["overall_metrics"].items() if v["core"]["num_prs"] >= 49}
        for j, m in dashboard["models"].items()
    }
    fletcher_core = core[JUDGES[GEMINI]].pop(TOOL)
    board = {t: v for t, v in core[JUDGES[LEADERBOARD_JUDGE]].items()}
    (data / "leaderboard-core.json").write_text(json.dumps({
        "about": "Martian's dashboard numbers: Core category profile, hidden tools removed, micro-averaged over 50 PRs.",
        "fletcher_gemini_judge": fletcher_core,
        "by_judge": {j: dict(sorted(v.items(), key=lambda x: -x[1]["f2"])) for j, v in core.items()},
    }, indent=2) + "\n")

    (charts / "ranking.svg").write_text(leaderboard_chart(board, fletcher_core, names))
    (charts / "ranking-f1-all-tools.svg").write_text(ranking_chart(sonnet, fletcher))
    (charts / "judge-calibration.svg").write_text(calibration_chart(by_judge))
    (charts / "precision-recall.svg").write_text(scatter_chart(board, fletcher_core, names))
    for judge in (LEADERBOARD_JUDGE, "anthropic_claude-sonnet-4-5-20250929", "openai_gpt-5.2"):
        b = core[JUDGES[judge]]
        for key in ("f2", "f1"):
            print(f"{JUDGES[judge]:>11} {key}: rank {1 + sum(1 for v in b.values() if v[key] > fletcher_core[key])} of {len(b) + 1}")

    cost = sum(r["fletcher"]["fletcher"]["cost_usd"] for r in reviews.values())
    print(f"Fletcher: F1 {fletcher['f1']}%, precision {fletcher['precision']}%, recall {fletcher['recall']}% "
          f"over {fletcher['prs']} PRs ({fletcher['tp']} TP / {fletcher['fp']} FP / {fletcher['fn']} FN); "
          f"recorded review cost ${cost:.2f}")


if __name__ == "__main__":
    main()
