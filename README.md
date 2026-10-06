# UGCORA Studio

**Product → Creator → Video.**

UGCORA Studio is a **private**, single-owner AI creative studio for generating
UGC-style marketing videos. It is **not** a SaaS: there is no billing, no
subscriptions, no public registration — just you, your products, and your AI providers.

The ideal workflow:

```
Upload Product → Analyze (Gemini) → Choose Creator → Generate Script →
Edit Script → Choose Style → Generate Video → Preview → Download
```

## Requirements

- Python 3.11+
- A Google Gemini API key (for product analysis & script generation)
- An NVIDIA API key with a model that supports video generation
  (any video-capable NVIDIA model; set the exact model id in Settings)

## Installation

```bash
# 1. Clone / enter project
cd ugcora

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
cp .env.example .env   # (or 'copy' on Windows)
```

Edit `.env` with your credentials:

```
ADMIN_USERNAME=you
ADMIN_PASSWORD=choose-a-strong-password
SESSION_SECRET=some-long-random-string

GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.0-flash

NVIDIA_API_KEY=your-nvidia-key
NVIDIA_MODEL=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

## Running

```bash
python run.py
```

Then open:

```
http://127.0.0.1:8000
```

Log in with the admin credentials from your `.env`. The SQLite database and
local data directories are created automatically on first run.

## Where things live

- `app/main.py` — FastAPI app factory, mounts routers and middleware.
- `app/routes/` — all HTTP routes (pages and API endpoints).
- `app/services/` — service layer: Gemini, NVIDIA, prompt engine, voice,
  file handling, auth, config, video orchestration.
- `app/models/` — SQLAlchemy models and database bootstrap.
- `app/templates/` — Jinja2 HTML.
- `app/static/` — CSS, JS, images.
- `data/` — all local file storage (SQLite DB, uploaded images, generated video files).

## Providers

### Gemini

Used for:

- Product image analysis
- UGC hook, CTA, and script generation
- Prompt engineering before the video call

The model is configurable at runtime in **Settings**.

### NVIDIA

Used for video generation. The service inspects the configured model and
clearly reports if the chosen model does not support video generation
rather than silently faking a result.

A `VideoProvider` abstraction (`app/services/video_service.py`) exists so
additional providers can be added without touching the UI.

## Troubleshooting

- **"Gemini API key is not configured"** → add it on the Settings page or in `.env`.
- **"This configured NVIDIA model does not support video generation"** →
  the NVIDIA model id you selected is image/text-only. Switch to a
  video-capable model in Settings.
- **"Not authenticated"** → session expired. Log in again.
- **Database errors** → delete `data/ugcora.db` and restart; it will be recreated.
- **File upload issues** → check `data/` is writable.

## Security

- API keys live in environment variables or an encrypted DB override (never
  returned to the browser in plain text — the UI shows `••••••••••1234`).
- Passwords are hashed with bcrypt.
- `.env` is in `.gitignore`.
- Sessions use signed cookies with `SESSION_SECRET`.

## License

Private project. Not for distribution.
