import sqlite3
import json

DB_PATH = "hate_filter.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS badwords (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word        TEXT NOT NULL UNIQUE,
            patterns    TEXT NOT NULL DEFAULT '[]',
            severity    INTEGER NOT NULL DEFAULT 1,
            created_by  TEXT NOT NULL DEFAULT 'admin',
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS filter_logs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          TEXT NOT NULL,
            original_text    TEXT NOT NULL,
            normalized_text  TEXT NOT NULL,
            detected_word    TEXT,
            detect_method    TEXT NOT NULL,
            ai_score         REAL,
            result           TEXT NOT NULL,
            action           TEXT NOT NULL,
            created_at       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_penalties (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT NOT NULL UNIQUE,
            warning_count INTEGER NOT NULL DEFAULT 0,
            status        TEXT NOT NULL DEFAULT '정상',
            reason        TEXT,
            expired_at    TEXT,
            updated_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id   TEXT NOT NULL,
            target_id     TEXT NOT NULL,
            comment_text  TEXT NOT NULL,
            reason        TEXT NOT NULL,
            report_count  INTEGER NOT NULL DEFAULT 1,
            status        TEXT NOT NULL DEFAULT '대기',
            reviewed_by   TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            reviewed_at   TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            word        TEXT NOT NULL UNIQUE,
            reason      TEXT NOT NULL,
            created_by  TEXT NOT NULL DEFAULT 'admin',
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    sample_badwords = [
        ("시발",  json.dumps(["si발","ㅅㅂ","시*발","씨발"], ensure_ascii=False), 3),
        ("병신",  json.dumps(["ㅂㅅ","byung신","병*신"],      ensure_ascii=False), 3),
        ("새끼",  json.dumps(["ㅅㄲ","saek끼","새*끼"],       ensure_ascii=False), 2),
        ("멍청이", json.dumps(["멍*청이","멍청ㅇ"],            ensure_ascii=False), 1),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO badwords (word, patterns, severity)
        VALUES (?, ?, ?)
    """, sample_badwords)

    cursor.execute("""
        INSERT OR IGNORE INTO whitelist (word, reason)
        VALUES ('병신증', '의학 용어')
    """)

    conn.commit()
    conn.close()
    print("DB 생성 완료!")
    print("테이블 생성: badwords / filter_logs / user_penalties / reports / whitelist")

if __name__ == "__main__":
    init_db()