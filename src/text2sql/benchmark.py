"""Run every strategy over the question set, scoring by execution accuracy (and exact match,
for contrast). A fresh DB connection per query keeps runs isolated."""
from __future__ import annotations

from .data import questions
from .db import connect
from .evaluate import exact_match, execution_match
from .generator import STRATEGIES


def _run_strategy(strategy: str, generator) -> dict:
    qs = questions()
    exec_ok = exact_ok = 0
    per_failure = {}
    for q in qs:
        con = connect()
        pred = generator.generate(strategy, q, con)
        em = execution_match(con, pred, q.gold)
        exec_ok += em
        exact_ok += exact_match(pred, q.gold)
        d = per_failure.setdefault(q.failure, [0, 0])
        d[0] += em
        d[1] += 1
        con.close()
    n = len(qs)
    return {
        "strategy": strategy,
        "execution_accuracy": round(exec_ok / n, 4),
        "exact_match": round(exact_ok / n, 4),
        "by_failure": {k: round(v[0] / v[1], 4) for k, v in per_failure.items()},
        "n": n,
    }


def run(generator) -> dict:
    rows = [_run_strategy(s, generator) for s in STRATEGIES]
    best = max(rows, key=lambda r: r["execution_accuracy"])
    return {"strategies": {r["strategy"]: r for r in rows},
            "best": best["strategy"],
            "_meta": {"n": rows[0]["n"], "provider": type(generator).__name__}}
