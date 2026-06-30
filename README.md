# text-to-sql

Natural-language questions → SQL over a real SQLite database, scored the way text-to-SQL should
be: by **execution accuracy** — do the generated and gold queries return the *same rows*? — not
by string match. It benchmarks four prompting strategies and shows *which* strategy fixes
*which* failure mode.

```bash
text-to-sql                      # deterministic mock (reproduces the numbers below)
text-to-sql --provider bedrock   # real Claude on AWS Bedrock (creds from .env / ~/.env)
text-to-sql --json
```

## Why execution accuracy

A query written with a different alias, column order, or whitespace **string-mismatches** the
gold query yet returns identical rows — string match marks it wrong. Worse, a query that's
*syntactically valid* can return the *wrong* rows (a missed join condition becomes a silent cross
join). Only **executing both queries and comparing result sets** tells you if the SQL is actually
correct. The benchmark runs every prediction against a seeded e-commerce DB (customers, products,
orders) and compares rows as an order-insensitive multiset (order-sensitive when the gold query
has `ORDER BY`).

## The two failure modes

A weak first attempt fails in two distinct ways, and the benchmark tags each question with the
one it triggers:

- **semantic** — valid SQL, **wrong rows** (missed join, aggregating the wrong table). Nothing
  errors, so a retry can't catch it — but **worked examples** teach the right pattern.
- **syntax** — **broken SQL that throws** (`FORM` typo, dangling `ON`). Examples don't reliably
  prevent a one-off slip, but a **self-correction retry** (feed the error back) fixes it.

## Measured results

`text-to-sql` on 12 questions (deterministic mock):

| strategy | exec acc | exact match | semantic | syntax |
|---|---|---|---|---|
| zero_shot | 41.7% | 16.7% | 0.00 | 0.00 |
| **few_shot** | 75.0% | 50.0% | **1.00** | 0.00 |
| **self_correct** | 66.7% | 41.7% | 0.00 | **1.00** |
| **few_shot_self_correct** | **100.0%** | 75.0% | 1.00 | 1.00 |

Two findings, both in the `semantic` / `syntax` (by-failure-mode) columns:

- **The failure modes are orthogonal and need different fixes.** Few-shot examples repair every
  *semantic* error (0.00 → 1.00) but **zero** syntax errors. Self-correction repairs every
  *syntax* error (0.00 → 1.00) but **zero** semantic errors. Neither alone clears 75%; only
  **combining** them reaches **100%**. A single "just add examples" or "just retry" reflex leaves
  half the failures on the table.
- **String match badly under-counts.** Zero-shot scores **42% by execution but only 17% by exact
  match** — string match flags correct-but-reworded SQL (`SELECT *` vs explicit columns,
  whitespace) as wrong. If you grade text-to-SQL by string equality you'll understate a good
  model by ~25 points and pick the wrong winner.

## Real-model mode

`--provider bedrock` (or `anthropic`) runs the **same four strategies with a live Claude model** —
zero-shot builds the prompt from the schema, few-shot prepends worked examples, and
self-correction re-prompts with the SQLite error message on an execution failure. Execution
accuracy is computed identically, so mock and real are directly comparable. Creds load from
`.env` or the global `~/.env`; no key → the deterministic mock, so CI reproduces every number free.

## Install & test

```bash
pip install -e ".[dev]"               # mock path
pip install -e ".[dev,bedrock]"       # + AWS Bedrock (or ".[dev,claude]" for the Anthropic API)
pytest -q                             # 5 passed (mock — deterministic, no network)
```

## Stack

Pure-stdlib SQLite (in-memory seeded DB), execution-based result-set scoring, a deterministic
mock generator + real Claude on AWS Bedrock / Anthropic API, pytest.

## License

MIT
