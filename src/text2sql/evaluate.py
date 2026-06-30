"""Execution-based scoring. The right metric for text-to-SQL isn't string match — a correct
query written with different aliases or whitespace string-mismatches the gold yet returns the
same rows. We compare *result sets*: run both queries, compare the rows (as a multiset, order-
insensitive unless the query is explicitly ordered)."""
from __future__ import annotations

import sqlite3


def run_sql(con: sqlite3.Connection, sql: str):
    """Execute and return rows, or raise sqlite3.Error on bad SQL."""
    cur = con.execute(sql)
    return cur.fetchall()


def _normalize(rows, ordered: bool):
    # rows are tuples; compare as a sorted multiset unless the query fixed an order
    return rows if ordered else sorted(rows, key=lambda r: tuple(str(x) for x in r))


def execution_match(con: sqlite3.Connection, pred_sql: str, gold_sql: str) -> bool:
    """True iff pred executes and returns the same result set as gold."""
    ordered = "order by" in gold_sql.lower()
    try:
        gold_rows = run_sql(con, gold_sql)
    except sqlite3.Error:
        return False  # gold should never error; treat as no-match if it somehow does
    try:
        pred_rows = run_sql(con, pred_sql)
    except sqlite3.Error:
        return False  # pred threw -> wrong
    return _normalize(pred_rows, ordered) == _normalize(gold_rows, ordered)


def exact_match(pred_sql: str, gold_sql: str) -> bool:
    """Naive string equality (whitespace/case-normalized) — shown only to contrast with execution
    accuracy; it under-counts correct-but-differently-written queries."""
    norm = lambda s: " ".join(s.lower().split())
    return norm(pred_sql) == norm(gold_sql)


def sql_errors(con: sqlite3.Connection, sql: str) -> bool:
    try:
        run_sql(con, sql)
        return False
    except sqlite3.Error:
        return True
