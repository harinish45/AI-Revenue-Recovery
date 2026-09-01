"""resolve_connect_args used to be an unconditional
{"check_same_thread": False} baked straight into create_engine() -- a
SQLite-only DBAPI argument. The README documents DATABASE_URL as "the only
thing that changes" to move this to Postgres in production; without this
guard that claim was false and pointing DATABASE_URL at Postgres would have
crashed at import time with a TypeError from psycopg2's connect()."""

from app.database import resolve_connect_args


def test_sqlite_url_gets_the_check_same_thread_arg():
    assert resolve_connect_args("sqlite:///./recoverai.db") == {"check_same_thread": False}


def test_postgres_url_gets_no_sqlite_specific_args():
    assert resolve_connect_args("postgresql://user:pass@localhost:5432/recoverai") == {}


def test_mysql_url_gets_no_sqlite_specific_args():
    assert resolve_connect_args("mysql+pymysql://user:pass@localhost:3306/recoverai") == {}
