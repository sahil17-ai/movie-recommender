"""
preprocess.py  –  Run ONCE to generate movies.pkl and similarity.pkl
Optionally fetches poster_path from TMDB if TMDB_API_KEY is set.

Usage:
  python preprocess.py                        # no posters
  TMDB_API_KEY=xxx python preprocess.py       # with real posters
"""

import ast, pickle, os, time
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem.porter import PorterStemmer
import nltk, requests

nltk.download("punkt", quiet=True)

HERE        = os.path.dirname(os.path.abspath(__file__))
TMDB_KEY    = os.getenv("TMDB_API_KEY", "")
TMDB_API    = "https://api.themoviedb.org/3/movie/{mid}"
TMDB_IMG    = "https://image.tmdb.org/t/p/w500"

# ── 1. Load ───────────────────────────────────────────────────────
df1 = pd.read_csv(os.path.join(HERE, "tmdb_5000_movies.csv"))
df2 = pd.read_csv(os.path.join(HERE, "tmdb_5000_credits.csv"))

# ── 2. Merge ──────────────────────────────────────────────────────
df = df1.merge(df2, on="title")
df = df[["movie_id","title","overview","genres","keywords","cast","crew","vote_average"]]
df.dropna(inplace=True)

# ── 3. Parse columns ──────────────────────────────────────────────
def convert(obj):
    return [i["name"] for i in ast.literal_eval(obj)]

def convert3(obj):
    return [i["name"] for i in ast.literal_eval(obj)[:3]]

def fetch_director(obj):
    for i in ast.literal_eval(obj):
        if i["job"] == "Director":
            return [i["name"]]
    return []

df["genres"]   = df["genres"].apply(convert)
df["keywords"] = df["keywords"].apply(convert)
df["cast"]     = df["cast"].apply(convert3)
df["crew"]     = df["crew"].apply(fetch_director)
df["overview"] = df["overview"].apply(lambda x: x.split())

for col in ["genres","keywords","cast","crew"]:
    df[col] = df[col].apply(lambda x: [i.replace(" ","") for i in x])

df["tags"] = df["overview"] + df["genres"] + df["keywords"] + df["cast"] + df["crew"]

ndf = df[["movie_id","title","tags","vote_average"]].copy()
ndf["tags"] = ndf["tags"].apply(lambda x: " ".join(x).lower())

# ── 4. Stem ───────────────────────────────────────────────────────
ps = PorterStemmer()
def stem(text):
    return " ".join(ps.stem(w) for w in text.split())
ndf["tags"] = ndf["tags"].apply(stem)

# ── 5. Vectorise ──────────────────────────────────────────────────
cv      = CountVectorizer(max_features=5000, stop_words="english")
vectors = cv.fit_transform(ndf["tags"]).toarray()
similarity = cosine_similarity(vectors)

# ── 6. Optionally fetch poster_path ───────────────────────────────
ndf = ndf.reset_index(drop=True)
ndf["poster_path"] = ""

if TMDB_KEY:
    print(f"🎬 Fetching poster paths from TMDB for {len(ndf)} movies...")
    for i, row in ndf.iterrows():
        try:
            r = requests.get(
                TMDB_API.format(mid=int(row["movie_id"])),
                params={"api_key": TMDB_KEY},
                timeout=5
            )
            if r.ok:
                path = r.json().get("poster_path","")
                if path:
                    ndf.at[i,"poster_path"] = TMDB_IMG + path
        except:
            pass
        if i % 100 == 0:
            print(f"  {i}/{len(ndf)} done...")
            time.sleep(0.5)  # respect rate limit
    print("✅ Poster fetch complete!")
else:
    print("ℹ️  No TMDB_API_KEY set — posters will be generated dynamically in the UI.")

# ── 7. Save ───────────────────────────────────────────────────────
pickle.dump(ndf, open(os.path.join(HERE,"movies.pkl"),"wb"))
pickle.dump(similarity, open(os.path.join(HERE,"similarity.pkl"),"wb"))
print(f"✅  Done! Saved movies.pkl ({len(ndf)} movies) and similarity.pkl {similarity.shape}")
