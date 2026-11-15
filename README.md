# Pass the Torch

A Python-first USC student project: share course experience through guided
reviews, then explore degree requirements and ask AI about future courses.
Students contribute their own experience; AI answers other students' questions.
There is no discussion board or expectation that contributors monitor replies.

## Open the prototype on Windows

Extract the ZIP into a **new folder**. Open the inner `pass-the-torch` folder
containing this README and `requirements.txt`. Double-click **start-windows.bat**,
or open PowerShell in that folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Keep the terminal open and visit <http://127.0.0.1:8000>. A fresh database is
created automatically with no real accounts or reviews. A separate, clearly
labelled fictional feedback database is also prepared for the demo toggle.
Python 3.12+ is required. Internet access is needed for package installation.
If Windows cannot find `python`, install Python or try `py -3` for the first command.

On macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

All students using the **same running server** share review evidence. Separate
local copies do not synchronize through GitHub; GitHub stores source code.

## If you previously opened an earlier build on port 8000

Stop the old server with Ctrl+C. Start this version from the new folder, then
press Ctrl+Shift+R in Chrome. The page now uses content-versioned assets and
no-store headers to prevent mixing old JavaScript/CSS with new HTML. A backend
version check also explains when an older Python server is still running.

## Enable AI (Gemini or OpenAI)

For your Google AI Studio key, follow **[GEMINI_SETUP.md](GEMINI_SETUP.md)**.
Copy `.env.example` to `.env` on your computer, then fill:

```dotenv
PASS_THE_TORCH_AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart the server after editing `.env`. The How answers work section shows the provider configuration;
that configuration alone does not prove that an API call has succeeded. Availability and
quota depend on your Google project. If the selected model is unavailable, use
an exact accessible model ID from AI Studio. No automatic paid-model fallback
occurs, and switching providers does not rewrite or delete reviews.

The Google adapter calls the documented `generateContent` endpoint, supplies
system instructions separately from the de-identified evidence, ignores thought
parts and rejects incomplete responses. Keys travel in a server-side header,
never a browser field, query string or prompt. No new package is needed.

For OpenAI, set `PASS_THE_TORCH_AI_PROVIDER=openai`, `OPENAI_API_KEY` and
`OPENAI_MODEL`. The existing Responses API adapter remains available and uses
`store: false`. Only the selected provider receives requests.

Without a configured key/model the app clearly uses **evidence-only mode**.
Provider auth/model/quota/timeout errors explain the next check and fall back to
evidence without exposing upstream response bodies. Model citations must match
retrieved source IDs; that check does not prove semantic support for every claim.

Google's free tier may use submitted content to improve its products. Check your
project's current terms and use clearly labelled synthetic, non-sensitive
examples for a free-tier demonstration. This release includes a separately labelled simulated feedback database; real
reviews are not relabelled or mixed into that dataset. See DEMO_GUIDE.md.

## Screens and access rules

1. **Account:** centered registration/sign-in, custom torch mark and plain
   explanation. Name, USC email, password; no USC ID collection. Email and
   enrollment are self-reported, not institutionally verified.
2. **Academic profile:** choose among five MS CS tracks; enter start/graduation
   dates and completed/current courses. Instructor is required. Options come
   from consented reviews and your own history for that course and semester;
   missing names require manual entry. No official instructor roster is connected.
3. **Contribute:** one question at a time, six questions, course count and
   questions remaining. Questions 1, 2, 4 use choices; 3, 5, 6 are written.
   Drafts save privately while typing and before navigation. Final consent publishes.
4. **Explore:** a requirements checklist leads to relevant course cards and a
   comparison workspace. Completed and current credits remain separate.
5. **Course detail:** requirement fit, semester/instructor filters, and Workload,
   Preparation, Learning Experience and Course Combinations sections. Each has
   source cards, AI questions and a button to summarize available feedback.

Incoming students have **no total question cap** before taking courses. Once
courses are entered, reviews for every current course unlock asking. Each review
expires for access after **21 days**; a check-in refreshes it. Existing answers
and degree exploration remain viewable while asking is locked. Between semesters,
students can refresh the most recent completed semester instead. A remembered
participation flag prevents clearing history from restoring incoming status.
Incoming status is date/history-based and remains self-reported in this demo.

Asking is unlimited in total. A temporary 12-requests/minute/account safeguard
prevents bursts; it is not a three-question quota. No person is contacted when
someone asks AI a question.

## Evidence and pattern analysis

Initial reviews describe the course so far. Follow-ups revisit the same six
topics: reselect hours/drivers/balance; edit written answers or select No change.
Every answer retains its original `written_at` and latest `confirmed_at` dates.
Unchanged answers are labelled reconfirmed, rather than presented as new writing.

- Statistics use **one latest report per student per course under the selected
  filters**. More check-ins do not create more votes. Hour ranges remain ranges.
- Explicit combination feedback records the actual same-semester course set and
  manageability. A report about three courses does not establish a particular
  pair's workload. Per-course combination counts can overlap across courses;
  the comparison screen deduplicates contributors across course reports for the exact selected combination.
- AI can identify themes in the supplied written reports and explain numerical
  distributions. This is not a trained predictive workload or success model.
- One or two reviews support individual observations. Sparse/missing evidence,
  instructor differences and dates remain visible. Fictional fixtures are visibly labelled and stored separately. Automated tests use mocked model calls.
- Topic-demand counts record the sections/courses being asked about. Raw private
  questions are not published or retained as a community FAQ. Semantic question
  clustering and adaptive review prompts are future work.

## Program-rule scope

Five dated USC department summaries are included: General, Artificial
Intelligence, Data Science, Game Development, Scientists and Engineers.
The requirements engine uses deterministic Python rules, not model guesses.
**This is a planning reference, not a graduation audit.** See
[docs/sources.md](docs/sources.md) for URLs and cohort limitations. Full catalogue
verification, grades, prerequisites, offering schedules, special approvals,
waivers, thesis paths and variable/repeated course rules are incomplete.
Curated course options do not establish enrollment eligibility. Full automatic
semester-by-semester degree scheduling is not implemented.

## Privacy and local operation

One SQLite database has separate tables for reference rules, private accounts,
private course history/drafts and consented shared reviews. Passwords use salted
PBKDF2-HMAC-SHA256 (600,000 iterations). Session tokens are hashed in the database;
cookies are HttpOnly/SameSite=Lax, expire after 24 hours, and authenticated writes
require CSRF tokens. Use `PASS_THE_TORCH_SECURE_COOKIE=true` when serving via HTTPS.

The model receives program rules/progress, course-code history, retrieved
experience content, selected course metadata and the recent conversation. It
receives no account IDs, passwords, email fields or contributor-name fields.
Instructor names are relevant context. Emails and long numeric identifiers in
free text are redacted, but this is not a comprehensive PII filter. Shared
reports display contributor names to signed-in students. Conversations are kept
only in the open page's memory; only course/section topic demand is persisted.
Do not put private information into questions/reviews. For OpenAI, API `store: false` is not a promise of zero provider retention.
Gemini data handling follows your Google project tier and terms.

This is a single-process local pilot. Public deployment needs real affiliation
verification, email recovery, moderation/reporting, HTTPS configuration, database
migrations/backups and shared rate limiting. Do not use the reload server as a
public production server.

## Latest update

Build **2026.11.15.5** incorporates the complete screen walkthrough: navigation
follows Profile → Contribute → Explore; review choices use a compact desktop
layout; preview Edit links return directly to the preview; sharing requires
consent. Semester/year selections start blank. Existing saved month values are
preserved. Preparatory units are explained beside degree totals, and the
requirements checklist appears before course search.

General questions now search current/recent courses followed by remaining
requirements (at most five courses); the answer shows its retrieval scope.
Named review fields preserve expected prior background versus topics taught.
A narrow check rejects the specific background-to-teaching reversal observed
in the walkthrough; this is not comprehensive semantic verification. Program
rules, profile-derived progress and student reviews have separate citations.
Alternative exact-pair rating summaries come directly from stored feedback.
Citation groups expand supporting course reviews without showing dozens of
inline buttons. Original text and differing answer dates remain available.

New configuration variables use `PASS_THE_TORCH_`. Existing `COURSEWISE_`
variables remain accepted, including your current database path. When both are
set, the new name takes precedence. Without an explicit path, an existing
`data/coursewise.sqlite3` is reused; fresh installs create
`data/pass-the-torch.sqlite3`. Existing session cookies continue to work; new
sessions use the Pass the Torch name. Keep your existing `.env` during an update.


Read **[UPDATE_AND_TRY.md](UPDATE_AND_TRY.md)** for the simplest installation over
your current project while preserving `.env` and `data/`. Then use the on-page
**Try demo evidence** button. This release also adds history-aware course
options, search, an unlock continuation button, safe readable AI formatting,
source links, stricter citation validation and account-scoped request handling.

The explicit alias `CSCI455 → CSCI455X` applies to entry, retrieval and existing
records. Before modifying old alias records, the app creates a private SQLite
backup in `data/backups/`. Shared review IDs, original free text and answer dates
are retained. If both course-history spellings existed, their original records
remain in the backup; the canonical entry prefers a current enrollment. No
other course suffixes are removed or merged.

## Updating from the earlier Coursewise download

Use a new folder first. Your previous app/data is not modified by extracting
this ZIP. To bring accounts and profiles forward, stop both servers and copy
only your previous `data/coursewise.sqlite3` into the new project's `data/`
folder. New tables are added automatically. Existing instructors must be filled
in where missing. Legacy `reviews` rows are preserved on disk, but are not
silently converted into the six-question format or counted as fresh reviews:
the old hour question included class time, and the new one excludes it. Submit
fresh reviews to unlock the new flow. Never copy `.venv`, cached files or student
databases into GitHub.

## Validation

```bash
python -m unittest discover -s tests -v
node --test tests/ui.test.cjs
python -m compileall -q app
node --check app/static/app.js
```

Node is optional for running the app; it runs the UI controller checks. The suite
covers the two-student loop, all-course access, incoming access beyond three
questions, expiry/reconfirmation, privacy/ownership, drafts, exact pairings,
academic rules, model-adapter failures and real JavaScript form handlers. New regressions cover synthetic/live separation, migration preservation, malformed grouped citations, exact-combination deduplication, safe formatting, navigation drafts and stale-session responses.
A full browser rendering test and a live paid model call were not possible in
the build workspace. Test both on your laptop before recording the video.

## GitHub push

See [GITHUB_PUSH.md](GITHUB_PUSH.md) for a new or existing repository, and
[docs/demo.md](docs/demo.md) for the two-student demo and submission checklist.
This archive has not been pushed or deployed. `.gitignore` excludes secrets,
student databases, environments and caches.
