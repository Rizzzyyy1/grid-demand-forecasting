"""Write the README results section from reports/runs/*/ (numbers are generated, never typed).

Usage: python scripts/collect_results.py [--readme] [--run=<run_id>]  # default: print to stdout
By default the validation run with the most models (newest on ties) is used; the test split is only reported
once it has been evaluated (reports/TEST_SPLIT_EVALUATED.json exists).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "reports" / "runs"
START, END = "<!-- results:start -->", "<!-- results:end -->"


def latest_run(split: str) -> Path | None:
    """Newest run of ``split`` with the most models (a combined run beats its parts)."""
    candidates = []
    for cfg in RUNS.glob("*/config.json"):
        c = json.loads(cfg.read_text())
        if c["split"] == split and not c["run_id"].endswith("smoke") and not c.get("superseded"):
            candidates.append((len(c["models"]), cfg.parent.name, cfg.parent))
    return max(candidates)[2] if candidates else None


def render(run: Path) -> str:
    cfg = json.loads((run / "config.json").read_text())
    point = pl.read_csv(run / "metrics_point.csv")
    models = [
        m
        for m in cfg.get("models_scored", cfg["models"])
        if m in point["model"].to_list() and not m.endswith("+cqr")
    ]
    wide = point.pivot(on="model", index="ba_code", values="mape").sort("ba_code")
    ours = [m for m in models if not m.startswith("operator")]
    lines = [
        f"Validation run `{cfg['run_id']}` · target days {cfg['window'][0]} → {cfg['window'][1]} · "
        f"{cfg['refits']} monthly refits · leakage check: {cfg['leakage']['cells_checked']:,} "
        f"feature values, {cfg['leakage']['violations']} violations.",
        "",
        "**MAPE (%) by region** (lower is better; bold = best of our models):",
        "",
        "| BA | " + " | ".join(models) + " |",
        "|---|" + "---|" * len(models),
    ]
    for row in wide.iter_rows(named=True):
        best = min((row[m] for m in ours if row.get(m) is not None), default=None)
        cells = []
        for m in models:
            v = row.get(m)
            cells.append("—" if v is None else (f"**{v:.2f}**" if v == best else f"{v:.2f}"))
        lines.append(f"| {row['ba_code']} | " + " | ".join(cells) + " |")
    comps_path = run / "comparisons.csv"
    if comps_path.exists():
        comps = pl.read_csv(comps_path).filter(pl.col("reference") == "operator_debiased")
        best_model = (
            pl.read_csv(run / "metrics_overall.csv")
            .filter(
                ~pl.col("model").str.starts_with("operator")
                & ~pl.col("model").str.ends_with("+cqr")
            )
            .sort("mape")["model"][0]
        )
        sub = comps.filter(pl.col("model") == best_model).sort("ba_code")
        wins = sub.filter((pl.col("skill_low") > 0) & (pl.col("dm_p") < 0.05)).height
        losses = sub.filter((pl.col("skill_high") < 0) & (pl.col("dm_p") < 0.05)).height
        lines += [
            "",
            f"**Skill of `{best_model}` vs the debiased operator forecast** (1 - MAE/MAE_ref; "
            f"95 % moving-block bootstrap CI; Diebold-Mariano p): significantly better in {wins}, "
            f"significantly worse in {losses}, inconclusive in {sub.height - wins - losses} of "
            f"{sub.height} regions.",
            "",
            "| BA | skill | 95 % CI | DM p |",
            "|---|---|---|---|",
        ]
        for r in sub.iter_rows(named=True):
            lines.append(
                f"| {r['ba_code']} | {r['skill']:+.3f} | [{r['skill_low']:+.3f}, "
                f"{r['skill_high']:+.3f}] | {r['dm_p']:.2g} |"
            )
    lines += [
        "",
        f"Full tables: [`reports/runs/{run.name}/summary.md`](reports/runs/{run.name}/summary.md).",
    ]
    return "\n".join(lines)


def main() -> None:
    explicit = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--run=")]
    run = RUNS / explicit[0] if explicit else latest_run("validation")
    body = render(run) if run else "— (no validation run yet: `gridcast backtest`)"
    if "--readme" not in sys.argv:
        print(body)
        return
    readme = ROOT / "README.md"
    text = readme.read_text()
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    readme.write_text(f"{head}{START}\n{body}\n{END}{tail}")
    print(f"updated README from {run.name if run else 'nothing'}")


if __name__ == "__main__":
    main()
