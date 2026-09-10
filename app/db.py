from contextlib import contextmanager

import psycopg

from app.config import DATABASE_URL


@contextmanager
def get_connection():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_schema(schema_path: str = "db/schema.sql") -> None:
    with open(schema_path, encoding="utf-8") as f:
        schema_sql = f.read()
    with get_connection() as conn:
        conn.execute(schema_sql)
