# squirrel-cf-bypass

Repo-local Cloudflare bypass sidecar for Squirrel.

## Run locally

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-cf-bypass'
pipenv install --dev
pipenv run uvicorn squirrel_cf_bypass.app.main:app --host 0.0.0.0 --port 8002
```

## Endpoints

- `GET /health`
- `POST /cache/clear`
- `GET /html?url=...`
- `ANY /{path:path}` with `x-hostname`
