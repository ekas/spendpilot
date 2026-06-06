from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.cases import router as cases_router
from app.storage.case_repository import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="DecisionOS Spend Intelligence Demo", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(cases_router)

@app.get("/")
def root():
    return {"name":"DecisionOS Spend Intelligence Demo", "docs":"/docs", "frontend":"Run the React app on port 5173"}

@app.get("/health")
def health():
    return {"status":"ok"}
