"""A small, deterministic SQLite database the questions run against — an e-commerce schema
(customers, products, orders) with seeded rows. Built in-memory so every run is identical and
no file or external DB is needed."""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT);
CREATE TABLE products  (id INTEGER PRIMARY KEY, name TEXT, price REAL, category TEXT);
CREATE TABLE orders    (id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER,
                        quantity INTEGER, order_date TEXT);
"""

_CUSTOMERS = [
    (1, "Alice", "Canada"), (2, "Bob", "USA"), (3, "Carlos", "Canada"),
    (4, "Diana", "UK"), (5, "Eve", "USA"),
]
_PRODUCTS = [
    (1, "Widget", 9.99, "Hardware"), (2, "Gadget", 19.99, "Hardware"),
    (3, "Manual", 4.99, "Books"), (4, "Course", 49.99, "Books"),
    (5, "Cable", 2.99, "Hardware"),
]
_ORDERS = [
    (1, 1, 1, 3, "2026-01-05"), (2, 1, 3, 1, "2026-01-06"), (3, 2, 2, 2, "2026-01-07"),
    (4, 3, 1, 5, "2026-02-01"), (5, 3, 4, 1, "2026-02-02"), (6, 4, 2, 1, "2026-02-03"),
    (7, 5, 5, 10, "2026-03-01"), (8, 5, 1, 2, "2026-03-02"), (9, 2, 4, 1, "2026-03-03"),
    (10, 1, 2, 1, "2026-03-04"),
]


def schema_text() -> str:
    """The CREATE statements, shown to the model so it knows the tables/columns."""
    return SCHEMA.strip()


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO customers VALUES (?,?,?)", _CUSTOMERS)
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", _PRODUCTS)
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", _ORDERS)
    con.commit()
    return con
