"""
WorkPulse Backend — All 11 Base44 Entities + Auth + AI Pipeline
Replaces Base44 cloud with local SQLite. Drop-in compatible API.
"""
import hashlib, json, os, sqlite3, subprocess, time, uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app)

DB_PATH = Path(os.environ.get('WORKPULSE_DB', Path(__file__).parent / 'workpulse.db'))
_NODE = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'nodejs'
if _NODE.exists(): os.environ['PATH'] = str(_NODE) + os.pathsep + os.environ.get('PATH', '')
os.environ.setdefault('QWEN_CODE_SUPPRESS_YOLO_WARNING', '1')

def uid(): return str(uuid.uuid4().hex)[:24]
def get_db():
    db = sqlite3.connect(str(DB_PATH)); db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA foreign_keys=ON')
    return db

def init_db():
    db = get_db()
    db.executescript("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, full_name TEXT, password_hash TEXT, role TEXT DEFAULT 'user', is_approved INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, default_theme TEXT DEFAULT 'dark', created_date TEXT DEFAULT (datetime('now')), updated_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS auth_tokens (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token TEXT NOT NULL UNIQUE, created_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, project_type TEXT DEFAULT 'internal', client_name TEXT, description TEXT, github_repo_url TEXT, created_date TEXT DEFAULT (datetime('now')), updated_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, brief TEXT, expected_output TEXT, assigned_to TEXT DEFAULT '[]', project_id TEXT, task_type TEXT DEFAULT 'internal', status TEXT DEFAULT 'floating', blocker TEXT, priority_order INTEGER DEFAULT 0, due_date TEXT, is_important INTEGER DEFAULT 0, is_urgent INTEGER DEFAULT 0, github_repo_url TEXT, created_date TEXT DEFAULT (datetime('now')), updated_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS team_members (id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT, member_status TEXT DEFAULT 'offline', check_in_status TEXT DEFAULT 'checked_out_manual', device_type TEXT, mobile_number TEXT, points_balance INTEGER DEFAULT 1000, show_in_team INTEGER DEFAULT 1, created_date TEXT DEFAULT (datetime('now')), updated_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, started_by TEXT NOT NULL, started_by_name TEXT, started_at TEXT DEFAULT (datetime('now')), ended_at TEXT, state_when_started TEXT, state_when_ended TEXT, actual_output TEXT, had_blocker INTEGER DEFAULT 0, blocker_description TEXT, is_active INTEGER DEFAULT 1, created_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, text TEXT NOT NULL, sent_by TEXT, sent_by_name TEXT, message_type TEXT DEFAULT 'comment', is_pinned INTEGER DEFAULT 0, created_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS notifications (id TEXT PRIMARY KEY, notification_type TEXT NOT NULL, target_member_id TEXT, task_id TEXT, task_title TEXT, from_member_name TEXT, message TEXT, is_read INTEGER DEFAULT 0, created_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS points_ledger (id TEXT PRIMARY KEY, member_id TEXT NOT NULL, event_type TEXT NOT NULL, points_change INTEGER NOT NULL, reason TEXT, category TEXT DEFAULT 'adjustment', balance_after INTEGER, created_date TEXT DEFAULT (datetime('now'))); CREATE TABLE IF NOT EXISTS org_settings (id TEXT PRIMARY KEY, key TEXT NOT NULL UNIQUE, value TEXT, label TEXT, created_date TEXT DEFAULT (datetime('now'))); CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
    db.commit()
    return db

def _auth(req):
    token = req.headers.get('Authorization','').replace('Bearer ','')
    if not token: return None
    row = get_db().execute("SELECT u.* FROM auth_tokens t JOIN users u ON t.user_id=u.id WHERE t.token=?", (token,)).fetchone()
    return dict(row) if row else None

@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.json; db = get_db()
    if db.execute("SELECT id FROM users WHERE email=?", (d['email'],)).fetchone(): return jsonify({'error': 'Email exists'}), 400
    pw = hashlib.sha256(d['password'].encode()).hexdigest(); id = uid()
    db.execute("INSERT INTO users (id,email,full_name,password_hash,role,is_approved) VALUES (?,?,?,?,?,1)", (id, d['email'], d.get('full_name',''), pw, d.get('role','user')))
    db.commit(); return jsonify({'id': id, 'email': d['email']})

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.json; db = get_db()
    pw = hashlib.sha256(d['password'].encode()).hexdigest()
    user = db.execute("SELECT * FROM users WHERE email=? AND password_hash=?", (d['email'], pw)).fetchone()
    if not user: return jsonify({'error': 'Invalid credentials'}), 401
    token = hashlib.sha256(f"{user['id']}{time.time()}".encode()).hexdigest()
    db.execute("INSERT INTO auth_tokens (id,user_id,token) VALUES (?,?,?)", (uid(), user['id'], token))
    db.commit(); return jsonify({'access_token': token, 'user': {k: user[k] for k in ['id','email','full_name','role','is_approved']}})

@app.route('/api/auth/me')
def me():
    u = _auth(request); return jsonify(u) if u else (jsonify({'error': 'Unauthorized'}), 401)

@app.route('/api/tasks', methods=['GET','POST'])
def tasks():
    db = get_db()
    if request.method == 'POST':
        d = request.json; id = uid()
        db.execute("INSERT INTO tasks (id,title,brief,expected_output,assigned_to,project_id,task_type,status,priority_order,due_date,github_repo_url) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (id, d['title'], d.get('brief',''), d.get('expected_output',''), json.dumps(d.get('assigned_to',[])), d.get('project_id'), d.get('task_type','internal'), d.get('status','floating'), d.get('priority_order',0), d.get('due_date'), d.get('github_repo_url','')))
        db.execute("INSERT INTO messages (id,task_id,text,sent_by_name,message_type) VALUES (?,?,?,?,?)", (uid(), id, f"Task created: {d['title']}", 'System', 'system_log'))
        db.commit(); return jsonify({'id': id})
    sql = "SELECT * FROM tasks WHERE 1=1"; params = []
    for f in ['status','project_id','task_type']:
        if request.args.get(f): sql += f" AND {f}=?"; params.append(request.args[f])
    if request.args.get('search'): sql += " AND (title LIKE ? OR brief LIKE ?)"; params.extend([f"%{request.args['search']}%"]*2)
    sql += " ORDER BY priority_order ASC, created_date DESC LIMIT 50"
    rows = [dict(r) for r in db.execute(sql, params).fetchall()]
    for r in rows:
        try: r['assigned_to'] = json.loads(r['assigned_to'])
        except: r['assigned_to'] = []
    return jsonify(rows)

@app.route('/api/tasks/<id>', methods=['GET','PATCH'])
def task_detail(id):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id=?", (id,)).fetchone()
    if not task: return jsonify({'error': 'Not found'}), 404
    if request.method == 'GET':
        d = dict(task)
        try: d['assigned_to'] = json.loads(d['assigned_to'])
        except: d['assigned_to'] = []
        d['messages'] = [dict(r) for r in db.execute("SELECT * FROM messages WHERE task_id=? ORDER BY created_date DESC LIMIT 50", (id,)).fetchall()]
        d['sessions'] = [dict(r) for r in db.execute("SELECT * FROM sessions WHERE task_id=? ORDER BY started_at DESC LIMIT 20", (id,)).fetchall()]
        return jsonify(d)
    d = request.json; sets = []; params = []
    for k in ['title','brief','status','priority_order','expected_output','blocker','due_date','assigned_to']:
        if k in d: sets.append(f"{k}=?"); params.append(json.dumps(d[k]) if isinstance(d[k],list) else d[k])
    if sets: params.append(id); db.execute(f"UPDATE tasks SET {', '.join(sets)}, updated_date=datetime('now') WHERE id=?", params); db.commit()
    return jsonify({'updated': True})

@app.route('/api/projects', methods=['GET','POST'])
def projects():
    db = get_db()
    if request.method == 'POST':
        d = request.json; id = uid()
        db.execute("INSERT INTO projects (id,name,project_type,client_name,description,github_repo_url) VALUES (?,?,?,?,?,?)", (id, d['name'], d.get('project_type','internal'), d.get('client_name',''), d.get('description',''), d.get('github_repo_url','')))
        db.commit(); return jsonify({'id': id})
    return jsonify([dict(r) for r in db.execute("SELECT * FROM projects ORDER BY created_date DESC").fetchall()])

@app.route('/api/team', methods=['GET','POST'])
def team():
    db = get_db()
    if request.method == 'POST':
        d = request.json; id = uid()
        db.execute("INSERT INTO team_members (id,name,role,member_status) VALUES (?,?,?,?)", (id, d['name'], d.get('role',''), d.get('member_status','offline')))
        db.commit(); return jsonify({'id': id})
    return jsonify([dict(r) for r in db.execute("SELECT * FROM team_members ORDER BY name").fetchall()])

@app.route('/api/messages', methods=['POST'])
def messages():
    d = request.json; db = get_db(); id = uid()
    db.execute("INSERT INTO messages (id,task_id,text,sent_by,sent_by_name,message_type) VALUES (?,?,?,?,?,?)", (id, d['task_id'], d['text'], d.get('sent_by',''), d.get('sent_by_name',''), d.get('message_type','comment')))
    db.commit(); return jsonify({'id': id})

@app.route('/api/sessions', methods=['POST'])
def sessions():
    d = request.json; db = get_db(); id = uid()
    db.execute("INSERT INTO sessions (id,task_id,started_by,started_by_name,state_when_started,is_active) VALUES (?,?,?,?,?,1)", (id, d['task_id'], d['started_by'], d.get('started_by_name',''), d.get('state_when_started','')))
    db.commit(); return jsonify({'id': id})

@app.route('/api/notifications', methods=['GET'])
def notifications():
    db = get_db()
    member_id = request.args.get('member_id')
    sql = "SELECT * FROM notifications WHERE 1=1"; params = []
    if member_id: sql += " AND target_member_id=?"; params.append(member_id)
    return jsonify([dict(r) for r in db.execute(sql, params).fetchall()])

@app.route('/api/settings', methods=['GET','POST'])
def settings():
    db = get_db()
    if request.method == 'POST':
        d = request.json
        db.execute("INSERT OR REPLACE INTO org_settings (id,key,value,label) VALUES (?,?,?,?)", (uid(), d['key'], d['value'], d.get('label','')))
        db.commit(); return jsonify({'saved': True})
    return jsonify([dict(r) for r in db.execute("SELECT * FROM org_settings").fetchall()])

PIPELINE_ROLES = ['architect','reviewer','backend','frontend','database','tests','qa']

@app.route('/api/pipeline/run/<task_id>/<role>', methods=['POST'])
def run_pipeline(task_id, role):
    if role not in PIPELINE_ROLES: return jsonify({'error': 'Unknown role'}), 400
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task: return jsonify({'error': 'Task not found'}), 404
    prompts = {
        'architect': f"ARCHITECT. Create SPEC.md using write_file. Task: {task['title']}. {task.get('expected_output','')}",
        'reviewer': "REVIEWER. Read SPEC.md. Write REVIEW.md.",
        'backend': "BACKEND. Build API routes per SPEC.md. Run tests.",
        'frontend': "FRONTEND. Build components per SPEC.md. Run tests.",
        'database': "DATABASE. Build schema per SPEC.md. Run tests.",
        'tests': "TESTS. Write tests per SPEC.md. Run all tests.",
        'qa': "QA. Review against SPEC.md. Report PASS or FAIL.",
    }
    repo = task['github_repo_url'] or os.environ.get('FACTORY_REPO', os.getcwd())
    try:
        start = time.monotonic()
        r = subprocess.run(['qwen','-p',prompts[role],'--output-format','json','--yolo','--auth-type','openai'], cwd=repo, capture_output=True, text=True, timeout=3600)
        dur = round(time.monotonic()-start, 1)
        tokens = 0
        for l in (r.stdout or '').split('\n'):
            try: tokens += json.loads(l.strip()).get('usage',{}).get('total_tokens',0)
            except: pass
        db.execute("INSERT INTO messages (id,task_id,text,sent_by_name,message_type) VALUES (?,?,?,?,?)", (uid(), task_id, f"[{role}] done in {dur}s ({tokens} tokens)", 'AI Factory', 'system_log'))
        db.commit()
        return jsonify({'success': True, 'role': role, 'duration': dur, 'tokens': tokens})
    except Exception as e:
        return jsonify({'error': str(e)[:500]})

@app.route('/')
def index(): return send_from_directory(app.static_folder, 'index.html')
@app.errorhandler(404)
def fallback(e): return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    init_db()
    print("\n  WorkPulse Backend: http://localhost:8080\n")
    app.run(host='0.0.0.0', port=8080, debug=False)