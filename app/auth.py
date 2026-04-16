# app/auth.py
# 인증 모듈 - JWT 교체 시 이 파일만 수정하면 됨
# 현재: user_id DB 존재 여부 확인
# 교체 시: JWT 토큰 발급/검증으로 변경

import sqlite3
from fastapi import HTTPException

DB_PATH = "hate_filter.db"


def get_current_user(user_id: str) -> str:
    """
    현재 요청의 유저를 검증하고 user_id 반환.
    JWT 교체 시 파라미터를 token: str로 바꾸고 내부 로직만 수정.
    """
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT user_id FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="존재하지 않는 유저입니다.")
        return user_id
    finally:
        conn.close()
