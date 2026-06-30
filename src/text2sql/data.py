"""The benchmark: NL questions with gold SQL, plus the mock generator's per-strategy outputs.

Each question carries a `failure` mode that a naive zero-shot pass falls into:
  * none     — answered correctly zero-shot (some via an equivalent-but-differently-worded query,
               which is why execution accuracy > string match).
  * semantic — zero-shot emits *valid* SQL that returns the *wrong rows* (missed join, wrong
               aggregate). Examples fix this (few-shot); a retry can't — nothing errored.
  * syntax   — zero-shot emits *broken* SQL that throws. A self-correction retry fixes this;
               examples don't reliably prevent a one-off slip.

`zeroshot` is what a weak first attempt produces; `fewshot_fixes` says whether showing worked
examples upgrades that attempt to the gold query.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Question:
    qid: str
    question: str
    gold: str
    failure: str            # none | semantic | syntax
    zeroshot: str           # the mock's weak first attempt
    fewshot_fixes: bool     # do examples upgrade zeroshot -> gold?


QUESTIONS = [
    # ---- easy: zero-shot correct (some reworded -> exec-correct but string-different) ----
    Question("q1", "List the names of all customers.",
             "SELECT name FROM customers",
             "none", "SELECT name FROM customers", False),
    Question("q2", "Show all customer records.",
             "SELECT id, name, country FROM customers",
             "none", "SELECT * FROM customers", False),            # equivalent, string-different
    Question("q3", "Which customers are from Canada?",
             "SELECT name FROM customers WHERE country='Canada'",
             "none", "SELECT name FROM customers WHERE country = 'Canada'", False),  # whitespace
    Question("q4", "List the names of products in the Books category.",
             "SELECT name FROM products WHERE category='Books'",
             "none", "SELECT name FROM products WHERE category='Books'", False),
    Question("q5", "What is the price of the product named Widget?",
             "SELECT price FROM products WHERE name='Widget'",
             "none", "SELECT price FROM products WHERE name = 'Widget'", False),

    # ---- semantic: valid SQL, wrong rows; few-shot examples fix it ----
    Question("q6", "Names of customers who ordered the product 'Widget'.",
             "SELECT DISTINCT c.name FROM customers c JOIN orders o ON c.id=o.customer_id "
             "JOIN products p ON o.product_id=p.id WHERE p.name='Widget'",
             "semantic",
             "SELECT name FROM customers WHERE id IN (SELECT customer_id FROM orders)",  # all buyers
             True),
    Question("q7", "Total revenue per category (price times quantity).",
             "SELECT p.category, SUM(p.price*o.quantity) AS revenue FROM products p "
             "JOIN orders o ON p.id=o.product_id GROUP BY p.category",
             "semantic",
             "SELECT category, SUM(price) AS revenue FROM products GROUP BY category",  # ignores orders
             True),
    Question("q8", "How many orders has each customer placed? Show the customer name.",
             "SELECT c.name, COUNT(o.id) AS n FROM customers c JOIN orders o "
             "ON c.id=o.customer_id GROUP BY c.id",
             "semantic",
             "SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id",  # ids, not names
             True),
    Question("q9", "Which category has the highest total revenue?",
             "SELECT p.category FROM products p JOIN orders o ON p.id=o.product_id "
             "GROUP BY p.category ORDER BY SUM(p.price*o.quantity) DESC LIMIT 1",
             "semantic",
             "SELECT category FROM products p JOIN orders o ON p.id=o.product_id "
             "GROUP BY category ORDER BY SUM(p.price) DESC LIMIT 1",  # ignores quantity
             True),

    # ---- syntax: broken SQL that throws; a retry fixes it, examples don't ----
    Question("q10", "List each customer name alongside the product names they ordered.",
             "SELECT c.name, p.name FROM customers c JOIN orders o ON c.id=o.customer_id "
             "JOIN products p ON o.product_id=p.id",
             "syntax",
             "SELECT c.name, p.name FROM customers c JOIN orders o ON c.id=o.customer_id "
             "JOIN products p ON o.product_id =",                  # dangling ON -> syntax error
             False),
    Question("q11", "What is the average order quantity?",
             "SELECT AVG(quantity) FROM orders",
             "syntax", "SELECT AVG(quantity) FORM orders", False),  # FORM typo -> error
    Question("q12", "How many products are there in total?",
             "SELECT COUNT(*) FROM products",
             "syntax", "SELECT COUNT() FROM", False),               # incomplete -> error
]


def questions() -> list[Question]:
    return list(QUESTIONS)
