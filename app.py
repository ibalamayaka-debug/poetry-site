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

S2T = OpenCC("s2t") if OpenCC else None
T2S = OpenCC("t2s") if OpenCC else None

RAW_CATEGORY_ALIASES = {
    "error": "未分类",
    "json": "未分类",
    "huajianji": "花间集",
    "nantang": "南唐词",
}

DISPLAY_TO_RAW_CATEGORIES = {}
for raw_name, display_name in RAW_CATEGORY_ALIASES.items():
    DISPLAY_TO_RAW_CATEGORIES.setdefault(display_name, set()).add(raw_name)


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


def to_simplified(text):
    if T2S:
        return T2S.convert(text)
    return text

# ... 其他所有函数和路由保持不变 ...

# ==================== Vercel 必须暴露的变量 ====================
application = app
handler = app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
