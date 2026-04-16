# app/routers/report_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from app.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["신고"])
DB_PATH = "hate_filter.db"

VALID_REASONS = ["욕설", "스팸", "음란물", "기타"]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class ReportCreate(BaseModel):
    reporter_id: str
    comment_id: int
    reason: str


@router.post("", summary="댓글 신고")
def create_report(body: ReportCreate):
    get_current_user(body.reporter_id)

    if body.reason not in VALID_REASONS:
        raise HTTPException(status_code=400, detail=f"신고 사유는 {VALID_REASONS} 중 하나여야 합니다.")

    conn = get_conn()
    try:
        comment = conn.execute(
            "SELECT user_id, content, is_deleted FROM comments WHERE id=?",
            (body.comment_id,)
        ).fetchone()
        if not comment:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
        if comment["is_deleted"]:
            raise HTTPException(status_code=400, detail="삭제된 댓글은 신고할 수 없습니다.")
        if comment["user_id"] == body.reporter_id:
            raise HTTPException(status_code=400, detail="본인 댓글은 신고할 수 없습니다.")

        # 중복 신고 확인 (1인 1신고)
        existing = conn.execute("""
            SELECT id FROM reports
            WHERE reporter_id=? AND comment_text=? AND target_id=?
        """, (body.reporter_id, comment["content"], comment["user_id"])).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="이미 신고한 댓글입니다.")

        conn.execute("""
            INSERT INTO reports (reporter_id, target_id, comment_text, reason)
            VALUES (?, ?, ?, ?)
        """, (body.reporter_id, comment["user_id"], comment["content"], body.reason))
        conn.commit()
        return {"message": "신고가 접수되었습니다."}
    finally:
        conn.close()
