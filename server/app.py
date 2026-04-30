"""
Precision HCC — Semiconductor Ops Guide
Backend Server (Flask + SQLite)
"""
import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(BASE_DIR)
DB_PATH    = os.path.join(ROOT_DIR, 'db', 'precision_ops.db')
PUBLIC_DIR = os.path.join(ROOT_DIR, 'public')
SECRET_KEY = os.environ.get('SECRET_KEY', 'precision-hcc-change-in-production-2024')
TOKEN_HOURS = 72

app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path='')
app.config['SECRET_KEY'] = SECRET_KEY
CORS(app, supports_credentials=True)

# ── Database ────────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE NOT NULL,
            name        TEXT    NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'member',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            last_login  TEXT
        );

        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            cap_id      INTEGER NOT NULL,
            item_key    TEXT    NOT NULL,
            done        INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, item_key)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_key    TEXT    NOT NULL,
            note        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_progress_user  ON progress(user_id);
        CREATE INDEX IF NOT EXISTS idx_progress_item  ON progress(item_key);
        CREATE INDEX IF NOT EXISTS idx_notes_item     ON notes(item_key);
        """)
        db.commit()

# ── Auth helpers ────────────────────────────────────────────────────────────
def make_token(user_id, role):
    payload = {
        'sub':  user_id,
        'role': role,
        'exp':  datetime.utcnow() + timedelta(hours=TOKEN_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            g.user_id = data['sub']
            g.user_role = data['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if g.user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ─────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email    = (data.get('email')    or '').strip().lower()
    name     = (data.get('name')     or '').strip()
    password = (data.get('password') or '').strip()
    invite   = (data.get('invite')   or '').strip()

    # Simple invite code to prevent open registration
    INVITE_CODE = os.environ.get('INVITE_CODE', 'precision2024')
    if invite != INVITE_CODE:
        return jsonify({'error': 'Invalid invite code'}), 403

    if not email or not name or not password:
        return jsonify({'error': 'Email, name, and password required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # First user becomes admin
    count = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    role = 'admin' if count == 0 else 'member'

    hashed = generate_password_hash(password)
    cur = db.execute(
        'INSERT INTO users (email, name, password, role) VALUES (?,?,?,?)',
        (email, name, hashed, role)
    )
    db.commit()
    user_id = cur.lastrowid
    token = make_token(user_id, role)
    return jsonify({'token': token, 'name': name, 'role': role, 'id': user_id}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data     = request.get_json() or {}
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    db.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user['id'],))
    db.commit()
    token = make_token(user['id'], user['role'])
    return jsonify({
        'token': token,
        'name':  user['name'],
        'role':  user['role'],
        'id':    user['id']
    })

@app.route('/api/auth/me', methods=['GET'])
@token_required
def me():
    db   = get_db()
    user = db.execute('SELECT id,name,email,role,created_at,last_login FROM users WHERE id=?',
                      (g.user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))

# ── Progress routes ──────────────────────────────────────────────────────────
@app.route('/api/progress', methods=['GET'])
@token_required
def get_progress():
    db   = get_db()
    rows = db.execute(
        'SELECT item_key, done, updated_at FROM progress WHERE user_id=?',
        (g.user_id,)
    ).fetchall()
    return jsonify({r['item_key']: {'done': bool(r['done']), 'updated_at': r['updated_at']}
                    for r in rows})

@app.route('/api/progress', methods=['POST'])
@token_required
def save_progress():
    data     = request.get_json() or {}
    item_key = data.get('item_key', '').strip()
    done     = bool(data.get('done', False))
    cap_id   = int(data.get('cap_id', 0))

    if not item_key:
        return jsonify({'error': 'item_key required'}), 400

    db = get_db()
    db.execute("""
        INSERT INTO progress (user_id, cap_id, item_key, done, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id, item_key) DO UPDATE SET
            done=excluded.done,
            updated_at=excluded.updated_at
    """, (g.user_id, cap_id, item_key, 1 if done else 0))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/progress/bulk', methods=['POST'])
@token_required
def bulk_progress():
    """Save multiple items at once (initial sync)"""
    items = request.get_json() or []
    db    = get_db()
    for item in items:
        key    = (item.get('item_key') or '').strip()
        done   = bool(item.get('done', False))
        cap_id = int(item.get('cap_id', 0))
        if not key: continue
        db.execute("""
            INSERT INTO progress (user_id, cap_id, item_key, done, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, item_key) DO UPDATE SET
                done=excluded.done, updated_at=excluded.updated_at
        """, (g.user_id, cap_id, 1 if done else 0, 1 if done else 0))
    db.commit()
    return jsonify({'ok': True})

# ── Notes routes ─────────────────────────────────────────────────────────────
@app.route('/api/notes/<item_key>', methods=['GET'])
@token_required
def get_notes(item_key):
    db   = get_db()
    rows = db.execute("""
        SELECT n.id, n.note, n.created_at, u.name as author
        FROM notes n
        JOIN users u ON u.id = n.user_id
        WHERE n.item_key=?
        ORDER BY n.created_at DESC
    """, (item_key,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/notes', methods=['POST'])
@token_required
def add_note():
    data     = request.get_json() or {}
    item_key = (data.get('item_key') or '').strip()
    note     = (data.get('note')     or '').strip()
    if not item_key or not note:
        return jsonify({'error': 'item_key and note required'}), 400
    db = get_db()
    cur = db.execute(
        'INSERT INTO notes (user_id, item_key, note) VALUES (?,?,?)',
        (g.user_id, item_key, note)
    )
    db.commit()
    row = db.execute("""
        SELECT n.id, n.note, n.created_at, u.name as author
        FROM notes n JOIN users u ON u.id=n.user_id
        WHERE n.id=?
    """, (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@token_required
def delete_note(note_id):
    db   = get_db()
    note = db.execute('SELECT user_id FROM notes WHERE id=?', (note_id,)).fetchone()
    if not note:
        return jsonify({'error': 'Not found'}), 404
    if note['user_id'] != g.user_id and g.user_role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    db.execute('DELETE FROM notes WHERE id=?', (note_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Admin routes ─────────────────────────────────────────────────────────────
@app.route('/api/admin/team', methods=['GET'])
@admin_required
def admin_team():
    db    = get_db()
    users = db.execute(
        'SELECT id, name, email, role, created_at, last_login FROM users ORDER BY name'
    ).fetchall()
    result = []
    for u in users:
        # Get progress summary per capability
        caps = db.execute("""
            SELECT cap_id, COUNT(*) as total, SUM(done) as done_count
            FROM progress WHERE user_id=?
            GROUP BY cap_id
        """, (u['id'],)).fetchall()
        cap_summary = {r['cap_id']: {'total': r['total'], 'done': r['done_count']} for r in caps}
        result.append({**dict(u), 'cap_progress': cap_summary})
    return jsonify(result)

@app.route('/api/admin/progress/<int:user_id>', methods=['GET'])
@admin_required
def admin_user_progress(user_id):
    db   = get_db()
    rows = db.execute(
        'SELECT item_key, done, updated_at FROM progress WHERE user_id=?', (user_id,)
    ).fetchall()
    return jsonify({r['item_key']: {'done': bool(r['done']), 'updated_at': r['updated_at']}
                    for r in rows})

@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_role(user_id):
    role = (request.get_json() or {}).get('role', '')
    if role not in ('admin', 'member'):
        return jsonify({'error': 'Role must be admin or member'}), 400
    db = get_db()
    db.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == g.user_id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    db        = get_db()
    total_u   = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    total_chk = db.execute('SELECT COUNT(*) as c FROM progress WHERE done=1').fetchone()['c']
    recent    = db.execute("""
        SELECT u.name, p.item_key, p.updated_at
        FROM progress p JOIN users u ON u.id=p.user_id
        WHERE p.done=1
        ORDER BY p.updated_at DESC LIMIT 10
    """).fetchall()
    return jsonify({
        'total_users':   total_u,
        'total_checked': total_chk,
        'recent':        [dict(r) for r in recent]
    })

# ── Serve frontend ────────────────────────────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(PUBLIC_DIR, path)):
        return send_from_directory(PUBLIC_DIR, path)
    return send_from_directory(PUBLIC_DIR, 'index.html')

# ── Boot ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    print(f"\n  Precision Ops Guide running on http://localhost:{port}")
    print(f"  Invite code: {os.environ.get('INVITE_CODE', 'precision2024')}\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
