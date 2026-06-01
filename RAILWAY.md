# Deploy AI Decision OS on Railway

Railway is a better fit than serverless hosting for this app because it runs a normal Python web service with MCP subprocesses, streaming responses, local reports, and optional Playwright extraction.

## 1. Prepare the Repo

Commit these deployment files:

- `Dockerfile`
- `.dockerignore`
- `pyproject.toml`
- `src/**`

The web server reads Railway's `PORT` environment variable and binds to `0.0.0.0`.

## 2. Create a Railway Project

1. Push the repo to GitHub.
2. Open Railway.
3. Create a new project.
4. Choose **Deploy from GitHub repo**.
5. Select this repository.
6. Railway should detect the `Dockerfile` and build from it.

## 3. Add Environment Variables

In Railway project settings, add:

```text
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=your_tavily_key
DECISION_OS_DATA_DIR=/data/.decision_os
```

`TAVILY_API_KEY` is optional. Without it, search falls back to a lighter web-search path.

## 4. Add Persistent Storage

Add a Railway volume and mount it at:

```text
/data
```

This keeps generated reports and SQLite memory across deploys/restarts.

Without a volume, reports and memory may be lost when the container restarts.

## 5. Deploy

Railway will run:

```text
python -m ai_decision_os.web
```

The app will listen on:

```text
0.0.0.0:$PORT
```

## 6. Verify

Open the generated Railway domain and test:

```text
How can Model Context Protocol be used?
```

You should see:

- live run state
- MCP/direct transport selector
- final answer in the Goal section
- results trace
- saved report
- report download button

## Notes

- First deploy may take several minutes because Playwright installs Chromium.
- If Playwright makes the image too large, remove browser extraction or deploy without `extract_page`.
- For production, consider replacing SQLite with Postgres and report files with object storage.
