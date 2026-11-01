import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

_conn = None


def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(os.getenv("DATABASE_URL"), autocommit=True, prepare_threshold=None)
    return _conn