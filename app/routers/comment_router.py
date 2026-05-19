# app/routers/comment_router.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import sqlite3
from app.auth import get_current_user
from app.filter_queue import enqueue_filter_task
from app.database import get_user_status

router = APIRouter(tags=["댓글"])
DB_PATH = "hate_filter.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class CommentCreate(BaseModel):
    user_id: str
    content: str
    parent_id: Optional[int] = None

class AppealCreate(BaseModel):
    user_id: str
    reason: str


@router.get("/posts/{post_id}/comments", summary="댓글 목록 조회")
def get_comments(post_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        rows = conn.execute("""
            SELECT id, user_id, parent_id, content, is_deleted, created_at
            FROM comments
            WHERE post_id=?
            ORDER BY created_at ASC
        """, (post_id,)).fetchall()

        result = []
        for r in rows:
            item = dict(r)
            if item["is_deleted"]:
                item["content"] = "삭제된 댓글입니다."
            result.append(item)
        return result
    finally:
        conn.close()


@router.post("/posts/{post_id}/comments", summary="댓글 작성")
def create_comment(post_id: int, body: CommentCreate, background_tasks: BackgroundTasks):
    get_current_user(body.user_id)

    if not body.content.strip():
        raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요.")
    if len(body.content) > 500:
        raise HTTPException(status_code=400, detail="댓글은 500자를 초과할 수 없습니다.")

    # 차단 유저 확인
    user_status = get_user_status(body.user_id)
    if user_status == "차단":
        raise HTTPException(status_code=403, detail="차단된 계정입니다.")

    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone():
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        if body.parent_id is not None:
            if not conn.execute(
                "SELECT id FROM comments WHERE id=? AND post_id=? AND is_deleted=0",
                (body.parent_id, post_id)
            ).fetchone():
                raise HTTPException(status_code=404, detail="대상 댓글을 찾을 수 없습니다.")

        # 댓글 즉시 저장 (original_content에 원문 보존)
        cursor = conn.execute("""
            INSERT INTO comments (post_id, user_id, parent_id, content, original_content)
            VALUES (?, ?, ?, ?, ?)
        """, (post_id, body.user_id, body.parent_id, body.content.strip(), body.content.strip()))

        conn.execute("UPDATE posts SET comment_count = comment_count + 1 WHERE id=?", (post_id,))
        conn.commit()

        comment_id = cursor.lastrowid

        # KcBERT 필터링 백그라운드 실행
        enqueue_filter_task(background_tasks, comment_id, body.user_id, body.content)

        return {"comment_id": comment_id, "content": body.content.strip()}
    finally:
        conn.close()


@router.post("/comments/{comment_id}/appeal", summary="댓글 이의제기")
def appeal_comment(comment_id: int, body: AppealCreate):
    get_current_user(body.user_id)
    conn = get_conn()
    try:
        row = conn.execute("SELECT user_id, is_deleted FROM comments WHERE id=?", (comment_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
        if row["is_deleted"]:
            raise HTTPException(status_code=400, detail="삭제된 댓글입니다.")
        if row["user_id"] != body.user_id:
            raise HTTPException(status_code=403, detail="본인 댓글만 이의제기할 수 있습니다.")
        existing = conn.execute(
            "SELECT id FROM appeals WHERE comment_id=? AND status='대기'", (comment_id,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="이미 이의제기가 접수되어 있습니다.")
        conn.execute(
            "INSERT INTO appeals (comment_id, user_id, reason) VALUES (?, ?, ?)",
            (comment_id, body.user_id, body.reason)
        )
        conn.commit()
        return {"message": "이의제기가 접수되었습니다."}
    finally:
        conn.close()


@router.delete("/comments/{comment_id}", summary="댓글 삭제")
def delete_comment(comment_id: int, user_id: str):
    get_current_user(user_id)
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id, is_deleted FROM comments WHERE id=?", (comment_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
        if row["is_deleted"]:
            raise HTTPException(status_code=400, detail="이미 삭제된 댓글입니다.")
        if row["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="본인 댓글만 삭제할 수 있습니다.")

        conn.execute("UPDATE comments SET is_deleted=1 WHERE id=?", (comment_id,))
        conn.commit()
        return {"message": "댓글이 삭제되었습니다."}
    finally:
        conn.close()
