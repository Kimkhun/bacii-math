from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, problems, vision

app = FastAPI(title="BACII Math Engine", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3016", "http://127.0.0.1:3016"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(problems.me_router)
app.include_router(vision.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "BACII Math Engine", "docs": "/docs", "health": "/health"}
