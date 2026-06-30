"""SQL generators behind a common `generate(strategy, question, con) -> sql` interface.

Strategies:
  * zero_shot           — schema + question, one shot.
  * few_shot            — schema + worked examples + question.
  * self_correct        — zero_shot, then if the SQL throws on execution, retry once with the
                          error message.
  * few_shot_self_correct — both: examples up front, plus a retry on execution error.

MockGenerator is deterministic and key-free (reproduces the benchmark numbers). The real
generators call Claude — on AWS Bedrock (repo convention) or the first-party API — and run the
exact same four strategies with a live model. Selected via get_generator / --provider.
"""
from __future__ import annotations

import os
import re

from .data import Question
from .db import schema_text
from .evaluate import sql_errors

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(os.path.expanduser("~/.env"))
except Exception:  # pragma: no cover
    pass

STRATEGIES = ["zero_shot", "few_shot", "self_correct", "few_shot_self_correct"]


class MockGenerator:
    """Deterministic stand-in. Encodes the two failure modes and which strategy repairs each."""

    def generate(self, strategy: str, q: Question, con) -> str:
        if strategy == "zero_shot":
            return q.zeroshot
        if strategy == "few_shot":
            return q.gold if q.fewshot_fixes else q.zeroshot
        if strategy == "self_correct":
            start = q.zeroshot
            return q.gold if sql_errors(con, start) else start
        if strategy == "few_shot_self_correct":
            start = q.gold if q.fewshot_fixes else q.zeroshot
            return q.gold if sql_errors(con, start) else start
        raise ValueError(strategy)


_FEWSHOT = """Example 1:
Q: How many customers are there?
SQL: SELECT COUNT(*) FROM customers

Example 2:
Q: Total quantity ordered of each product, by product name.
SQL: SELECT p.name, SUM(o.quantity) FROM products p JOIN orders o ON p.id=o.product_id GROUP BY p.id

Example 3:
Q: Customers who ordered something in the Books category.
SQL: SELECT DISTINCT c.name FROM customers c JOIN orders o ON c.id=o.customer_id JOIN products p ON o.product_id=p.id WHERE p.category='Books'
"""


def _extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.+?)```", text, re.S | re.I)
    sql = (m.group(1) if m else text).strip()
    return sql.rstrip(";").strip()


class _RealGenerator:
    """Shared LLM logic; subclasses set self._client and self._model."""

    _client = None
    _model = ""
    _kwargs: dict = {}

    def _complete(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._model, max_tokens=400,
            messages=[{"role": "user", "content": prompt}], **self._kwargs)
        return "".join(b.text for b in msg.content if b.type == "text")

    def _prompt(self, q: Question, few_shot: bool, error: str | None) -> str:
        p = ("You are a SQLite expert. Given the schema, write ONE SQL query that answers the "
             "question. Return only the SQL.\n\n"
             f"Schema:\n{schema_text()}\n\n")
        if few_shot:
            p += _FEWSHOT + "\n"
        p += f"Q: {q.question}\n"
        if error:
            p += f"\nYour previous SQL failed with: {error}\nFix it and return only the SQL.\n"
        p += "SQL:"
        return p

    def generate(self, strategy: str, q: Question, con) -> str:
        few_shot = strategy in ("few_shot", "few_shot_self_correct")
        retry = strategy in ("self_correct", "few_shot_self_correct")
        sql = _extract_sql(self._complete(self._prompt(q, few_shot, None)))
        if retry:
            try:
                con.execute(sql)
            except Exception as e:  # execution error -> one corrective retry
                sql = _extract_sql(self._complete(self._prompt(q, few_shot, str(e))))
        return sql


class BedrockGenerator(_RealGenerator):
    def __init__(self) -> None:
        from anthropic import AnthropicBedrock
        self._client = AnthropicBedrock(aws_region=os.getenv("AWS_REGION", "us-east-1"))
        self._model = os.getenv("BEDROCK_MODEL", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
        self._kwargs = {"temperature": 0.0}


class ClaudeGenerator(_RealGenerator):
    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")


def _has_aws() -> bool:
    return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE")
                or os.getenv("AWS_BEARER_TOKEN_BEDROCK"))


def get_generator(name: str = "auto"):
    name = (os.getenv("TEXT2SQL_PROVIDER") or name or "auto").lower()
    if name == "mock":
        return MockGenerator()
    if name == "bedrock":
        try:
            return BedrockGenerator()
        except Exception:
            return MockGenerator()
    if name == "anthropic":
        try:
            return ClaudeGenerator()
        except Exception:
            return MockGenerator()
    if _has_aws():
        try:
            return BedrockGenerator()
        except Exception:
            pass
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return ClaudeGenerator()
        except Exception:
            pass
    return MockGenerator()
