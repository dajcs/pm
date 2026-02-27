from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Kanban Studio API")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve static frontend -- must be last so /api routes take priority
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
