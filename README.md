# CineMatch - Movie Recommender

Full-stack movie recommendation app using FastAPI + vanilla JS.
Model is content-based similarity over movie metadata.

## Project Structure

```text
movie-recommender/
|-- backend/
|   |-- main.py
|   |-- preprocess.py
|   |-- requirements.txt
|   |-- .env
|   |-- movies.pkl
|   `-- similarity.pkl
`-- frontend/
    `-- index.html
```

## Local Setup (Windows)

### 1) Create and activate venv (recommended)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure environment

Create `backend/.env`:

```env
TMDB_API_KEY=your_tmdb_v3_key
LIVE_POSTER_FETCH=0
```

Notes:
- `LIVE_POSTER_FETCH=0`: fast/stable load, uses generated fallback posters.
- `LIVE_POSTER_FETCH=1`: fetch real TMDB posters at runtime.
- If TMDB API is blocked on your network, runtime poster fetch may need VPN.

### 4) Start backend (important: use venv python)

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open: `http://127.0.0.1:8000`

## API

- `GET /movies?limit=40`
- `GET /search?q=avatar`
- `GET /recommend?movie=Avatar`
- Docs: `http://127.0.0.1:8000/docs`

## Hosting Guide

## A) Host on same Wi-Fi/LAN (quick)

Run backend on all interfaces:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open from another device:

```text
http://YOUR_PC_LOCAL_IP:8000
```

(Allow Python/Uvicorn in Windows Firewall when prompted.)

## B) Public hosting (Render/Railway style)

1. Push project to GitHub.
2. Create a new Web Service.
3. Set root directory to `backend`.
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

6. Add environment variables in dashboard:
- `TMDB_API_KEY`
- `LIVE_POSTER_FETCH` (`0` or `1`)

After deploy, open your service URL.

## Troubleshooting

- `StringDtype.__init__...` error:
  - run app with backend venv Python
  - ensure `pandas==3.0.2` is installed
- App keeps loading spinner:
  - set `LIVE_POSTER_FETCH=0` and restart
- Posters not showing:
  - verify `TMDB_API_KEY` in `backend/.env`
  - with blocked network, use VPN or keep fallback mode (`LIVE_POSTER_FETCH=0`)
    <img width="1901" height="891" alt="image" src="https://github.com/user-attachments/assets/90ce3346-2f76-49dc-aec2-79507e7d3f36" />
    <img width="1901" height="668" alt="image" src="https://github.com/user-attachments/assets/116e9c00-adab-49c6-bab9-2fd69280936a" />
    <img width="1902" height="679" alt="image" src="https://github.com/user-attachments/assets/a232ca93-2c9b-49ff-9f26-b4052549e8fe" />



