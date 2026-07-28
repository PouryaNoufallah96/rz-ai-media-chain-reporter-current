# AGENTS.md

Read this first, every session. Then read only the file(s) you actually need.

## Stack
- **Backend**: Python 3.11, raw `http.server` on port **3001** (NOT Flask/FastAPI). SQLite DB.
- **Frontend**: React + Vite (`frontend/`), talks to backend via `/api/*` with cookies.
- **AI**: all LLM/image calls go through **OpenRouter**. Google Apps Script for Sheets.

## Backend module map (`backend/`)
| File | Owns |
|---|---|
| `server.py` (~300) | HTTP `Handler` class + route dispatch + `__main__`. No business logic. |
| `config.py` | `.env` loader + shared constants: `EDITORIAL_MODELS`, `PLAT_RULES`, `BRAND_HASHTAGS`, `BRAND_PROMO_PITCH`, brand-tone dicts. |
| `llm.py` | `openrouter_chat`, `_repair_json`, `openrouter_image`, OpenAI-SDK client singleton. |
| `brand_profiles.py` (~1260) | `BRAND_IMAGE_PROFILES` — the big per-brand image-style dicts. Read ONLY when editing image profiles. |
| `image_pipeline.py` | Art-Director 2-stage image pipeline: brief → validate → assemble prompt. |
| `handlers/copy.py` | Social copy generation (`/api/copy/generate`). |
| `handlers/image.py` | Promo ideas + image gen (`/api/promo/generate-ideas`, `/api/image/generate`). |
| `handlers/editorial.py` | Multi-model editorial select + filter pipelines (`/api/ai/editorial-select`, `/api/filter/*`). |
| `handlers/account.py` | Activity logging, saved cards, summary, brand keywords (`/api/account/*`). |
| `handlers/schedule.py` | Schedule CRUD + background auto-post loop (`/api/schedule/*`). |
| `handlers/social.py` | Telegram + X/Twitter posting (`/api/telegram/post`, `/api/twitter/post`). |
| `handlers/sheets.py` | Google Apps Script proxy (`/api/sheets/*`). |
| `database.py`, `auth.py` | SQLite layer + auth/sessions. |
| `filtering/` | Embedding + DeepSeek editorial scoring pipeline. |
| `brand_docs/*.docx` | The 4 brand bibles (RZ Prime, Coin Hall, Meta Coin Guard, ChainReporter). |

## UI section ↔ endpoint ↔ backend file
| UI section | Frontend file | Endpoint(s) | Backend file |
|---|---|---|---|
| Login / logout | `store/authStore.js` | `/api/auth/*` | `auth.py` + `server.py` |
| Editorial lane board + Analyze button | `hooks/useAnalyzeAndRoute.js` | `/api/filter/pipeline`, `/api/filter/deepseek`, `/api/ai/editorial-select` | `handlers/editorial.py` + `filtering/` |
| Promo post ideas (promo mode) | `hooks/useAnalyzeAndRoute.js` | `/api/promo/generate-ideas` | `handlers/image.py` |
| Per-card social copy generation | `utils/routeCardToPlatform.js` | `/api/copy/generate` | `handlers/copy.py` |
| Image preview / generate | `components/mm/PreviewPanel.jsx` | `/api/image/generate` | `handlers/image.py` + `image_pipeline.py` |
| Publish to Telegram / X | `components/mm/PreviewPanel.jsx` | `/api/telegram/post`, `/api/twitter/post` | `handlers/social.py` |
| Approve / schedule / update Sheet | `components/mm/PreviewPanel.jsx` | `/api/sheets/*`, `/api/schedule/create` | `handlers/sheets.py`, `handlers/schedule.py` |
| Save card / log activity | `components/mm/PreviewPanel.jsx` | `/api/account/save`, `/api/account/log-action` | `handlers/account.py` |
| Account dashboard (stats, saved, scheduled) | `store/accountStore.js` + `components/account/*` | `/api/account/summary`, `/api/account/saved*`, `/api/schedule/*` | `handlers/account.py`, `handlers/schedule.py` |
| RSS feed import | `utils/rss.js` | `/api/rss` | `server.py` (inline) |
| Sidebar brand-keywords | `components/mm/Sidebar.jsx` | `/api/account/brand-keywords` | `handlers/account.py` |

## Critical rules
- **Brand bibles already live in `backend/brand_docs/*.docx`** (loaded via `brand_docs/__init__.py`). Never paste them into chat — reference by brand name.
- **Read only the file(s) you need** (use the tables above). Don't read whole `server.py` or `brand_profiles.py` unless the task is literally in them.
- `.env` holds all keys (OpenRouter, Telegram, X, Apps Script). Never paste secrets into chat.
- **Start backend**: `cd backend && python server.py` (port 3001). **Frontend**: `cd frontend && npm run dev`.
- Keep `MEDIA_LIST` in `backend/config.py` in sync with `frontend/src/store/mmStore.js`.
- Routes are dispatched by exact path string in `server.py` `Handler.do_GET` / `do_POST` — add new routes there.
## VPS update recipe
- ChainReporter deploy target is locked by `DEPLOYMENT_TARGET.lock`: VPS `5.75.207.209`, remote root `/var/www/chainreporter`, services `chainreporter-backend` and `chainreporter-frontend`.
- Never deploy this folder to the forbidden VPS `51.255.163.171` or remote root `/var/www/rzecosystem`.
- Use `deploy-to-vps.ps1` with an explicit `-Files` list for the files changed in the task; do not rely on Git auto-detection in this folder because the worktree may contain unrelated edits.
- Workspace deploy key filename: `.deploy_chainreporter_vps_key` (gitignored). The deploy script auto-selects it, canonicalizes it into `%TEMP%`, and grants access to the actual process user from `whoami` so Codex sandbox users can SSH.
- Normal deploy command shape:
  `powershell -ExecutionPolicy Bypass -File .\deploy-to-vps.ps1 -Files "frontend/src/path.jsx,backend/handlers/file.py"`
- If key access fails, check the workspace key grants the current process user from `whoami`, not just `$env:USERNAME`:
  `icacls .\.deploy_chainreporter_vps_key /grant:r "$((whoami).Trim()):(R)"`
- If a private key was pasted into chat or copied manually, rotate it on the VPS after use.
- After deploy, verify remotely:
  `ssh -i <key> root@5.75.207.209 "systemctl is-active chainreporter-backend; systemctl is-active chainreporter-frontend; curl -fsS http://127.0.0.1:3001/api/health"`
