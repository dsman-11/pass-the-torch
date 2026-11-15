# Install the walkthrough update

Build **2026.11.15.5**. No new packages or API key are required.

Windows hotfix: explicitly closes the course-alias backup connection and compares
database paths portably in the tests. If you already installed this build,
replace only `app/migrations.py`, `tests/test_batch.py`, and (for GitHub checks)
`.github/workflows/checks.yml` from this archive. Keep `.env` and `data` unchanged.
The UI/build ID is unchanged because this patch does not change browser assets.

1. Stop your running server with **Ctrl+C**.
2. Extract the ZIP and open its inner **pass-the-torch** folder.
3. Copy the new **app** folder into your existing working project. Choose
   **Replace files**. You may also replace the documentation and tests.
4. Keep your existing **.env**, **data** and **.venv**. Your walkthrough accounts
   and reviews stay in the database selected by your existing `.env`, including
   `data/walkthrough-01.sqlite3` if that is what you configured.
5. Start **start-windows.bat** and press **Ctrl+Shift+R** in Chrome.

Do not replace your `.env` with `.env.example`. Old `COURSEWISE_` settings still
work. New setups use `PASS_THE_TORCH_` names; if both exist, the new name wins.
Old session cookies and databases remain readable. No reset is necessary.
If running from a new extracted folder, copy your existing `.env` and entire
`data` folder there with both servers stopped. Do not copy private files to GitHub.

## Quick check before recording

1. Sign in to your existing walkthrough account. Confirm the two course reviews
   remain available and asking is unlocked.
2. Inspect **Profile → Contribute → Explore courses**. Review pages hide the
   demo switch. Questions use compact desktop choices; the preview has Edit
   links and sharing requires consent.
3. On Explore, check preparatory units beside degree totals, then open a remaining
   requirement. The checklist now comes before search.
4. In real mode, click **Summarize available feedback**. It should retrieve your
   current reviews and show which courses were searched.
5. Ask: **Based on the available feedback, how manageable is CSCI455x with
   CSCI570, and what should I prepare for?** Expect two reviews from one
   contributor. Background advice should preserve what was expected beforehand.
6. Click **Try demo evidence**, then ask: **How does 402 + 561 compare with
   402 + 567 in these demo reviews?** Separate rating cards should show four
   simulated contributors for each exact pair. Grouped citation buttons open
   the supporting course review groups; individual references open a review.
7. Ask about **CSCI566**. It has no fictional reviews. Missing experience should
   remain explicit.

These checks confirm your browser layout and live Gemini connection; the build
workspace uses backend and JavaScript controller tests with mocked provider
responses. LLM wording varies. Citations and the narrow interpretation guard do
not establish that every generated claim is correct.

## What is included

- Compact account/profile/review screens, intentional semester selections,
  direct preview editing, conditional Other text, exclusive Too early answers.
- One clear completion message and expandable shared-review management.
- Requirements first, clearer credit totals, curated titles and readable fit text.
- Scoped general-summary retrieval and explicit evidence counts.
- Named review semantics, profile citations and a guard for the observed category error.
- Separate exact-pair counts, grouped citations, fixed list formatting and compact source dates.
- Updated branding with backward-compatible configuration and sessions.

The fictional dataset remains separate from your real contributions. This
prototype remains a planning reference and descriptive evidence tool.
