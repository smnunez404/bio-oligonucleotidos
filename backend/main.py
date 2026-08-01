"""App FastAPI de la plataforma visual — expone el pipeline bio-oligonucleotidos."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    aso_masking,
    heuristic_filters,
    off_target,
    oligo_walk,
    ranking,
    sequence,
    splice_motifs,
    structure,
    thermodynamics,
)

app = FastAPI(
    title="bio-oligonucleotidos API",
    description="Pipeline de diseño in silico de ASO splice-switching contra ABCA4 c.161-395G>A",
    version="0.1.0",
)

# El frontend Vite corre en un puerto distinto durante desarrollo local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sequence.router)
app.include_router(oligo_walk.router)
app.include_router(heuristic_filters.router)
app.include_router(splice_motifs.router)
app.include_router(thermodynamics.router)
app.include_router(structure.router)
app.include_router(off_target.router)
app.include_router(aso_masking.router)
app.include_router(ranking.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
