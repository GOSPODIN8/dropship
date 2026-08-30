# -*- coding: utf-8 -*-
"""
Простое хранилище на SQLite: кто зашёл в бота, кто купил гайд.
Не требует установки отдельной СУБД — файл базы создаётся автоматически.
"""
import sqlite3
from datetime import datetime
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_seen TEXT,
            got_free_lesson INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            amount_stars INTEGER,
            telegram_payment_charge_id TEXT,
            purchased_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def upsert_user(user_id: int, username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (user_id, username, first_seen) VALUES (?, ?, ?)",
            (user_id, username, datetime.utcnow().isoformat())
        )
    else:
        cur.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()
    conn.close()


def mark_free_lesson_sent(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET got_free_lesson = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_purchase(user_id: int, username: str, amount_stars: int, charge_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO purchases (user_id, username, amount_stars, telegram_payment_charge_id, purchased_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, username, amount_stars, charge_id, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def has_purchased(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM purchases WHERE user_id = ? LIMIT 1", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None


def stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), COALESCE(SUM(amount_stars),0) FROM purchases")
    total_purchases, total_stars = cur.fetchone()
    conn.close()
    return {
        "total_users": total_users,
        "total_purchases": total_purchases,
        "total_stars": total_stars,
    }
