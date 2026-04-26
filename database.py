import sqlite3
import os
from datetime import datetime, timedelta

conn = sqlite3.connect(os.getenv("DB_PATH", "data.db"), check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    url TEXT,
    last_content TEXT
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT DEFAULT 'free',
    phone TEXT DEFAULT 'غير متوفر',
    max_links INTEGER DEFAULT 1,
    expiry_date DATETIME,
    last_warning_sent INTEGER DEFAULT -1
)
"""
)

try:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT 'غير متوفر'")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE users ADD COLUMN max_links INTEGER DEFAULT 1")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE users ADD COLUMN expiry_date DATETIME")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE users ADD COLUMN last_warning_sent INTEGER DEFAULT -1")
except sqlite3.OperationalError:
    pass

conn.commit()


def add_link(user_id, url, content):
    cursor.execute(
        "INSERT INTO links (user_id, url, last_content) VALUES (?, ?, ?)",
        (user_id, url, content),
    )
    conn.commit()


def get_links():
    cursor.execute("SELECT * FROM links")
    return cursor.fetchall()


def get_active_links():
    cursor.execute(
        """
        SELECT l.id, l.user_id, l.url, l.last_content
        FROM links l
        JOIN users u ON l.user_id = u.user_id
        WHERE u.expiry_date > datetime('now', 'localtime')
    """
    )
    return cursor.fetchall()


def get_user_links(user_id):
    cursor.execute("SELECT * FROM links WHERE user_id=?", (user_id,))
    return cursor.fetchall()


def delete_link(user_id, url):
    cursor.execute("DELETE FROM links WHERE user_id=? AND url=?", (user_id, url))
    deleted = cursor.rowcount
    conn.commit()
    return deleted > 0


def update_content(link_id, content):
    cursor.execute("UPDATE links SET last_content=? WHERE id=?", (content, link_id))
    conn.commit()


def get_user_limit(user_id):
    cursor.execute("SELECT max_links FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        expiry = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (user_id, plan, phone, max_links, expiry_date) VALUES (?, 'free', 'غير متوفر', 1, ?)",
            (user_id, expiry),
        )
        conn.commit()
        return 1


def get_user_expiry(user_id):
    cursor.execute("SELECT expiry_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        return row[0]
    else:
        # Default to 3 days from now if missing
        get_user_limit(user_id)  # ensure user exists
        cursor.execute("SELECT expiry_date FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None


def update_user_limit(user_id, limit):
    get_user_limit(user_id)  # ensure user exists before updating
    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE users SET max_links=?, expiry_date=?, last_warning_sent=-1 WHERE user_id=?",
        (limit, expiry, user_id),
    )
    conn.commit()


def get_user_phone(user_id):
    cursor.execute("SELECT phone FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "غير متوفر"


def update_user_phone(user_id, phone):
    get_user_limit(user_id)  # ensure user exists
    cursor.execute("UPDATE users SET phone=? WHERE user_id=?", (phone, user_id))
    conn.commit()


def get_user_link_count(user_id):
    cursor.execute("SELECT COUNT(*) FROM links WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]


def get_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM links")
    links = cursor.fetchone()[0]
    return users, links


def get_all_users():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]


def get_all_users_expiry():
    cursor.execute(
        "SELECT user_id, expiry_date, last_warning_sent FROM users WHERE expiry_date IS NOT NULL"
    )
    return cursor.fetchall()


def update_last_warning(user_id, warning_level):
    cursor.execute(
        "UPDATE users SET last_warning_sent=? WHERE user_id=?", (warning_level, user_id)
    )
    conn.commit()


def get_users_info():
    cursor.execute(
        """
        SELECT u.user_id, u.max_links, u.phone, u.expiry_date, COUNT(l.id) as link_count
        FROM users u
        LEFT JOIN links l ON u.user_id = l.user_id
        GROUP BY u.user_id
    """
    )
    return cursor.fetchall()
