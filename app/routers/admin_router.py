# app/routers/admin_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3, json
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["관리자"])
DB_PATH = "hate_filter.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class BadwordCreate(BaseModel):
    word: str
    patterns: list[str] = []
    severity: int = 1

class BadwordUpdate(BaseModel):
    patterns: Optional[list[str]] = None
    severity: Optional[int] = None

class WhitelistCreate(BaseModel):
    word: str
    reason: str

class PenaltyUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

# 욕설 사전
@router.get("/badwords", summary="욕설 사전 전체 조회")
def get_badwords():
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM badwords ORDER BY severity DESC").fetchall()
        return [{"id": r["id"], "word": r["word"], "patterns": json.loads(r["patterns"]), "severity": r["severity"], "created_at": r["created_at"]} for r in rows]
    finally:
        conn.close()

@router.post("/badwords", summary="욕설 사전 추가")
def add_badword(body: BadwordCreate):
    conn = get_conn()
    try:
        if conn.execute("SELECT id FROM badwords WHERE word=?", (body.word,)).fetchone():
            raise HTTPException(status_code=400, detail=f"'{body.word}' 은 이미 존재합니다.")
        conn.execute("INSERT INTO badwords (word, patterns, severity) VALUES (?, ?, ?)",
            (body.word, json.dumps(body.patterns, ensure_ascii=False), body.severity))
        conn.commit()
        return {"message": f"'{body.word}' 추가 완료"}
    finally:
        conn.close()

@router.put("/badwords/{badword_id}", summary="욕설 사전 수정")
def update_badword(badword_id: int, body: BadwordUpdate):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM badwords WHERE id=?", (badword_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="해당 단어를 찾을 수 없습니다.")
        new_patterns = json.dumps(body.patterns if body.patterns is not None else json.loads(row["patterns"]), ensure_ascii=False)
        new_severity = body.severity if body.severity is not None else row["severity"]
        conn.execute("UPDATE badwords SET patterns=?, severity=? WHERE id=?", (new_patterns, new_severity, badword_id))
        conn.commit()
        return {"message": f"id={badword_id} 수정 완료"}
    finally:
        conn.close()

@router.delete("/badwords/{badword_id}", summary="욕설 사전 삭제")
def delete_badword(badword_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT word FROM badwords WHERE id=?", (badword_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="해당 단어를 찾을 수 없습니다.")
        conn.execute("DELETE FROM badwords WHERE id=?", (badword_id,))
        conn.commit()
        return {"message": f"'{row['word']}' 삭제 완료"}
    finally:
        conn.close()

# 화이트리스트
@router.get("/whitelist", summary="화이트리스트 전체 조회")
def get_whitelist():
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM whitelist ORDER BY created_at DESC").fetchall()]
    finally:
        conn.close()

@router.post("/whitelist", summary="화이트리스트 추가")
def add_whitelist(body: WhitelistCreate):
    conn = get_conn()
    try:
        if conn.execute("SELECT id FROM whitelist WHERE word=?", (body.word,)).fetchone():
            raise HTTPException(status_code=400, detail=f"'{body.word}' 은 이미 존재합니다.")
        conn.execute("INSERT INTO whitelist (word, reason) VALUES (?, ?)", (body.word, body.reason))
        conn.commit()
        return {"message": f"'{body.word}' 화이트리스트 추가 완료"}
    finally:
        conn.close()

@router.delete("/whitelist/{whitelist_id}", summary="화이트리스트 삭제")
def delete_whitelist(whitelist_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT word FROM whitelist WHERE id=?", (whitelist_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="해당 단어를 찾을 수 없습니다.")
        conn.execute("DELETE FROM whitelist WHERE id=?", (whitelist_id,))
        conn.commit()
        return {"message": f"'{row['word']}' 삭제 완료"}
    finally:
        conn.close()

# 유저 제재
@router.get("/penalties", summary="유저 제재 전체 조회")
def get_penalties():
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM user_penalties ORDER BY warning_count DESC").fetchall()]
    finally:
        conn.close()

@router.put("/penalties/{user_id}", summary="유저 제재 상태 수정")
def update_penalty(user_id: str, body: PenaltyUpdate):
    if body.status not in ["정상", "경고", "차단"]:
        raise HTTPException(status_code=400, detail="status는 '정상', '경고', '차단' 중 하나여야 합니다.")
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM user_penalties WHERE user_id=?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")
        conn.execute("UPDATE user_penalties SET status=?, reason=?, updated_at=? WHERE user_id=?",
            (body.status, body.reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        return {"message": f"user_id={user_id} → '{body.status}' 변경 완료"}
    finally:
        conn.close()

@router.delete("/penalties/{user_id}", summary="유저 제재 초기화")
def reset_penalty(user_id: str):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM user_penalties WHERE user_id=?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")
        conn.execute("DELETE FROM user_penalties WHERE user_id=?", (user_id,))
        conn.commit()
        return {"message": f"user_id={user_id} 제재 초기화 완료"}
    finally:
        conn.close()

# 회원 관리
@router.get("/users", summary="가입 회원 전체 조회")
def get_users():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT u.user_id, u.created_at,
                   COALESCE(p.warning_count, 0) AS warning_count,
                   COALESCE(p.status, '정상')   AS status
            FROM users u
            LEFT JOIN user_penalties p ON u.user_id = p.user_id
            ORDER BY u.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.delete("/users/{user_id}", summary="회원 삭제")
def delete_user(user_id: str):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM users WHERE user_id=?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_penalties WHERE user_id=?", (user_id,))
        conn.commit()
        return {"message": f"'{user_id}' 회원 삭제 완료"}
    finally:
        conn.close()
@router.get("/logs", summary="필터링 로그 전체 조회")
def get_logs():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, user_id, original_text, detect_method,
                   ai_score, result, action, created_at
            FROM filter_logs
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.delete("/logs/{log_id}", summary="댓글 로그 삭제")
def delete_log(log_id: int):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM filter_logs WHERE id=?", (log_id,)).fetchone():
            raise HTTPException(status_code=404, detail="해당 댓글을 찾을 수 없습니다.")
        conn.execute("DELETE FROM filter_logs WHERE id=?", (log_id,))
        conn.commit()
        return {"message": f"댓글 id={log_id} 삭제 완료"}
    finally:
        conn.close()

# 이의제기
@router.get("/appeals", summary="이의제기 목록 조회")
def get_appeals():
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT a.id, a.comment_id, a.user_id, a.reason, a.status, a.created_at,
                   c.content, c.original_content
            FROM appeals a
            JOIN comments c ON a.comment_id = c.id
            ORDER BY a.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.post("/appeals/{appeal_id}/restore", summary="오탐 복원 및 화이트리스트 추가")
def restore_appeal(appeal_id: int, add_whitelist: bool = True):
    conn = get_conn()
    try:
        appeal = conn.execute("""
            SELECT a.*, c.original_content
            FROM appeals a JOIN comments c ON a.comment_id = c.id
            WHERE a.id=?
        """, (appeal_id,)).fetchone()
        if not appeal:
            raise HTTPException(status_code=404, detail="이의제기를 찾을 수 없습니다.")

        # 원문으로 복원
        conn.execute(
            "UPDATE comments SET content=? WHERE id=?",
            (appeal["original_content"], appeal["comment_id"])
        )

        # 이의제기 상태 승인으로 변경
        conn.execute(
            "UPDATE appeals SET status='승인', reviewed_at=datetime('now','localtime') WHERE id=?",
            (appeal_id,)
        )

        # Feedback loop: 마스킹된 단어 각각 화이트리스트에 추가
        if add_whitelist:
            import json
            row = conn.execute("SELECT masked_words FROM comments WHERE id=?", (appeal["comment_id"],)).fetchone()
            words = []
            if row and row["masked_words"]:
                try:
                    words = json.loads(row["masked_words"])
                except:
                    pass
            for word in set(words):
                if word:
                    conn.execute(
                        "INSERT OR IGNORE INTO whitelist (word, reason, created_by) VALUES (?, ?, ?)",
                        (word, f"오탐 복원 자동 추가 (이의제기 #{appeal_id})", "system")
                    )

        conn.commit()
        return {"message": f"이의제기 #{appeal_id} 승인 및 원문 복원 완료"}
    finally:
        conn.close()

@router.post("/appeals/{appeal_id}/reject", summary="이의제기 거절")
def reject_appeal(appeal_id: int):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM appeals WHERE id=?", (appeal_id,)).fetchone():
            raise HTTPException(status_code=404, detail="이의제기를 찾을 수 없습니다.")
        conn.execute(
            "UPDATE appeals SET status='거절', reviewed_at=datetime('now','localtime') WHERE id=?",
            (appeal_id,)
        )
        conn.commit()
        return {"message": f"이의제기 #{appeal_id} 거절 완료"}
    finally:
        conn.close()
