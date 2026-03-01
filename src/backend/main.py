from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

ASSETS_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the Vite SPA — html=True handles client-side routing (returns index.html for unknown paths)
if ASSETS_DIR.exists():
    app.mount("/", StaticFiles(directory=ASSETS_DIR, html=True), name="spa")
