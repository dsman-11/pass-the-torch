"""Fictional fixtures, stored apart from real accounts, profiles and reviews."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .db import initialize, connect

NOTICE = "Simulated demo evidence. Student identities, instructors and experiences are fictional; this is not evidence of actual USC course difficulty."


def seed_demo(path):
    initialize(path)
    with connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS demo_meta (id TEXT PRIMARY KEY)")
        if db.execute("SELECT 1 FROM demo_meta WHERE id='fictional-v1'").fetchone():
            return
        # Refuse to seed any populated database not explicitly marked as ours.
        if db.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
            raise ValueError("Demo database contains accounts without a demo marker; choose a separate empty path")
        stamp = datetime.now(timezone.utc)
        instructors = {"CSCI402": "Demo Systems Instructor", "CSCI561": "Demo AI Instructor", "CSCI567": "Demo ML Instructor"}
        scenarios = [
            ("A", ["CSCI402","CSCI561"], ["16–20","6–10"], "Manageable with planning", "Prior C++ and algorithms experience", "Starting systems projects early kept the overlap manageable."),
            ("B", ["CSCI402","CSCI561"], ["21+","11–15"], "Difficult to balance", "First systems course; Python background", "Learning C++ while two assignments overlapped made this week difficult."),
            ("C", ["CSCI402","CSCI561"], ["11–15","6–10"], "Comfortable", "CS undergraduate background", "I was already familiar with the programming tools and scheduled work early."),
            ("D", ["CSCI402","CSCI561"], ["16–20","11–15"], "Difficult to balance", "Comfortable with C++; limited time outside classes", "The project deadline and an exam fell in the same week."),
            ("E", ["CSCI402","CSCI567"], ["16–20","16–20"], "Difficult to balance", "Python experience; reviewing linear algebra", "I needed time for math review as well as systems debugging."),
            ("F", ["CSCI402","CSCI567"], ["11–15","11–15"], "Manageable with planning", "Prior systems and probability coursework", "The pair worked for me with a consistent weekly schedule."),
            ("G", ["CSCI402","CSCI567"], ["21+","16–20"], "Unsustainable so far", "Non-CS background; learning C++ and probability", "Debugging and reviewing probability left too little time in this period."),
            ("H", ["CSCI402","CSCI567"], ["16–20","11–15"], "Comfortable", "Professional C++ and prior ML experience", "My background reduced preparation time, so my experience may not transfer to a beginner."),
            ("I", ["CSCI561"], ["11–15"], "Not assessed / only course", "Programming background; new to search algorithms", "Working through small examples helped more than rereading notes."),
            ("J", ["CSCI567"], ["16–20"], "Not assessed / only course", "Returning to probability after several years", "Refreshing probability before assignments helped me understand the work."),
        ]
        first = {}
        for name, codes, hours, balance, prep, advice in scenarios:
            uid = "fictional-"+name
            db.execute("INSERT INTO accounts VALUES (?,?,?,?,?)", (uid, "Demo Student "+name, name.lower()+"@example.invalid", "!DEMO-NO-LOGIN", stamp.isoformat()))
            for code, hour in zip(codes, hours):
                old = (stamp-timedelta(days=20)).isoformat()
                values = [hour, ["Projects","Coding assignments"] if code=="CSCI402" else ["Problem sets / proofs","Exam preparation"],
                          prep+". This is a fictional preparation report.",
                          {"courses": [c for c in codes if c!=code], "balance": balance},
                          "In this fictional scenario, worked examples and office hours helped me understand assignments.", advice]
                answers = [{"value": value,"written_at":old,"confirmed_at":old,"state":"new"} for value in values]
                cur = db.execute("INSERT INTO experiences(account_id,course_code,term,instructor,enrollment_status,answers_json,submitted_at,previous_id) VALUES (?,?,?,?,?,?,?,NULL)",
                                 (uid,code,"Fall 2026",instructors[code],"current",json.dumps(answers),old))
                first[(name,code)] = (cur.lastrowid, answers)
        for name, code, hour in [("A","CSCI402","21+"),("I","CSCI561","16–20")]:
            previous, answers = first[(name,code)]
            latest = (stamp-timedelta(days=1)).isoformat()
            updated = [{**a,"confirmed_at":latest,"state":"reconfirmed"} for a in answers]
            updated[0] = {"value":hour,"written_at":latest,"confirmed_at":latest,"state":"new"}
            db.execute("INSERT INTO experiences(account_id,course_code,term,instructor,enrollment_status,answers_json,submitted_at,previous_id) VALUES (?,?,?,?,?,?,?,?)",
                       ("fictional-"+name,code,"Fall 2026",instructors[code],"current",json.dumps(updated),latest,previous))
        db.execute("INSERT INTO demo_meta VALUES ('fictional-v1')")
