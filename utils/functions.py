import psycopg2
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_settings):
    # In production, use environment variables or a config file for these values
    conn = psycopg2.connect(**db_settings)
    try:
        yield conn
    finally:
        conn.close()