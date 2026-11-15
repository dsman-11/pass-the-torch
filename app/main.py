import json
import hashlib
import secrets
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import llm
from .config import Settings
from .db import connect, initialize, program_data
from .models import Registration, Credentials, ProfileInput, Question, ReviewInput, DraftInput, normalize_course
from .experience import access_status, enrollment, latest, validate_answers, now, HOURS, DRIVERS, BALANCE, LABELS
from .explore import exploration
from .progress import calculate_progress
from .retrieval import retrieve, combination_evidence, question_courses, redact
from .demo import seed_demo, NOTICE as DEMO_NOTICE
from .security import hash_password, verify_password, token_hash, RateLimiter
from .version import BUILD_ID

STATIC = Path(__file__).with_name("static")
SESSION_COOKIE = "pass_the_torch_session"


def session_token(request):
    return request.cookies.get(SESSION_COOKIE) or request.cookies.get("coursewise_session", "")


def create_app(settings=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        initialize(settings.db_path)
        if settings.demo_enabled:
            demo_path = settings.demo_db_path or str(Path(settings.db_path).parent/"demo-feedback.sqlite3")
            if Path(demo_path).resolve() == Path(settings.db_path).resolve():
                raise ValueError("Demo and real databases must use different paths")
            settings.demo_db_path = demo_path
            seed_demo(demo_path)
        yield

    app = FastAPI(title="Pass the Torch", lifespan=lifespan)
    app.state.settings = settings
    limiter = RateLimiter()

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Pydantic's default error includes rejected inputs, including passwords.
        errors = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.middleware("http")
    async def protect(request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse(status_code=403, content={"detail": "Use the same site for this request"})
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(status_code=403, content={"detail": "Cross-site requests are not accepted"})
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse(status_code=415, content={"detail": "Send JSON"})
            # Enforce a real body bound, even when Content-Length is absent.
            body = await request.body()
            if len(body) > 48_000:
                return JSONResponse(status_code=413, content={"detail": "Request is too large"})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path == "/" or request.url.path.startswith(("/api/", "/static/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def db_dep():
        with connect(settings.db_path) as db:
            yield db

    def account(request: Request, db=Depends(db_dep)):
        token = session_token(request)
        row = db.execute("SELECT a.id,a.name,a.email,s.csrf FROM sessions s JOIN accounts a ON a.id=s.account_id WHERE s.token_hash=? AND s.expires_at>?",
                         (token_hash(token), int(time.time()))).fetchone()
        if not row:
            raise HTTPException(401, "Please sign in")
        if request.method not in ("GET", "HEAD"):
            csrf = request.headers.get("x-csrf-token", "")
            if not secrets.compare_digest(csrf, row["csrf"]):
                raise HTTPException(403, "Session check failed. Refresh and try again")
        return dict(row)

    @contextmanager
    def evidence_db(request, real_db):
        mode = request.headers.get("x-evidence-mode", "real")
        if mode not in ("real", "demo"):
            raise HTTPException(422, "Evidence mode must be real or demo")
        if mode == "demo":
            if not settings.demo_enabled:
                raise HTTPException(400, "Demo evidence is disabled")
            with connect(settings.demo_db_path) as demo_db:
                yield demo_db, True
        else:
            yield real_db, False

    def course_code(value):
        try:
            return normalize_course(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    def public_account(row):
        return {k: row[k] for k in ("id", "name", "email")}

    def issue_session(db, response, user_id, old_token=""):
        if old_token:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(old_token),))
        db.execute("DELETE FROM sessions WHERE expires_at<?", (int(time.time()),))
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (token_hash(token), user_id, csrf, int(time.time())+86400))
        response.delete_cookie("coursewise_session", path="/")
        response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=settings.secure_cookie,
                            samesite="lax", max_age=86400, path="/")
        return csrf

    def throttle(request, prefix, maximum):
        key = (prefix, request.client.host if request.client else "local")
        if not limiter.allow(key, maximum):
            raise HTTPException(429, "Please wait a minute before trying again")

    @app.get("/api/catalog")
    def catalog(db=Depends(db_dep)):
        return {"app_version": BUILD_ID, "programs": [dict(r) for r in db.execute("SELECT id,name,source_url,snapshot_date FROM programs")],
                "courses": [dict(r) for r in db.execute("SELECT * FROM courses ORDER BY code")],
                "verification": "self-reported", "ai_configured": settings.ai_configured,
                "ai_provider": settings.provider, "ai_model": settings.model, "demo_available": settings.demo_enabled}

    @app.post("/api/register", status_code=201)
    def register(payload: Registration, response: Response, request: Request, db=Depends(db_dep)):
        throttle(request, "auth", 15)
        uid = str(uuid.uuid4())
        try:
            db.execute("INSERT INTO accounts VALUES (?,?,?,?,?)", (uid, payload.name, payload.email,
                       hash_password(payload.password), datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Could not create this account. Try signing in")
        csrf = issue_session(db, response, uid, session_token(request))
        return {"account": {"id": uid, "name": payload.name, "email": payload.email}, "csrf": csrf}

    @app.post("/api/login")
    def login(payload: Credentials, response: Response, request: Request, db=Depends(db_dep)):
        throttle(request, "auth", 15)
        row = db.execute("SELECT * FROM accounts WHERE email=?", (payload.email,)).fetchone()
        # A real password calculation also runs on the unknown-account path.
        encoded = row["password_hash"] if row else "pbkdf2_sha256$600000$dummy-timing-salt$"+"0"*64
        ok = verify_password(payload.password, encoded)
        if not row or not ok:
            raise HTTPException(401, "Email or password is incorrect")
        csrf = issue_session(db, response, row["id"], session_token(request))
        return {"account": public_account(row), "csrf": csrf}

    @app.get("/api/me")
    def me(user=Depends(account), db=Depends(db_dep)):
        profile = db.execute("SELECT * FROM profiles WHERE account_id=?", (user["id"],)).fetchone()
        courses = db.execute("SELECT course_code,status,term,instructor FROM student_courses WHERE account_id=? ORDER BY status,course_code", (user["id"],)).fetchall()
        return {"account": public_account(user), "csrf": user["csrf"],
                "profile": {k: profile[k] for k in ("program_id", "start_date", "graduation_date")} if profile else None,
                "access": access_status(db, user["id"]),
                "courses": [dict(r) for r in courses]}

    @app.post("/api/logout")
    def logout(request: Request, response: Response, user=Depends(account), db=Depends(db_dep)):
        db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(session_token(request)),))
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.delete_cookie("coursewise_session", path="/")
        return {"ok": True}

    @app.put("/api/profile")
    def save_profile(payload: ProfileInput, user=Depends(account), db=Depends(db_dep)):
        if not program_data(db, payload.program_id):
            raise HTTPException(422, "Select a supported program")
        prior = db.execute("SELECT start_date FROM profiles WHERE account_id=?", (user["id"],)).fetchone()
        started = bool(payload.courses) or payload.start_date < now().strftime("%Y-%m") or bool(prior and prior[0] < now().strftime("%Y-%m"))
        db.execute("INSERT INTO participation VALUES (?,?) ON CONFLICT(account_id) DO UPDATE SET has_started=max(has_started,excluded.has_started)", (user["id"], int(started)))
        db.execute("INSERT INTO profiles VALUES (?,?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET program_id=excluded.program_id,start_date=excluded.start_date,graduation_date=excluded.graduation_date,background=excluded.background,goals=excluded.goals,weekly_budget=excluded.weekly_budget",
                   (user["id"], payload.program_id, payload.start_date, payload.graduation_date, "", "", None))
        db.execute("DELETE FROM student_courses WHERE account_id=?", (user["id"],))
        db.executemany("INSERT INTO student_courses(account_id,course_code,status,term,instructor) VALUES (?,?,?,?,?)",
                       [(user["id"], c.code, c.status, c.term, c.instructor.strip()) for c in payload.courses])
        return {"ok": True}

    def progress_for(db, uid):
        p = db.execute("SELECT * FROM profiles WHERE account_id=?", (uid,)).fetchone()
        if not p:
            raise HTTPException(409, "Save your program and course history first")
        history = [dict(r) for r in db.execute("SELECT * FROM student_courses WHERE account_id=?", (uid,))]
        catalog = {r["code"]: dict(r) for r in db.execute("SELECT * FROM courses")}
        return calculate_progress(program_data(db, p["program_id"]), history, catalog, p["start_date"])

    @app.get("/api/progress")
    def progress(user=Depends(account), db=Depends(db_dep)):
        return progress_for(db, user["id"])

    @app.get("/api/explore")
    def explore(request: Request, user=Depends(account), db=Depends(db_dep)):
        p = db.execute("SELECT * FROM profiles WHERE account_id=?", (user["id"],)).fetchone()
        if not p:
            raise HTTPException(409, "Save your academic profile first")
        history = [dict(r) for r in db.execute("SELECT * FROM student_courses WHERE account_id=?", (user["id"],))]
        result = exploration(db, program_data(db, p["program_id"]), history, p["start_date"])
        with evidence_db(request, db) as (source_db, simulated):
            counts = {r[0]: r[1] for r in source_db.execute("SELECT course_code,count(DISTINCT account_id) FROM experiences GROUP BY course_code")}
        for c in result["courses"]:
            c["contributor_count"] = counts.get(c["code"], 0)
        result["dataset_mode"] = "demo" if simulated else "real"
        return result

    @app.get("/api/instructors")
    def instructors(course: str, term: str, user=Depends(account), db=Depends(db_dep)):
        course = course_code(course)
        # Only consented shared reports and this account's own history supply options.
        rows = db.execute("SELECT instructor FROM experiences WHERE course_code=? AND term=? UNION SELECT instructor FROM student_courses WHERE account_id=? AND course_code=? AND term=?", (course, term, user["id"], course, term)).fetchall()
        return {"instructors": sorted({r[0] for r in rows if r[0].strip()}), "provenance": "Student-reported names; not an official section roster"}

    @app.get("/api/review-schema")
    def review_schema(user=Depends(account)):
        return {"hours": HOURS, "drivers": DRIVERS, "balance": BALANCE, "labels": LABELS, "refresh_days": 21}

    def own_course(db, user, code):
        try:
            return enrollment(db, user["id"], course_code(code))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/api/reviews/latest/{code}")
    def last_review(code: str, user=Depends(account), db=Depends(db_dep)):
        c = own_course(db, user, code)
        code = c["course_code"]
        r = latest(db, user["id"], c)
        draft = db.execute("SELECT draft_json FROM review_drafts WHERE account_id=? AND course_code=? AND term=? AND instructor=?", (user["id"], code, c["term"], c["instructor"])).fetchone()
        return {"review": {"id": r["id"], "answers": json.loads(r["answers_json"]), "submitted_at": r["submitted_at"]} if r else None,
                "draft": json.loads(draft[0]) if draft else None}

    @app.put("/api/reviews/draft")
    def save_draft(payload: DraftInput, user=Depends(account), db=Depends(db_dep)):
        c = own_course(db, user, payload.course_code)
        db.execute("INSERT INTO review_drafts VALUES (?,?,?,?,?) ON CONFLICT(account_id,course_code,term,instructor) DO UPDATE SET draft_json=excluded.draft_json", (user["id"], c["course_code"], c["term"], c["instructor"], payload.model_dump_json()))
        return {"ok": True}

    @app.post("/api/reviews", status_code=201)
    def submit_review(payload: ReviewInput, user=Depends(account), db=Depends(db_dep)):
        if not payload.consent:
            raise HTTPException(422, "Confirm sharing your review as AI evidence and with signed-in students")
        c = own_course(db, user, payload.course_code)
        prior = latest(db, user["id"], c)
        if (prior["id"] if prior else None) != payload.previous_id:
            raise HTTPException(409, "Your review changed in another tab. Reopen it to continue")
        try:
            answers = validate_answers(db, user["id"], c, payload.answers, prior)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc))
        cursor = db.execute("INSERT INTO experiences(account_id,course_code,term,instructor,enrollment_status,answers_json,submitted_at,previous_id) VALUES (?,?,?,?,?,?,?,?)",
                            (user["id"], c["course_code"], c["term"], c["instructor"], c["status"], json.dumps(answers), now().isoformat(), payload.previous_id))
        db.execute("DELETE FROM review_drafts WHERE account_id=? AND course_code=? AND term=? AND instructor=?", (user["id"], c["course_code"], c["term"], c["instructor"]))
        return {"id": cursor.lastrowid, "access": access_status(db, user["id"])}

    @app.get("/api/reviews/mine")
    def mine(user=Depends(account), db=Depends(db_dep)):
        rows = db.execute("SELECT id,course_code,term,instructor,submitted_at,previous_id FROM experiences WHERE account_id=? ORDER BY submitted_at DESC,id DESC", (user["id"],)).fetchall()
        return {"reviews": [dict(r) for r in rows]}

    @app.delete("/api/reviews/{code}")
    def delete_reviews(code: str, user=Depends(account), db=Depends(db_dep)):
        code = course_code(code)
        # Erase the full chain so an older report cannot silently reappear.
        db.execute("DELETE FROM experiences WHERE account_id=? AND course_code=?", (user["id"], code))
        db.execute("DELETE FROM review_drafts WHERE account_id=? AND course_code=?", (user["id"], code))
        db.execute("DELETE FROM reviews WHERE account_id=? AND course_code=?", (user["id"], code))
        return {"ok": True, "access": access_status(db, user["id"])}

    @app.get("/api/course/{code}")
    def course_evidence(code: str, request: Request, term: str = "", instructor: str = "", user=Depends(account), db=Depends(db_dep)):
        with evidence_db(request, db) as (source_db, simulated):
            bundle = retrieve(source_db, [course_code(code)], term, instructor, simulated)[0]
        bundle["dataset_mode"] = "demo" if simulated else "real"
        return bundle

    @app.get("/api/comparison")
    def comparison(codes: str, request: Request, term: str = "", user=Depends(account), db=Depends(db_dep)):
        selected = list(dict.fromkeys(course_code(c.strip()) for c in codes.split(",") if c.strip()))
        if not 2 <= len(selected) <= 5:
            raise HTTPException(422, "Compare two to five courses")
        with evidence_db(request, db) as (source_db, simulated):
            result = combination_evidence(source_db, selected, term, simulated=simulated)
        return result

    @app.post("/api/ask")
    async def ask(payload: Question, request: Request, user=Depends(account), db=Depends(db_dep)):
        access = access_status(db, user["id"])
        if not access["unlocked"]:
            raise HTTPException(403, access["reason"])
        # Temporary anti-burst protection, not a lifetime or contribution quota.
        if not limiter.allow(("ask", user["id"]), 12):
            raise HTTPException(429, "Please wait a minute before asking again")
        progress = progress_for(db, user["id"])
        history = [dict(r) for r in db.execute("SELECT course_code,status,term FROM student_courses WHERE account_id=? ORDER BY status,term DESC,course_code", (user["id"],))]
        mentioned = question_courses(payload.question, [])
        codes = mentioned if len(mentioned) >= 2 else question_courses(payload.question, payload.courses)
        scope = "Courses named in your question" if mentioned else "Courses selected on this page"
        if not codes and not payload.summarize:
            for h in reversed(payload.history):
                if h["role"] == "user":
                    codes = question_courses(h["content"], [])
                    if codes:
                        scope = "Courses from your previous question"
                        break
        with evidence_db(request, db) as (source_db, simulated):
            if not codes:
                # General questions need a grounded, visible scope too. Start with
                # the student's current/recent history, then remaining requirements.
                candidates = [c["course_code"] for c in sorted(history, key=lambda c: c["status"] != "current")]
                candidates += [code for r in progress["requirements"] if r["status"] == "remaining" for code in r["courses"]]
                codes = list(dict.fromkeys(candidates))[:5]
                scope = "Your current/recent courses, then remaining requirements (up to five courses)"
            bundles = retrieve(source_db, codes, payload.term.strip(), payload.instructor.strip(), simulated)
            combo = combination_evidence(source_db, codes, payload.term.strip(), payload.instructor.strip(), simulated)
            subsets = {tuple(c["courses"]) for b in bundles for c in b["combinations"]
                       if set(c["courses"]) < set(codes)}
            alternatives = [combination_evidence(source_db, group, payload.term.strip(), payload.instructor.strip(), simulated)
                            for group in sorted(subsets)]
            combination_sources = {r["citation"]:r for group in [combo]+alternatives for r in group["reviews"]}
            all_sources = {r["id"]:r for b in bundles for r in b["reviews"]}
            all_sources.update({r["id"]:r for r in combination_sources.values()})
            ids = list(all_sources)
            people = source_db.execute("SELECT count(DISTINCT account_id) FROM experiences WHERE id IN ("+",".join("?" for _ in ids)+")", ids).fetchone()[0] if ids else 0
        personal = {"course_history": history, "section": payload.section,
                    "citation": "P:profile", "retrieval_scope": {"courses": codes, "note": scope},
                    "conversation": [{"role": h["role"], "content": redact(h["content"])} for h in payload.history]}
        personal["selected_course_metadata"] = [dict(r) for code in codes for r in db.execute("SELECT * FROM courses WHERE code=?", (code,))]
        personal["dataset_mode"] = "simulated" if simulated else "real"
        personal["combination_evidence"] = {**combo, "reviews": [{k:v for k,v in r.items() if k!="contributor_name"} for r in combo["reviews"]]}
        personal["related_combinations"] = [{**group, "reviews": [{k:v for k,v in r.items() if k!="contributor_name"} for r in group["reviews"]]} for group in alternatives]
        personal["metadata_note"] = "Curated course units and titles; verify variable units and enrollment prerequisites against the applicable catalogue."
        result = await llm.answer(settings, payload.question, bundles, progress, personal)
        if simulated:
            result["notice"] = DEMO_NOTICE+" "+result["notice"]
            result["answer"] = "Simulated demo evidence — fictional student experiences.\n\n"+result["answer"]
        else:
            db.execute("INSERT INTO information_requests(account_id,course_codes,section,created_at) VALUES (?,?,?,?)", (user["id"], json.dumps(codes), payload.section, now().isoformat()))
        return {**result, "student_sources": bundles, "combination_sources": list(combination_sources.values()), "dataset_mode": "demo" if simulated else "real",
                "retrieval_scope": {"courses": codes, "note": scope, "term": payload.term, "instructor": payload.instructor},
                "evidence_summary": {"review_count": len(all_sources), "unique_contributors": people},
                "profile_source": {"citation": "P:profile", "courses": history,
                                   "completed_units": progress["completed"]["degree_units"], "in_progress_units": progress["projected"]["degree_units"]-progress["completed"]["degree_units"]},
                "combination_groups": [{k:v for k,v in group.items() if k!="reviews"} for group in ([combo] if combo["unique_contributors"] else [])+alternatives],
                "official_sources": [{"citation": f"S:{progress['program_id']}", "url": progress["source_url"],
                                      "title": progress["program"], "snapshot_date": progress["snapshot_date"]}]}

    @app.get("/")
    def home():
        # Every asset URL changes with its bytes, including when an older app
        # was opened on the same localhost port. File timestamps are not enough
        # to distinguish files extracted from different ZIP downloads.
        html = (STATIC/"index.html").read_text(encoding="utf-8")
        for name in ("app.js", "styles.css", "torch.svg"):
            digest = hashlib.sha256((STATIC/name).read_bytes()).hexdigest()[:12]
            html = html.replace(f"/static/{name}", f"/static/{name}?v={digest}")
        return HTMLResponse(html)

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
