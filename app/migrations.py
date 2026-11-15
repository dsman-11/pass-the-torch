import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from .aliases import canonical


def migrate_aliases(db, path):
    """Back up before normalizing existing codes; retain review IDs and dates."""
    db.execute("CREATE TABLE IF NOT EXISTS migrations (id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    if db.execute("SELECT 1 FROM migrations WHERE id='455-alias-v1'").fetchone():
        return
    affected = any(db.execute(f"SELECT 1 FROM {table} WHERE course_code='CSCI455' LIMIT 1").fetchone()
                   for table in ("student_courses", "experiences", "reviews", "review_drafts"))
    affected |= bool(db.execute("SELECT 1 FROM experiences WHERE answers_json LIKE '%\"CSCI455\"%' LIMIT 1").fetchone())
    affected |= bool(db.execute("SELECT 1 FROM review_drafts WHERE draft_json LIKE '%\"CSCI455\"%' LIMIT 1").fetchone())
    db.commit()
    if affected:
        folder = Path(path).parent / "backups"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        backup = folder / (Path(path).stem+"-before-course-alias-"+stamp+".sqlite3")
        # sqlite3.Connection's own context manager commits/rolls back, but does
        # not close the handle. Windows prevents cleanup of an open backup file.
        with closing(sqlite3.connect(backup)) as dest:
            db.backup(dest)
        backup.chmod(0o600)
        for row in db.execute("SELECT * FROM student_courses WHERE course_code='CSCI455'").fetchall():
            other = db.execute("SELECT * FROM student_courses WHERE account_id=? AND course_code='CSCI455X'", (row["account_id"],)).fetchone()
            if other:
                if row["status"] == "current" and other["status"] != "current":
                    db.execute("UPDATE student_courses SET status=?,term=?,instructor=? WHERE id=?", (row["status"], row["term"], row["instructor"], other["id"]))
                db.execute("DELETE FROM student_courses WHERE id=?", (row["id"],))
            else:
                db.execute("UPDATE student_courses SET course_code='CSCI455X' WHERE id=?", (row["id"],))
        db.execute("UPDATE experiences SET course_code='CSCI455X' WHERE course_code='CSCI455'")
        # Legacy collisions stay in the backup and in their original table;
        # they are never discarded to satisfy a new unique key.
        db.execute("UPDATE OR IGNORE reviews SET course_code='CSCI455X' WHERE course_code='CSCI455'")
        for row in db.execute("SELECT rowid,* FROM review_drafts").fetchall():
            data = json.loads(row["draft_json"])
            data["course_code"] = canonical(data.get("course_code", row["course_code"]))
            for answer in data.get("answers", {}).values():
                if isinstance(answer, dict) and isinstance(answer.get("courses"), list):
                    answer["courses"] = list(dict.fromkeys(canonical(c) for c in answer["courses"]))
            db.execute("UPDATE review_drafts SET draft_json=? WHERE rowid=?", (json.dumps(data), row["rowid"]))
            db.execute("UPDATE OR IGNORE review_drafts SET course_code=? WHERE rowid=?", (canonical(row["course_code"]), row["rowid"]))
        for row in db.execute("SELECT id,course_codes FROM information_requests").fetchall():
            codes = list(dict.fromkeys(canonical(c) for c in json.loads(row["course_codes"])))
            db.execute("UPDATE information_requests SET course_codes=? WHERE id=?", (json.dumps(codes), row["id"]))
        for row in db.execute("SELECT id,paired_courses FROM reviews").fetchall():
            codes = list(dict.fromkeys(canonical(c) for c in json.loads(row["paired_courses"] or "[]")))
            db.execute("UPDATE reviews SET paired_courses=? WHERE id=?", (json.dumps(codes), row["id"]))
        for row in db.execute("SELECT id,answers_json FROM experiences").fetchall():
            answers = json.loads(row["answers_json"])
            pair = answers[3]["value"]
            pair["courses"] = list(dict.fromkeys(canonical(c) for c in pair["courses"]))
            db.execute("UPDATE experiences SET answers_json=? WHERE id=?", (json.dumps(answers), row["id"]))
    db.execute("INSERT INTO migrations VALUES ('455-alias-v1',?)", (datetime.now(timezone.utc).isoformat(),))
