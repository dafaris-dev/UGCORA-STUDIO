# UGCORA Studio

**Product → Creator → Video.**

UGCORA Studio is a **private, single-owner** AI creative studio for generating
UGC-style marketing videos. It is **not** a SaaS: there is no billing, no
subscriptions, no public registration — just you, your products, and your AI
providers.

Workflow:

```
Upload Product → Analyze (Gemini) → Choose Creator → Generate Script →
Edit Script → Choose Style → Generate Video → Preview → Download
```

---

## 🚀 Quickstart (menjalankan di komputer kamu)

### Prasyarat
- **Python 3.11+** — [download di python.org](https://www.python.org/downloads/)
  (Windows: saat install, centang **"Add Python to PATH"**)
- Terminal / Command Prompt

### 1. Download project
```bash
git clone https://github.com/dafaris-dev/UGCORA-STUDIO.git
cd UGCORA-STUDIO
```

### 2. Jalankan sekali untuk setup

**macOS / Linux:**
```bash
./start.sh
```

**Windows:**
```bat
start.bat
```

Script ini akan otomatis:
1. Membuat virtual environment (`venv/`)
2. Install semua dependency
3. Membuat file `.env` dari template
4. Berhenti dan minta kamu isi `.env`

### 3. Edit `.env`
Buka file `.env` (text editor apa saja) dan isi:
```ini
ADMIN_USERNAME=namamu
ADMIN_PASSWORD=password-rahasia

GEMINI_API_KEY=xxx     # dari https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-2.0-flash

NVIDIA_API_KEY=xxx     # dari https://build.nvidia.com/
NVIDIA_MODEL=           # id model video (lihat katalog NVIDIA NIM)
NVIDIA_BASE_URL=https:/integrate.api.nvidia.com/v1
```

### 4. Jalankan lagi
```bash
./start.sh          # macOS/Linux
start.bat           # Windows
```

### 5. Buka di browser
```
http://127.0.0.1:8000
```
Login pakai `ADMIN_USERNAME` + `ADMIN_PASSWORD` dari `.env`.

---

## Cara akses dari HP / device lain di jaringan WiFi yang sama

Edit `.env`:
```ini
APP_HOST=0.0.0.0
APP_PORT=8000
```
Lalu jalankan ulang. Dari HP buka `http://IP-LAPTOPMU:8000` (cek IP laptop
dengan `ipconfig` di Windows atau `ifconfig` / `ip a` di mac/linux).

---

## Setup manual (tanpa script)

Kalau mau manual:
```bash
python -m venv venv

# Activate
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate          # Windows

pip install -r requirements.txt
cp .env.example .env           # (Windows: copy .env.example .env)
# edit .env
python run.py
```

---

## Struktur project
```
app/
├── main.py              FastAPI app factory
├── routes/              HTTP routes (pages + /api/*)
├── services/            Gemini, NVIDIA, prompt engine, video orchestration, auth
├── models/              SQLAlchemy models + DB bootstrap
├── templates/           Jinja2 HTML
└── static/              CSS, JS

data/                    Local storage (SQLite db, uploads, generated videos)
```

## Fitur utama

- **Products** — Upload gambar, Gemini analyze: kategori, audience, problem,
  USP, marketing angle, hook, CTA.
- **Creator Library** — 8 fictional creator pre-seeded, bisa tambah custom.
- **Scripts** — 12 template × 8 tone × 4 durasi. Gemini generate + rewrite.
- **Prompt Engine** — 13-section structured prompt (SUBJECT, ENVIRONMENT, …).
- **Video Provider Abstraction** — `NvidiaVideoProvider` sudah terpasang.
  Jika model yang dikonfigurasi tidak mendukung video, aplikasi **jujur
  menolak** — tidak pernah fake output.
- **Projects** — Mengelompokkan campaign (product + creators + videos + variations).
- **Settings** — Masked API keys, test connection untuk setiap provider.

## Keamanan
- API keys hanya di `.env` atau DB override — tidak pernah tampil ke
  frontend plain (UI menampilkan `••••••••••1234`).
- Password admin di-hash dengan bcrypt.
- `.env` sudah di `.gitignore`.
- Session cookie di-sign dengan `SESSION_SECRET`.

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `Gemini API key is not configured` | Isi `GEMINI_API_KEY` di `.env` atau Settings page |
| `This configured provider/model does not support video generation` | Ganti `NVIDIA_MODEL` ke model video-capable (cari di NVIDIA NIM catalog) |
| Port 8000 sudah dipakai | Ubah `APP_PORT=8080` di `.env` |
| `python: command not found` | Install Python 3.11+ dan tambahkan ke PATH |
| DB corrupt | Hapus `data/ugcora.db` dan jalankan ulang; akan dibuat lagi |

## License
Private project. Not for distribution.
