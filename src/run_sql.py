"""Load the SIMULATED tables into DuckDB, score comments (lexicon, no LLM), run sql/01-04, export results.

Usage: python src/run_sql.py      -> data/processed/*.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexicon import classify_themes, label, sentiment_score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SIM, PROC, SQL = ROOT / "data" / "simulated", ROOT / "data" / "processed", ROOT / "sql"
TABLES = ["posts", "ads_spend", "export_settings", "accounts_daily", "comments_sample", "creators", "creators_weekly",
          "mentions", "campaigns"]
EXPORT = ["posts_h", "kpi_month_mpf", "kpi_month_mp", "kpi_month_market", "share_of_voice", "group_totals", "anomalies",
          "dq_sponsored", "dq_timezone", "dq_duplicates", "dq_definition", "creator_growth", "creator_scores",
          "comments_scored", "metric_map"]


def score_comments(c: pd.DataFrame) -> pd.DataFrame:
    c = c.copy()
    c["score"] = [sentiment_score(t, l) for t, l in zip(c.text, c.lang)]
    c["label"] = c.score.map(label)
    th = pd.DataFrame([classify_themes(t) for t in c.text])
    return pd.concat([c.drop(columns="text"), th.add_prefix("theme_")], axis=1)


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto(?, header=true)", [str(SIM / f"{t}.csv")])
    con.register("cs_df", score_comments(pd.read_csv(SIM / "comments_sample.csv")))
    con.execute("CREATE TABLE comments_scored AS SELECT * FROM cs_df")
    for f in sorted(SQL.glob("0*.sql")):
        con.execute(f.read_text(encoding="utf-8"))
    return con


def main():
    PROC.mkdir(parents=True, exist_ok=True)
    con = connect()
    for t in EXPORT:
        df = con.execute(f"SELECT * FROM {t}").df()
        df = df.round(10).sort_values(list(df.columns), kind="mergesort").reset_index(drop=True)  # deterministic output
        df.to_csv(PROC / f"{t}.csv", index=False)
    n = con.execute("SELECT COUNT(*) FROM anomalies WHERE flagged").fetchone()[0]
    print(f"SQL done: {len(EXPORT)} tables exported, {n} flagged KPI-months")
    import analyse  # detection rules, communities, fact sheet
    analyse.main()


if __name__ == "__main__":
    main()
