import os
import html
import re
import json
import io
import sqlite3
import secrets
from pathlib import Path

try:
    import libsql
except ImportError:
    libsql = None

try:
    from opencc import OpenCC
except Exception:
    OpenCC = None

try:
    from hanziconv import HanziConv
except Exception:
    HanziConv = None

try:
    import qrcode
except Exception:
    qrcode = None

from flask import Flask, jsonify, render_template, request, send_file

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "poetry.db"
DB_PATH = Path(os.environ.get("POETRY_DB_PATH", str(DEFAULT_DB_PATH)))


def get_conn():
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if url and token and libsql:
        try:
            conn = libsql.connect(url, auth_token=token)
            return conn
        except Exception:
            pass
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    raise RuntimeError("Database not available")


def execute_query(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    if rows and isinstance(rows[0], tuple):
        cols = [col[0] for col in cur.description]
        mapped = [dict(zip(cols, row)) for row in rows]
        conn.close()
        return mapped
    conn.close()
    return [dict(row) for row in rows]


def execute_query_single(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    if isinstance(row, tuple):
        cols = [col[0] for col in cur.description]
        mapped = dict(zip(cols, row))
        conn.close()
        return mapped
    conn.close()
    return dict(row)


def execute_write(query, params=()):
    conn = get_conn()
    conn.execute(query, params)
    conn.commit()
    conn.close()


app = Flask(__name__)

# ... (rest of your existing code: S2T, T2S, RAW_CATEGORY_ALIASES, functions, routes, etc. remain unchanged)

# Vercel needs this exposed at top level
application = app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
