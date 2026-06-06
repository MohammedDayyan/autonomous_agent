# Deploy AI Decision OS on Render

Render works well for this app as a Docker web service. It is a better fit than serverless hosting because AI Decision OS uses a long-running Python server, MCP subprocesses, streaming responses, local reports, SQLite memory, and optional Playwright extraction.

Render docs:

- Web services: https://render.com/docs/web-services
- Docker services: https://render.com/docs/docker
- Persistent disks: https://render.com/docs/disks
- Environment variables: https://render.com/docs/configure-environment-variables
- Blueprints: https://render.com/docs/blueprint-spec

## Option A: Deploy Manually

1. Push this repo to GitHub.
2. Open Render.
3. Click **New +**.
4. Choose **Web Service**.
5. Connect your GitHub repository.
6. For runtime, choose **Docker**.
7. Render will use the root `Dockerfile`.
8. Set the health check path:

```text
/health
```

9. Add environment variables:

```text
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=your_tavily_key
GITHUB_TOKEN=your_github_token_optional
DECISION_OS_DATA_DIR=/data/.decision_os
```

10. Deploy.

## Option B: Deploy With Blueprint

This repo includes `render.yaml`.

1. Push this repo to GitHub.
2. In Render, choose **New +**.
3. Choose **Blueprint**.
4. Select this repo.
5. Render reads `render.yaml`.
6. Fill in the secret values for `GROQ_API_KEY`, `TAVILY_API_KEY`, and optional `GITHUB_TOKEN`.
7. Deploy.

## Persistent Reports and Memory

Render services use an ephemeral filesystem unless you attach a persistent disk. To preserve generated reports and SQLite memory:

1. Open the Render service.
2. Go to **Disks**.
3. Add a disk.
4. Mount it at:

```text
/data
```

5. Keep:

```text
DECISION_OS_DATA_DIR=/data/.decision_os
```

Without a disk, reports and memory may disappear after redeploys/restarts.

## Verify

After deploy, open:

```text
https://your-service.onrender.com/health
```

Expected:

```json
{
  "ok": true,
  "tavily_configured": true
}
```

If `tavily_configured` is `false`, the running Render service does not see your Tavily key. Open the service's **Environment** page and confirm the key is named exactly:

```text
TAVILY_API_KEY
```

The app also accepts `TRAVILY_API_KEY` as a compatibility fallback, but `TAVILY_API_KEY` is the correct name to use.

For deeper search diagnostics, open:

```text
https://your-service.onrender.com/health/search?q=Cristiano%20Ronaldo%20GOAT
```

The `provider` field should be `tavily`. If it is `duckduckgo`, the key is still missing from the deployed service environment.

Then open the main app and run:

```text
How can Model Context Protocol be used?
```

You should see:

- live run state
- final answer in the Goal section
- plan/results trace
- saved report
- report preview/download

## Notes

- First build can take several minutes because the Dockerfile installs Chromium for Playwright.
- If `extract_page` reports a missing Playwright executable under `/root/.cache/ms-playwright`, the service is probably not running from this Dockerfile or the Docker build did not run after the Playwright install step was added. Redeploy as a Docker web service from the latest commit.
- If the image becomes too large or builds are slow, remove Playwright extraction or switch `extract_page` to a lighter HTTP-only reader.
- For production, consider moving SQLite to Render Postgres and report files to object storage.
