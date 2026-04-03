# app/routers/auth_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from passlib.context import CryptContext
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["인증"])
DB_PATH = "hate_filter.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class AuthRequest(BaseModel):
    user_id: str
    password: str


@router.post("/register", summary="회원가입")
def register(body: AuthRequest):
    if not body.user_id.strip() or not body.password.strip():
        raise HTTPException(status_code=400, detail="아이디와 비밀번호를 입력해주세요.")
    if len(body.user_id) < 3 or len(body.user_id) > 20:
        raise HTTPException(status_code=400, detail="아이디는 3~20자 사이여야 합니다.")
    if len(body.password) < 4:
        raise HTTPException(status_code=400, detail="비밀번호는 4자 이상이어야 합니다.")

    conn = get_conn()
    try:
        if conn.execute("SELECT id FROM users WHERE user_id=?", (body.user_id,)).fetchone():
            raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")
        password_hash = pwd_context.hash(body.password)
        conn.execute(
            "INSERT INTO users (user_id, password_hash, created_at) VALUES (?, ?, ?)",
            (body.user_id, password_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return {"message": "회원가입이 완료되었습니다.", "user_id": body.user_id}
    finally:
        conn.close()


@router.post("/login", summary="로그인")
def login(body: AuthRequest):
    if not body.user_id.strip() or not body.password.strip():
        raise HTTPException(status_code=400, detail="아이디와 비밀번호를 입력해주세요.")

    conn = get_conn()
    try:
        # 유저 조회
        row = conn.execute(
            "SELECT user_id, password_hash FROM users WHERE user_id=?",
            (body.user_id,)
        ).fetchone()

        if not row or not pwd_context.verify(body.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

        # 차단 여부 확인
        penalty = conn.execute(
            "SELECT status FROM user_penalties WHERE user_id=?",
            (body.user_id,)
        ).fetchone()

        if penalty and penalty["status"] == "차단":
            raise HTTPException(status_code=403, detail="차단된 계정입니다. 관리자에게 문의하세요.")

        return {"message": "로그인 성공", "user_id": row["user_id"]}
    finally:
        conn.close()
