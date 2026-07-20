# text-to-sql

Natural-language questions → SQL over a real SQLite database, scored the way text-to-SQL should
be: by **execution accuracy**, do the generated and gold queries return the *same rows*?, not
by string match. It benchmarks four prompting strategies and shows *which* strategy fixes
*which* failure mode.

```bash
text-to-sql --provider bedrock   # real Claude on AWS Bedrock (the numbers below; creds from .env / ~/.env)
text-to-sql                      # deterministic offline mock (a contrasting teaching fixture)
text-to-sql --json
```

## Why execution accuracy

A query written with a different alias, column order, or whitespace **string-mismatches** the
gold query yet returns identical rows, string match marks it wrong. Worse, a query that's
*syntactically valid* can return the *wrong* rows (a missed join condition becomes a silent cross
join). Only **executing both queries and comparing result sets** tells you if the SQL is actually
correct. The benchmark runs every prediction against a seeded e-commerce DB (customers, products,
orders) and compares rows as an order-insensitive multiset (order-sensitive when the gold query
has `ORDER BY`).

## The two failure modes

A weak first attempt fails in two distinct ways, and the benchmark tags each question with the
one it triggers:

- **semantic**, valid SQL, **wrong rows** (missed join, aggregating the wrong table). Nothing
  errors, so a retry can't catch it, but **worked examples** teach the right pattern.
- **syntax**, **broken SQL that throws** (`FORM` typo, dangling `ON`). Examples don't reliably
  prevent a one-off slip, but a **self-correction retry** (feed the error back) fixes it.

## Measured results

Real run, **Claude Haiku 4.5 on AWS Bedrock**, 12 questions (execution accuracy = do the generated
and gold SQL return the same rows?). The `none / semantic / syntax` columns are execution accuracy
*within* each question subset (plain questions / semantic-trap questions / syntax-trap questions):

| strategy | exec acc | exact match | none | semantic | syntax |
|---|---|---|---|---|---|
| zero_shot | 83.3% | 25.0% | 0.80 | 0.75 | 1.00 |
| **few_shot** | **100.0%** | 58.3% | 1.00 | 1.00 | 1.00 |
| self_correct | 83.3% | 25.0% | 0.80 | 0.75 | 1.00 |
| **few_shot_self_correct** | **100.0%** | 58.3% | 1.00 | 1.00 | 1.00 |

Two findings, the first one is where the real model **overturned** what the offline mock assumed:

- **On the real model, self-correction was a no-op, few-shot alone hit 100%.** Claude Haiku made
  essentially **no syntax errors** (syntax-subset accuracy 1.00 even zero-shot), so there was nothing
  for self-correction to catch: `self_correct` scored **83.3%, identical to zero-shot**. The residual
  failures were all *semantic* (valid SQL, wrong rows, the semantic subset sat at 0.75), and few-shot
  examples repaired those (→ 1.00), lifting the whole set to **100%**. The calibrated mock assumed the
  two failure modes were orthogonal and *both* fixes were needed; the real model's failures were
  purely semantic, so the "just add examples" reflex was, on this model, exactly right. That gap
  between the assumed and the measured story is the reason to run it live.
- **String match badly under-counts, even more on the real model.** Zero-shot scored **83% by
  execution but only 25% by exact match**, a **58-point gap**: Claude rewords correct SQL constantly
  (`SELECT *` vs explicit columns, whitespace, aliasing), and string equality flags all of it wrong.
  Grade text-to-SQL by string match and you'll understate a good model by nearly 60 points and pick
  the wrong winner.

> The offline `--mock` path (a deterministic generator with *designed* orthogonal failure modes)
> reproduces a contrasting table, zero_shot 41.7%, few_shot 75.0%, self_correct 66.7%, combined
> 100.0%, where both fixes are needed. Keeping it makes the comparison explicit: the mock is a
> teaching fixture; the numbers above are the real model's actual behavior.

## Real-model mode

`--provider bedrock` (or `anthropic`) runs the **same four strategies with a live Claude model**, 
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
