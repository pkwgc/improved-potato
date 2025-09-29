from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from .routers import auth, games, props, admin, profile
from .database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Texas Poker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(games.router)
app.include_router(props.router)
app.include_router(admin.router)
app.include_router(profile.router)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {
        "message": "Texas Poker API",
        "version": "1.0.0",
        "docs": "/docs"
    }
