import sqlite3

from text2sql.benchmark import run
from text2sql.data import questions
from text2sql.db import connect
from text2sql.evaluate import exact_match, execution_match
from text2sql.generator import MockGenerator


def test_gold_sql_all_execute():
    for q in questions():
        con = connect()
        con.execute(q.gold).fetchall()   # must not raise
        con.close()


def test_zeroshot_failures_behave_as_tagged():
    gen = MockGenerator()
    for q in questions():
        con = connect()
        pred = gen.generate("zero_shot", q, con)
        ok = execution_match(con, pred, q.gold)
        if q.failure == "none":
            assert ok, q.qid              # easy ones correct zero-shot
        else:
            assert not ok, q.qid          # semantic/syntax ones wrong zero-shot
        con.close()


def test_execution_beats_exact_match():
    # an equivalent but reworded query: same rows, different string
    con = connect()
    assert execution_match(con, "SELECT * FROM customers",
                           "SELECT id, name, country FROM customers")
    assert not exact_match("SELECT * FROM customers",
                           "SELECT id, name, country FROM customers")
    con.close()


def test_strategy_lift_and_failure_specificity():
    res = run(MockGenerator())["strategies"]
    z = res["zero_shot"]["execution_accuracy"]
    fs = res["few_shot"]["execution_accuracy"]
    sc = res["self_correct"]["execution_accuracy"]
    both = res["few_shot_self_correct"]["execution_accuracy"]
    # each technique adds lift; the combination is best
    assert z < fs and z < sc
    assert both > fs and both > sc
    assert both == 1.0
    # the honest finding: few-shot fixes semantic errors, self-correct fixes syntax errors
    assert res["few_shot"]["by_failure"]["semantic"] == 1.0
    assert res["few_shot"]["by_failure"]["syntax"] == 0.0
    assert res["self_correct"]["by_failure"]["syntax"] == 1.0
    assert res["self_correct"]["by_failure"]["semantic"] == 0.0


def test_string_match_undercounts_zero_shot():
    res = run(MockGenerator())["strategies"]
    z = res["zero_shot"]
    assert z["exact_match"] < z["execution_accuracy"]
