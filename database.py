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

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT DEFAULT 'free',
    phone TEXT DEFAULT 'غير متوفر',
    max_links INTEGER DEFAULT 1
)
""")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT 'غير متوفر'")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE users ADD COLUMN max_links INTEGER DEFAULT 1")
except sqlite3.OperationalError:
    pass

conn.commit()


def add_link(user_id, url, content):
    cursor.execute("INSERT INTO links (user_id, url, last_content) VALUES (?, ?, ?)",
                   (user_id, url, content))
    conn.commit()


def get_links():
    cursor.execute("SELECT * FROM links")
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
    cursor.execute("UPDATE links SET last_content=? WHERE id=?",
                   (content, link_id))
    conn.commit()


def get_user_limit(user_id):
    cursor.execute("SELECT max_links FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute("INSERT INTO users (user_id, plan, phone, max_links) VALUES (?, 'free', 'غير متوفر', 1)", (user_id,))
        conn.commit()
        return 1


def update_user_limit(user_id, limit):
    get_user_limit(user_id) # ensure user exists before updating
    cursor.execute("UPDATE users SET max_links=? WHERE user_id=?", (limit, user_id))
    conn.commit()


def get_user_phone(user_id):
    cursor.execute("SELECT phone FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 'غير متوفر'


def update_user_phone(user_id, phone):
    get_user_limit(user_id) # ensure user exists
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


def get_users_info():
    cursor.execute("""
        SELECT u.user_id, u.max_links, u.phone, COUNT(l.id) as link_count
        FROM users u
        LEFT JOIN links l ON u.user_id = l.user_id
        GROUP BY u.user_id
    """)
    return cursor.fetchall()