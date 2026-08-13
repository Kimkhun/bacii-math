from fastapi import FastAPI

from routers import auth, problems

app = FastAPI(title="BACII Math Engine", version="0.2.0")

app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(problems.me_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "BACII Math Engine", "docs": "/docs", "health": "/health"}
