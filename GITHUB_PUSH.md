# Download → local review → GitHub

1. Extract the archive and run the prototype following README.md.
2. Review the screens and test using your own courses. Configure your API key
   in `.env` on your computer if you want real AI responses.
3. Push **source files only**. The included `.gitignore` excludes `.env`,
   `.venv/`, `data/`, SQLite files and Python caches.

## New GitHub repository

From the folder containing README.md, use GitHub CLI after signing in with
`gh auth login`:

```bash
git init -b main
git add .
git status --short
```

Review the staged file list. It should contain no API keys or student database.
Then:

```bash
git commit -m "Build Pass the Torch course planning prototype"
gh repo create pass-the-torch --private --source=. --remote=origin --push
```

Change the visibility if the competition requires a public repo. An alternative
is to create an empty repository on github.com and follow its displayed
commands for pushing an existing local repository.

## Existing repository

Copy these source files into your existing checkout, preserving its `.git/`
folder and any existing work. Review differences before staging. Run:

```bash
git status
git add .
git diff --cached --stat
git commit -m "Add Pass the Torch guided reviews and course exploration"
git push
```

If any secret or student database was already tracked, `.gitignore` will not
untrack it. Remove it from Git tracking and rotate any exposed key before making
that repository public.

## Working with your partner

Both partners should clone the same repository. SQLite is local: pushing code
does not synchronize reviews. For the demo use one running server, separate
browser profiles, and genuine, consented reviews from both students. A hosted
multi-user app requires a separate deployment with persistent storage and HTTPS.

## Submission reminders from your supplied guidelines

Submit on Devpost by **Sunday, November 15, 2026 at 11:00 AM Pacific**, with every
teammate added. Include the project description, prototype/repository/demo link,
video walkthrough of at most three minutes, a short PDF/Google Slides deck and
at least one project screenshot. This source download does not include a final
pitch deck or recording; capture them from the working app on your computer.
