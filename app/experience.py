"""Six-question review schema, refresh rules and source-level timestamps."""
import json
from datetime import datetime, timezone, timedelta
from .privacy import redact

HOURS = ["0–5", "6–10", "11–15", "16–20", "21+", "Too early to tell"]
DRIVERS = ["Coding assignments", "Projects", "Problem sets / proofs", "Reading", "Exam preparation", "Group work", "Other", "Too early to tell"]
BALANCE = ["Comfortable", "Manageable with planning", "Difficult to balance", "Unsustainable so far", "Not assessed / only course"]
LABELS = ["Weekly hours outside scheduled classes", "Workload drivers", "Expected background", "Course combinations", "Learning experience", "Advice before registering"]
REFRESH_DAYS = 21


def now():
    return datetime.now(timezone.utc)


def enrollment(db, uid, code):
    row = db.execute("SELECT * FROM student_courses WHERE account_id=? AND course_code=?", (uid, code)).fetchone()
    if not row or not row["instructor"].strip():
        raise ValueError("Add this course and its instructor to your profile first")
    return dict(row)


def latest(db, uid, course):
    row = db.execute("SELECT * FROM experiences WHERE account_id=? AND course_code=? AND term=? AND lower(instructor)=lower(?) ORDER BY submitted_at DESC,id DESC LIMIT 1",
                     (uid, course["course_code"], course["term"], course["instructor"])).fetchone()
    return dict(row) if row else None


def access_status(db, uid):
    p = db.execute("SELECT * FROM profiles WHERE account_id=?", (uid,)).fetchone()
    if not p:
        return {"unlocked": False, "reason": "Complete your academic profile.", "courses": [], "incoming": False}
    courses = [dict(r) for r in db.execute("SELECT * FROM student_courses WHERE account_id=?", (uid,))]
    flag = db.execute("SELECT has_started FROM participation WHERE account_id=?", (uid,)).fetchone()
    started = bool(courses) or bool(flag and flag[0]) or p["start_date"] < now().strftime("%Y-%m")
    if not started:
        return {"unlocked": True, "incoming": True, "reason": "Incoming student access. Contribute once you begin taking courses.", "courses": []}
    required = [c for c in courses if c["status"] == "current"]
    if not required and courses:
        # Between semesters, refresh courses from the most recent completed term.
        def term_order(c):
            season, year = c["term"].split()
            return int(year), {"Spring": 0, "Summer": 1, "Fall": 2}[season]
        recent = max(map(term_order, courses))
        required = [c for c in courses if term_order(c) == recent]
    result = []
    for c in required:
        r = latest(db, uid, c)
        due = (datetime.fromisoformat(r["submitted_at"])+timedelta(days=REFRESH_DAYS)) if r else None
        result.append({"course_code": c["course_code"], "term": c["term"], "instructor": c["instructor"],
                       "review_id": r["id"] if r else None, "fresh": bool(due and due > now()),
                       "due_at": due.isoformat() if due else None})
    unlocked = bool(result) and all(c["fresh"] for c in result)
    return {"unlocked": unlocked, "incoming": False, "courses": result,
            "reason": "Course reviews are up to date. Ask freely." if unlocked else "Review each listed course to unlock AI questions. Your degree checklist remains available."}


def validate_answers(db, uid, course, raw, prior):
    stamp = now().isoformat()
    old = json.loads(prior["answers_json"]) if prior else None
    out = []
    for i, value in enumerate(raw):
        other_text = ""
        if value is None:
            if i not in (2, 4, 5) or not old:
                raise ValueError("No change is available only for written answers in a follow-up")
            out.append({**old[i], "confirmed_at": stamp, "state": "reconfirmed"})
            continue
        if i == 0 and value not in HOURS:
            raise ValueError("Select a weekly-hours range")
        if i == 1:
            # The list format remains valid for existing clients and saved reviews.
            if isinstance(value, dict):
                if set(value) != {"drivers", "other"} or not isinstance(value["other"], str):
                    raise ValueError("Choose workload drivers and describe Other")
                other_text = redact(value["other"].strip())
                value = value["drivers"]
                if isinstance(value, list) and "Other" in value and not 2 <= len(other_text) <= 300:
                    raise ValueError("Describe Other in 2–300 characters")
                if not isinstance(value, list) or "Other" not in value:
                    other_text = ""
            if not isinstance(value, list) or not value or len(value) > len(DRIVERS) or any(x not in DRIVERS for x in value):
                raise ValueError("Select workload drivers")
            value = list(dict.fromkeys(value))
            if "Too early to tell" in value and len(value) != 1:
                raise ValueError("Use Too early to tell on its own")
        if i in (2, 4, 5):
            if not isinstance(value, str) or not 10 <= len(value.strip()) <= 1800:
                raise ValueError("Written answers need 10–1800 characters, or use Too early to tell")
            value = redact(value.strip())
        if i == 3:
            if not isinstance(value, dict) or set(value) != {"courses", "balance"} or value["balance"] not in BALANCE:
                raise ValueError("Select the course combination and manageability")
            pairs = value["courses"]
            if not isinstance(pairs, list) or len(pairs) > 5 or any(not isinstance(x, str) for x in pairs):
                raise ValueError("Select courses from your same-term history")
            allowed = {r[0] for r in db.execute("SELECT course_code FROM student_courses WHERE account_id=? AND term=? AND course_code<>?", (uid, course["term"], course["course_code"]))}
            if not set(pairs).issubset(allowed) or (not pairs and value["balance"] != BALANCE[-1]):
                raise ValueError("Identify the actual same-term courses, or choose Not assessed / only course")
            value = {"courses": sorted(set(pairs)), "balance": value["balance"]}
        unchanged = old and value == old[i]["value"] and (i != 1 or other_text == old[i].get("other_text", ""))
        out.append({"value": value, "written_at": old[i]["written_at"] if unchanged else stamp,
                    "confirmed_at": stamp, "state": "reconfirmed" if unchanged else "new"})
        if i == 1 and other_text:
            out[-1]["other_text"] = other_text
    return out
