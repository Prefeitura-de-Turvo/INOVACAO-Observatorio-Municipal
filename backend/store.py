import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def now():
    return datetime.now(UTC).isoformat()


@contextmanager
def connection():
    path = Path(os.getenv("DATABASE_PATH", "data/observatorio.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        "CREATE TABLE IF NOT EXISTS cache (id TEXT PRIMARY KEY, payload TEXT, success_at TEXT, attempt_at TEXT, error TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT, detail TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS evidence (id INTEGER PRIMARY KEY, indicator TEXT, collected_at TEXT, response TEXT)"
    )
    db.execute("CREATE TABLE IF NOT EXISTS locks (name TEXT PRIMARY KEY, until_at REAL)")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def save(id, payload, evidence):
    timestamp = now()
    with connection() as db:
        db.execute(
            "INSERT INTO evidence(indicator,collected_at,response) VALUES(?,?,?)",
            (id, timestamp, json.dumps(evidence, ensure_ascii=False)),
        )
        db.execute(
            "INSERT INTO cache VALUES(?,?,?,?,NULL) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,success_at=excluded.success_at,attempt_at=excluded.attempt_at,error=NULL",
            (id, json.dumps(payload, ensure_ascii=False), timestamp, timestamp),
        )


def fail(id, message):
    with connection() as db:
        db.execute(
            "INSERT INTO cache VALUES(?,NULL,NULL,?,?) ON CONFLICT(id) DO UPDATE SET attempt_at=excluded.attempt_at,error=excluded.error",
            (id, now(), message),
        )


def read_all():
    with connection() as db:
        return {r["id"]: dict(r) for r in db.execute("SELECT * FROM cache")}
