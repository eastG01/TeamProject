import sqlite3

DB_PATH = "hate_filter.db"
conn = sqlite3.connect(DB_PATH)

conn.execute("""
CREATE TABLE IF NOT EXISTS appeals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id   INTEGER NOT NULL,
    user_id      TEXT NOT NULL,
    reason       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT '대기',
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    reviewed_at  TEXT
)
""")

try:
    conn.execute("ALTER TABLE comments ADD COLUMN original_content TEXT")
    print("original_content 컬럼 추가됨")
except Exception as e:
    print(f"original_content: {e}")

try:
    conn.execute("ALTER TABLE comments ADD COLUMN masked_words TEXT")
    print("masked_words 컬럼 추가됨")
except Exception as e:
    print(f"masked_words: {e}")

conn.commit()
conn.close()
print("마이그레이션 완료")
