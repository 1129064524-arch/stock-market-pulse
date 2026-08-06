# Windows desktop build

The desktop build keeps the entire analysis engine local:

- Electron opens the desktop window.
- The bundled `market-pulse-api.exe` serves the React build and all `/api/*` routes on `127.0.0.1:8765`.
- Market data, rules, fund scanning and model calls all run in the local FastAPI process; the API key never enters the renderer.

For a packaged install, put the model settings in the user's app data directory:

```text
%APPDATA%/Market Pulse/.env
```

Copy the relevant values from the repository `.env.example`. The shared visual-analysis channel is supported through `PROMPT_ANALYSIS_API_BASE_URL`, `PROMPT_ANALYSIS_ENDPOINT`, `PROMPT_ANALYSIS_API_KEY`, and `PROMPT_ANALYSIS_MODEL`.

To enable background model coordination in the scheduler, set `LLM_AUTO_ANALYSIS=true`. It runs only during trading sessions and defaults to one cross-market analysis every three minutes.

Build prerequisites are Node.js 22, Python 3.12, the packages in `requirements.txt`, and PyInstaller. The GitHub Actions workflow installs PyInstaller, builds the API executable, packages the NSIS installer, and publishes it on `v*` tags. `electron-updater` checks the published GitHub Release when the packaged app starts.
