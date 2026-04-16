# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.model import load_model
from app.routers import filter_router, admin_router, auth_router, post_router, comment_router, report_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield

app = FastAPI(
    title="악플 필터링 API",
    description="KcBERT 기반 실시간 악성 댓글 탐지 시스템",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(filter_router.router)
app.include_router(admin_router.router)
app.include_router(auth_router.router)
app.include_router(post_router.router)
app.include_router(comment_router.router)
app.include_router(report_router.router)
