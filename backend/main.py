"""
TMDB Movie Recommender - FastAPI Backend
"""

import math
import os
import pickle
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, ".env")


def load_env_file(path: str) -> None:
    """Load KEY=VALUE pairs from .env without requiring python-dotenv."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(ENV_FILE)

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_DETAIL = "https://api.themoviedb.org/3/movie/{mid}"
LIVE_POSTER_FETCH = os.getenv("LIVE_POSTER_FETCH", "0").strip().lower() in {"1", "true", "yes", "on"}

MOVIES_PKL = os.path.join(HERE, "movies.pkl")
SIMILARITY_PKL = os.path.join(HERE, "similarity.pkl")
FRONTEND_DIR = os.path.join(HERE, "..", "frontend")

movies_df = None
similarity = None
poster_cache = {}
tmdb_unreachable = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global movies_df, similarity
    try:
        with open(MOVIES_PKL, "rb") as f:
            movies_df = pickle.load(f)
    except TypeError as exc:
        if "StringDtype.__init__" in str(exc):
            raise RuntimeError(
                "movies.pkl is incompatible with the current pandas version. "
                "Use backend venv or install pandas==3.0.2, then restart."
            ) from exc
        raise
    with open(SIMILARITY_PKL, "rb") as f:
        similarity = pickle.load(f)
    if "movie_id" not in movies_df.columns and "id" in movies_df.columns:
        movies_df.rename(columns={"id": "movie_id"}, inplace=True)
    movies_df.reset_index(drop=True, inplace=True)
    if TMDB_API_KEY:
        print(f"TMDB key loaded (length={len(TMDB_API_KEY)})")
        print(f"LIVE_POSTER_FETCH={'ON' if LIVE_POSTER_FETCH else 'OFF'}")
    else:
        print("TMDB key missing. Add TMDB_API_KEY to backend/.env to show real posters.")
    print(f"Loaded {len(movies_df)} movies")
    yield


app = FastAPI(title="Movie Recommender API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_poster_url(value: object) -> str:
    """Normalize poster value into a full URL when possible."""
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""

    path = str(value).strip()
    if not path or path.lower() == "nan":
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/"):
        return TMDB_IMG_BASE + path
    return ""


def get_poster_url(row) -> str:
    """Return poster URL: pkl value -> optional TMDB API -> empty string."""
    global tmdb_unreachable

    if "poster_path" in row:
        normalized = normalize_poster_url(row["poster_path"])
        if normalized:
            return normalized

    movie_id = int(row["movie_id"])
    if movie_id in poster_cache:
        return poster_cache[movie_id]

    if tmdb_unreachable:
        poster_cache[movie_id] = ""
        return ""

    if TMDB_API_KEY and LIVE_POSTER_FETCH:
        try:
            r = requests.get(
                TMDB_DETAIL.format(mid=movie_id),
                params={"api_key": TMDB_API_KEY},
                timeout=1.0,
            )
            if r.ok:
                path = r.json().get("poster_path", "")
                if path:
                    poster = TMDB_IMG_BASE + path
                    poster_cache[movie_id] = poster
                    return poster
        except Exception:
            # If TMDB is blocked/unreachable, stop retrying for every movie.
            tmdb_unreachable = True

    poster_cache[movie_id] = ""
    return ""


def row_to_dict(row) -> dict:
    rating = float(row.get("vote_average", 0)) if "vote_average" in row else 0.0
    return {
        "movie_id": int(row["movie_id"]),
        "title": str(row["title"]),
        "rating": round(rating, 1),
        "poster": get_poster_url(row),
    }


@app.get("/movies")
def list_movies(limit: int = Query(40, ge=1, le=200)):
    return [row_to_dict(row) for _, row in movies_df.head(limit).iterrows()]


@app.get("/search")
def search_movies(q: str = Query(..., min_length=1)):
    mask = movies_df["title"].str.contains(q, case=False, na=False)
    return [row_to_dict(row) for _, row in movies_df[mask].head(20).iterrows()]


@app.get("/recommend")
def recommend(movie: str = Query(..., min_length=1)):
    matches = movies_df[movies_df["title"].str.lower() == movie.lower()]
    if matches.empty:
        matches = movies_df[movies_df["title"].str.lower().str.contains(movie.lower(), na=False)]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Movie '{movie}' not found.")

    idx = matches.index[0]
    top5 = sorted(
        [(i, d) for i, d in enumerate(similarity[idx]) if i != idx],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    recs = []
    for i, score in top5:
        movie_data = row_to_dict(movies_df.iloc[i])
        movie_data["similarity"] = round(float(score), 4)
        recs.append(movie_data)
    return recs


if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
