import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(path):
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(path):
    from .data import COURSES, PROGRAMS
    from .migrations import migrate_aliases
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        migrate_aliases(db, path)
        db.executemany("INSERT OR IGNORE INTO courses(code,units,title) VALUES (?,?,?)",
                       [(code, v[0], v[1]) for code, v in COURSES.items()])
        # Fill newly curated titles without replacing local/custom titles.
        db.executemany("UPDATE courses SET title=? WHERE code=? AND title=code",
                       [(v[1], code) for code, v in COURSES.items() if v[1] != code])
        for p in PROGRAMS:
            db.execute("INSERT OR IGNORE INTO programs VALUES (?,?,?,?,?)",
                       (p["id"], p["name"], p["url"], "2026-11-14", json.dumps(p["rules"])))
    Path(path).chmod(0o600)


def program_data(db, program_id):
    row = db.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    return {**dict(row), "rules": json.loads(row["rules_json"])} if row else None
