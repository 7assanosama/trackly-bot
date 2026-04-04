import sqlite3

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    url TEXT,
    last_content TEXT
)
""")

conn.commit()


def add_link(user_id, url, content):
    cursor.execute("INSERT INTO links (user_id, url, last_content) VALUES (?, ?, ?)",
                   (user_id, url, content))
    conn.commit()


def get_links():
    cursor.execute("SELECT * FROM links")
    return cursor.fetchall()


def update_content(link_id, content):
    cursor.execute("UPDATE links SET last_content=? WHERE id=?",
                   (content, link_id))
    conn.commit()