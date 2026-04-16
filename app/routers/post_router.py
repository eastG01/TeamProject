# app/routers/post_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime
from app.auth import get_current_user

router = APIRouter(prefix="/posts", tags=["게시글"])
DB_PATH = "hate_filter.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class PostCreate(BaseModel):
    user_id: str
    title: str
    content: str


@router.get("", summary="게시글 목록 조회")
def get_posts():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, user_id, title, comment_count, created_at
            FROM posts
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("", summary="게시글 작성")
def create_post(body: PostCreate):
    get_current_user(body.user_id)

    if not body.title.strip():
        raise HTTPException(status_code=400, detail="제목을 입력해주세요.")
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="내용을 입력해주세요.")
    if len(body.title) > 100:
        raise HTTPException(status_code=400, detail="제목은 100자를 초과할 수 없습니다.")
    if len(body.content) > 5000:
        raise HTTPException(status_code=400, detail="내용은 5000자를 초과할 수 없습니다.")

    conn = get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
            (body.user_id, body.title.strip(), body.content.strip())
        )
        conn.commit()
        return {"message": "게시글이 등록되었습니다.", "post_id": cursor.lastrowid}
    finally:
        conn.close()


@router.get("/{post_id}", summary="게시글 상세 조회")
def get_post(post_id: int):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM posts WHERE id=?", (post_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        return dict(row)
    finally:
        conn.close()


@router.delete("/{post_id}", summary="게시글 삭제")
def delete_post(post_id: int, user_id: str):
    get_current_user(user_id)
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id FROM posts WHERE id=?", (post_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        if row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="본인 게시글만 삭제할 수 있습니다.")
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
        return {"message": "게시글이 삭제되었습니다."}
    finally:
        conn.close()
