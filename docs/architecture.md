# Pass the Torch architecture

FastAPI serves a small static HTML/CSS/JavaScript interface and a Python API.
SQLite keeps reference rules, account data, course history, private drafts and
consented experiences in separate tables. No Node build step is required.

## Core modules

- `data.py`, `progress.py`, `explore.py`: dated program snapshots, deterministic
  credit allocation, requirement-to-course links. Nothing sets `audit_complete`
  to true. Options still require catalogue/prerequisite/approval checks.
- `experience.py`: six-answer validation, answer-level provenance, 21-day access
  freshness and incoming/continuing participation state.
- `retrieval.py`: exact course/term/instructor filters, latest report per person,
  transparent distributions and exact combination observations. Up to 12 source
  contributors per course are passed to AI; statistics cover the entire filtered
  latest-per-person set. Older versions are retained for provenance.
- `llm.py`: optional Gemini generateContent or OpenAI Responses integration. Both review content and previous
  conversation are untrusted data. No tools/actions are provided. Source IDs
  must exist in retrieved context; unusable references trigger evidence fallback.
  This does not establish semantic correctness of each generated claim.
- `main.py`, `security.py`: server-side sessions, CSRF, ownership checks, API
  lifecycle and local burst protection. All SQL uses bound values.

## Review lifecycle

Initial course review covers experience so far. A follow-up revisits the same
questions. Submitted selections are re-evaluated; free responses can be edited
or explicitly reconfirmed. Reconfirmation preserves the original writing date
and records the new confirmation date. A review chain is not a set of independent
people. Deleting your course reviews erases the entire chain, preventing an old
version from reappearing in retrieval after a deletion.

Drafts save privately while typing and before navigation, and remain private until explicit final sharing consent. A stale browser tab
cannot overwrite the latest review: `previous_id` must match the latest owned
report for that exact course, term and instructor. Different instructors/terms
need a new initial review. Profile edits never rewrite shared evidence metadata.

## Access and conversations

The requirements checklist and evidence remain viewable. Asking requires a
profile and fresh reviews for every current course; the most recent completed
term is used between semesters. Students with no history whose start month is
not in the past have incoming access. Participation is remembered, so deleting
history cannot grant incoming access again. Affiliation/enrollment are still
self-reported; this is not an authenticity guarantee.

There is no total question quota or human Q&A. Recent conversation is sent as
untrusted context; prompts and answers are not added to the review corpus.
Course/section topic-demand counts are stored without raw question text.
No semantic clustering or adaptive prompt generation is claimed in this version.

## Statistical limits

Workload ranges are not converted to invented exact means. Combination reports
require an explicitly selected set from a contributor's same-term history.
A three-course report is not a two-course report. The combination endpoint deduplicates qualifying exact-set reports by account
across the course panels. Each contributor supplies one most recent qualifying
report, with source context retained.
Different instructor/semester contexts remain filterable and visible. The app
has descriptive statistics and on-demand AI themes, not a trained success model.

## Future adoption work

Catalogue versioning, actual USC verification, moderation/reporting, deployment,
recovery emails, shared rate limiting, formal model evaluations and operational
ownership need institution-specific work before a public launch. Program
summaries are not complete graduation audits. See `sources.md` for provenance.


## New separation and provenance rules

`demo.py` prepares a separate feedback-only SQLite file with fictional identities,
instructors and scenarios. The real account/session/profile/review tables are
never seeded with fake people. `X-Evidence-Mode` selects the source database for
read operations. Real contribution/access rules are unaffected. Simulated
requests are tagged in the prompt, the response and each source card; demo
question demand is not written into the real topic-demand table.

`migrations.py` backs up an old database before the explicit 455 alias migration.
IDs, text and answer timestamps stay intact. Pair/draft course references are
normalised too. The applied migration is recorded so it is not repeated.

The citation parser validates entire source blocks, not just matching fragments.
It rejects course-code review IDs, unknown IDs, malformed/dangling references
and unbracketed R:/S: tokens. Grouped valid references are canonicalised. This
checks provenance identifiers, not every claim's semantic entailment. The UI
escapes text before applying a small formatting subset and creates source
buttons only for identifiers present in the response's available source cards.

The browser increments a session/evidence epoch on account or corpus changes.
Late HTTP results from a previous epoch are discarded before touching state.
Draft saves are serialised; navigating away flushes the current answer. A dirty
review warns before closing the tab. No raw AI HTML is executed.
