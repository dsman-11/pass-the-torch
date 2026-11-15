# Connect your Google AI Studio key

The earlier download only supported OpenAI. This release adds Gemini without
changing the review schema or requiring new Python packages.

## Update while keeping your existing reviews

1. Stop the running Python server with **Ctrl+C**.
2. Extract the updated ZIP into a separate folder.
3. Copy its **app** folder into your currently working `pass-the-torch` project.
   Choose **Replace files**. Keep your existing **data** folder and `.env` file.
   Your accounts and submitted reviews are stored in the existing data folder.
4. If you prefer to run the new extracted project instead, copy the previous
   `data/coursewise.sqlite3` into the new project's `data/` folder while both
   servers are stopped. Keep a backup of the original database.

## Put the key on your computer

In the project you will run, create a file named **.env** next to README.md.
Windows Notepad may append `.txt`: use Save as type **All files**, with filename
`.env`. If `.env` already exists, edit it and preserve your database setting.

```dotenv
PASS_THE_TORCH_AI_PROVIDER=gemini
GEMINI_API_KEY=PASTE_YOUR_GOOGLE_AI_STUDIO_KEY_HERE
GEMINI_MODEL=gemini-3.5-flash-lite
PASS_THE_TORCH_DB=data/pass-the-torch.sqlite3
```

Replace the placeholder with your key locally. Do not send the key in chat,
include it in screenshots, or commit `.env` to GitHub. `.gitignore` excludes it.
The model is a starting example from Google's current free-tier pricing table;
your project's model access and quota still need to be tested.

## Start and test

1. Run `start-windows.bat` from the project you updated, or use the existing
   uvicorn command from README.md.
2. Open <http://127.0.0.1:8000> and press **Ctrl+Shift+R**.
3. Sign in. Open Explore courses and ask a question such as:
   **Which requirements remain for my track, based on my current courses?**
4. The screen should show `AI configured: gemini`. A successful generated answer
   will have a **Gemini answer** notice. Configuration alone does not verify the
   key, quota, or quality of the generated answer.

The default real-evidence mode can still have no CSCI402 reviews. Select
**Try demo evidence** to use the separate, labelled fictional dataset; your
existing reviews remain unchanged.

## If the answer falls back to saved evidence

- **Not configured:** check that the file is exactly `.env`, both Gemini settings
  are populated, the provider is `gemini`, and the server was restarted.
- **400/401:** check the key and model ID. Copy the key without surrounding spaces.
- **403:** check Google project permissions, API restrictions and eligibility.
- **404:** copy an exact supported Gemini model ID from AI Studio into
  `GEMINI_MODEL`, then restart. Do not paste a display name or a URL.
- **429:** check the Google project's rate limit or quota. Creating a key does
  not by itself guarantee free-tier capacity.
- **Timed out:** retry after checking your connection and the provider status.
- **Unusable citations:** the model responded without usable source references;
  the app deliberately shows original evidence instead.

If settings still do not update, the terminal may have older environment
variables already set. The app follows environment-variable precedence over
`.env`; open a fresh terminal or update those specific variables, then restart.
Do not paste your full environment or key into diagnostics.

Google's free tier lists submitted content as eligible for product improvement.
Use non-sensitive, clearly labelled simulated data for a free-tier demo. This update includes a separate labelled demo database. It preserves your real
reviews and never presents the fictional fixtures as actual student experience.
