import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone


class Store:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, history TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS session_state(id TEXT PRIMARY KEY, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, session_id TEXT, order_id TEXT,
                    summary TEXT, created_at TEXT, fingerprint TEXT UNIQUE);
                CREATE TABLE IF NOT EXISTS ticket_issues(session_id TEXT, order_key TEXT, issue_key TEXT,
                    ticket_id TEXT NOT NULL, PRIMARY KEY(session_id, order_key, issue_key));
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        return db

    def new_session(self):
        sid = str(uuid.uuid4())
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES (?, ?)', (sid, '[]'))
        return sid

    def history(self, sid):
        with self.connect() as db:
            row = db.execute('SELECT history FROM sessions WHERE id=?', (sid,)).fetchone()
        if row is None:
            raise ValueError('Unknown session')
        return json.loads(row['history'])

    def state(self, sid):
        self.history(sid)
        with self.connect() as db:
            row = db.execute('SELECT state FROM session_state WHERE id=?', (sid,)).fetchone()
        return json.loads(row['state']) if row else {}

    def save_state(self, sid, state):
        self.history(sid)
        with self.connect() as db:
            db.execute('INSERT INTO session_state VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET state=excluded.state',
                       (sid, json.dumps(state)))

    def save(self, sid, history):
        with self.connect() as db:
            db.execute('UPDATE sessions SET history=? WHERE id=?', (json.dumps(history[-24:]), sid))

    def reset(self, sid):
        self.history(sid)
        with self.connect() as db:
            db.execute('UPDATE sessions SET history=? WHERE id=?', ('[]', sid))
            db.execute('DELETE FROM session_state WHERE id=?', (sid,))

    def ticket(self, sid, summary, order_id=None, issue_key=None):
        self.history(sid)
        summary = summary.strip()
        if not 5 <= len(summary) <= 2000:
            raise ValueError('Ticket summary must contain 5–2000 characters')
        identity = f'{sid}:{order_id}:{issue_key}:' if issue_key else f'{sid}:{order_id}:'
        fp = hashlib.sha256((identity + summary.casefold()).encode()).hexdigest()
        # Explicit issue keys make provider retries and paraphrased requests idempotent.
        issue_key = issue_key or fp
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT ticket_id FROM ticket_issues WHERE session_id=? AND order_key=? AND issue_key=?',
                                  (sid, order_id or '', issue_key)).fetchone()
            reused = existing is not None
            if existing:
                tid = existing['ticket_id']
            else:
                tid = 'ZT-' + uuid.uuid4().hex[:12]
                db.execute('INSERT OR IGNORE INTO tickets VALUES (?,?,?,?,?,?)',
                           (tid, sid, order_id, summary, datetime.now(timezone.utc).isoformat(), fp))
                tid = db.execute('SELECT id FROM tickets WHERE fingerprint=?', (fp,)).fetchone()['id']
                db.execute('INSERT INTO ticket_issues VALUES (?,?,?,?)', (sid, order_id or '', issue_key, tid))
            row = db.execute('SELECT id,order_id,summary,created_at FROM tickets WHERE id=?', (tid,)).fetchone()
        return dict(row, created=True, ticket_id=tid, reused=reused)

    def tickets(self, sid):
        self.history(sid)
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,order_id,summary,created_at FROM tickets WHERE session_id=?', (sid,))]
