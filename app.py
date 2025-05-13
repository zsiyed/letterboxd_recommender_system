import os
import pickle
import sqlite3
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# —— CONFIGURATION ——
MODEL_DIR = os.getenv("MODEL_DIR", "./models")
DB_PATH   = os.getenv("DB_PATH",   "./recommender.db")

# —— LOAD ARTIFACTS ON STARTUP ——
# user_to_idx: { username: user_index_in_matrix }
with open(os.path.join(MODEL_DIR, "user_to_idx.pkl"), "rb") as f:
    user_to_idx = pickle.load(f)

# idx_to_item: { item_index_in_matrix: movie_id_or_title_key }
with open(os.path.join(MODEL_DIR, "idx_to_item.pkl"), "rb") as f:
    idx_to_item = pickle.load(f)

# Factor matrices
user_factors = np.load(os.path.join(MODEL_DIR, "user_factors.npy"))   # shape (num_users,  k)
item_factors = np.load(os.path.join(MODEL_DIR, "item_factors.npy"))   # shape (num_items,  k)

# —— Pydantic schemas ——
class Recommendation(BaseModel):
    movie_id: str
    title: str
    score: float

class RecsResponse(BaseModel):
    username: str
    recommendations: List[Recommendation]

# —— APP INSTANCE ——
app = FastAPI(
    title="Matrix-Factorization Recommender",
    description="Given a username, return top-N movie recommendations.",
)

# —— UTILS ——
def get_metadata_for(movie_id: str):
    """
    Look up the movie title (and any other metadata) by movie_id
    from the `reviews` table in SQLite. Adjust query if you have
    a separate `items` table.
    """
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT title FROM reviews WHERE title = ? LIMIT 1", (movie_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "Unknown Title"


# —— ENDPOINT ——
@app.get(
    "/recommendations",
    response_model=RecsResponse,
    summary="Get top-N movie recs for a user",
)
def recommend(
    username: str,
    n: int = Query(10, ge=1, le=100, description="Number of movies to return"),
):
    # 1) Check user exists
    if username not in user_to_idx:
        raise HTTPException(status_code=404, detail="User not found in model.")

    # 2) Compute scores = dot(item_factors, user_vector)
    u_idx = user_to_idx[username]
    u_vec = user_factors[u_idx]                 # shape (k,)
    scores = item_factors @ u_vec               # shape (num_items,)

    # 3) Select top-N
    top_idx = np.argsort(scores)[::-1][:n]

    # 4) Build response payload
    recs = []
    for idx in top_idx:
        movie_id = idx_to_item[idx]
        title    = get_metadata_for(movie_id)
        recs.append(
            Recommendation(
                movie_id=movie_id,
                title=title,
                score=float(scores[idx]),
            )
        )

    return RecsResponse(username=username, recommendations=recs)