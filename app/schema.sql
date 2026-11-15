PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS programs (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, source_url TEXT NOT NULL,
 snapshot_date TEXT NOT NULL, rules_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
 code TEXT PRIMARY KEY, units INTEGER NOT NULL, title TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS accounts (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
 password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 csrf TEXT NOT NULL, expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS profiles (
 account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
 program_id TEXT NOT NULL REFERENCES programs(id), start_date TEXT NOT NULL,
 graduation_date TEXT NOT NULL, background TEXT NOT NULL DEFAULT '',
 goals TEXT NOT NULL DEFAULT '', weekly_budget INTEGER
);
CREATE TABLE IF NOT EXISTS student_courses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 course_code TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('completed','current')),
 term TEXT NOT NULL, instructor TEXT NOT NULL DEFAULT '',
 UNIQUE(account_id, course_code)
);
CREATE TABLE IF NOT EXISTS reviews (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 course_code TEXT NOT NULL, term TEXT NOT NULL, instructor TEXT NOT NULL,
 enrollment_status TEXT NOT NULL, week_start TEXT NOT NULL, hours INTEGER NOT NULL,
 background TEXT NOT NULL, preparation TEXT NOT NULL, workload TEXT NOT NULL,
 advice TEXT NOT NULL, paired_courses TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, UNIQUE(account_id,course_code,term,week_start)
);
CREATE INDEX IF NOT EXISTS review_course ON reviews(course_code,term,week_start);
CREATE TABLE IF NOT EXISTS participation (
 account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
 has_started INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS experiences (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 course_code TEXT NOT NULL, term TEXT NOT NULL, instructor TEXT NOT NULL,
 enrollment_status TEXT NOT NULL, answers_json TEXT NOT NULL,
 submitted_at TEXT NOT NULL, previous_id INTEGER REFERENCES experiences(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS experience_lookup ON experiences(course_code,term,instructor,submitted_at);
CREATE TABLE IF NOT EXISTS review_drafts (
 account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 course_code TEXT NOT NULL, term TEXT NOT NULL, instructor TEXT NOT NULL,
 draft_json TEXT NOT NULL, PRIMARY KEY(account_id,course_code,term,instructor)
);
CREATE TABLE IF NOT EXISTS information_requests (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 course_codes TEXT NOT NULL, section TEXT NOT NULL, created_at TEXT NOT NULL
);
