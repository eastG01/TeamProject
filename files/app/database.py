# app/database.py
# SQLite DB 연결 및 쿼리 모음
# F-03: 욕설 사전 조회
# F-08: 필터링 로그 저장
# F-09: ai_score 조건부 저장
# F-10: 유저 경고 누적 관리

import sqlite3
import json
from datetime import datetime
from typing import Optional

DB_PATH = "hate_filter.db"


def get_connection():
    """DB 연결 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하게
    return conn


# ── F-03: 욕설 사전 조회 ──────────────────────────────────────────────────────
def get_badwords() -> list[dict]:
    """
    욕설 사전 전체 조회
    반환: [{"word": "시발", "patterns": ["si발", "ㅅㅂ"], "severity": 3}, ...]
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT word, patterns, severity FROM badwords")
        rows = cursor.fetchall()
        return [
            {
                "word":     row["word"],
                "patterns": json.loads(row["patterns"]),
                "severity": row["severity"]
            }
            for row in rows
        ]
    finally:
        conn.close()


def match_badword(normalized_text: str) -> Optional[str]:
    """
    F-03: 정규화된 텍스트에서 욕설 사전 매칭
    매칭되면 해당 욕설 단어 반환 / 없으면 None 반환
    """
    badwords = get_badwords()

    # 화이트리스트 먼저 확인
    if is_whitelisted(normalized_text):
        return None

    for entry in badwords:
        # 원형 단어 확인
        if entry["word"] in normalized_text:
            return entry["word"]
        # 변형 패턴 확인 (정규화 후에도 남아있을 수 있는 패턴)
        for pattern in entry["patterns"]:
            if pattern in normalized_text:
                return pattern

    return None


def is_whitelisted(text: str) -> bool:
    """화이트리스트 단어가 포함되어 있으면 True"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM whitelist")
        rows = cursor.fetchall()
        for row in rows:
            if row["word"] in text:
                return True
        return False
    finally:
        conn.close()


# ── F-08, F-09: 필터링 로그 저장 ─────────────────────────────────────────────
def save_filter_log(
    user_id:         str,
    original_text:   str,
    normalized_text: str,
    detect_method:   str,           # "욕설사전" or "KcBERT"
    result:          str,           # "악플" / "보류" / "정상"
    action:          str,           # "차단" / "대기" / "통과"
    detected_word:   Optional[str] = None,   # 욕설사전 매칭 시
    ai_score:        Optional[float] = None  # KcBERT 판단 시
):
    """
    F-08: 모든 판단 결과 DB 저장
    F-09: 욕설사전 매칭이면 ai_score=NULL / KcBERT면 detected_word=NULL
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO filter_logs
            (user_id, original_text, normalized_text, detected_word,
             detect_method, ai_score, result, action, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            original_text,
            normalized_text,
            detected_word,   # 욕설사전 매칭이면 단어 / KcBERT면 None(NULL)
            detect_method,
            ai_score,        # KcBERT 점수 / 욕설사전이면 None(NULL)
            result,
            action,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
    finally:
        conn.close()


# ── F-10: 유저 경고 누적 관리 ────────────────────────────────────────────────
def update_user_penalty(user_id: str) -> dict:
    """
    악플 감지 시 유저 경고 누적
    1~2회 → 경고 / 3회 이상 → 계정 차단
    반환: {"warning_count": 2, "status": "경고"}
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 기존 제재 정보 조회
        cursor.execute(
            "SELECT warning_count, status FROM user_penalties WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row is None:
            # 첫 번째 악플 → 새로 생성
            warning_count = 1
            status = "경고"
            cursor.execute("""
                INSERT INTO user_penalties (user_id, warning_count, status, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, warning_count, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            # 기존 유저 → 경고 누적
            warning_count = row["warning_count"] + 1
            status = "차단" if warning_count >= 3 else "경고"
            cursor.execute("""
                UPDATE user_penalties
                SET warning_count = ?, status = ?, updated_at = ?
                WHERE user_id = ?
            """, (warning_count, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))

        conn.commit()
        return {"warning_count": warning_count, "status": status}
    finally:
        conn.close()


def get_user_status(user_id: str) -> Optional[str]:
    """유저 현재 제재 상태 조회 (차단된 유저면 "차단" 반환)"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM user_penalties WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row["status"] if row else "정상"
    finally:
        conn.close()
