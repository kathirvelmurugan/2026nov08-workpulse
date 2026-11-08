"""
Unified SDLC Platform — Backend
Python + Flask + SQLite + Qwen Code CLI
"""
import json, os, sqlite3, subprocess, time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app)

DB_PATH = Path(os.environ.get('WORKPULSE_DB', Path(__file__).parent / 'workpulse.db'))
REPO_PATH = os.environ.get('FACTORY_REPO', os.getcwd())
AGENT_TIMEOUT = int(os.environ.get('AGENT_TIMEOUT', '3600'))
PIPELINE_ROLES = ['architect', 'reviewer', 'backend', 'frontend', 'database', 'tests', 'qa']

_NODE = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'nodejs'
_NPM = Path(os.environ.get('APPDATA', '')) / 'npm'
if _NODE.exists(): os.environ['PATH'] = str(_NODE) + os.pathsep + str(_NPM) + os.pathsep + os.environ.get('PATH', '')
os.environ.setdefault('QWEN_CODE_SUPPRESS_YOLO_WARNING', '1')

def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
            description TEXT, project_type TEXT NOT NULL DEFAULT 'internal', client_name TEXT,
            repo_url TEXT, tech_stack TEXT, status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS work_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER REFERENCES projects(id),
            title TEXT NOT NULL, description TEXT NOT NULL, work_type TEXT NOT NULL DEFAULT 'feature',
            status TEXT NOT NULL DEFAULT 'intake', priority TEXT NOT NULL DEFAULT 'medium',
            assigned_to TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')), completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS pipeline_phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT, work_item_id INTEGER NOT NULL REFERENCES work_items(id),
            phase_order INTEGER NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
            started_at TEXT, completed_at TEXT, duration_s REAL, agent_used TEXT,
            tokens_in INTEGER DEFAULT 0, tokens_out INTEGER DEFAULT 0, error_log TEXT,
            UNIQUE(work_item_id, role)
        );
        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, phase_id INTEGER REFERENCES pipeline_phases(id),
            attempt INTEGER NOT NULL DEFAULT 1, agent_cmd TEXT, stdout_summary TEXT,
            stderr_summary TEXT, exit_code INTEGER, duration_s REAL,
            tokens_in INTEGER DEFAULT 0, tokens_out INTEGER DEFAULT 0,
            started_at TEXT NOT NULL DEFAULT (datetime('now')), finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, work_item_id INTEGER NOT NULL REFERENCES work_items(id),
            phase_id INTEGER REFERENCES pipeline_phases(id), author TEXT NOT NULL DEFAULT 'system',
            comment_type TEXT NOT NULL DEFAULT 'note', content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_wi_project ON work_items(project_id);
        CREATE INDEX IF NOT EXISTS idx_ph_wi ON pipeline_phases(work_item_id);
    """)
    db.commit()
    return db

PHASE_PROMPTS = {
    'architect': lambda d: f"ARCHITECT. Create SPEC.md at repo root using write_file. Feature: {d}. Sections: API Contract, DB Schema, File Assignments per role, Shared Types, Acceptance Criteria. Partition so no two agents touch same file. After SPEC.md exists, done.",
    'reviewer': lambda d: f"REVIEWER. Read SPEC.md. Critique the plan. Find gaps, edge cases, security concerns. Write REVIEW.md with APPROVED or REVISION_NEEDED. Do NOT edit code.",
    'backend': lambda d: f"BACKEND dev. Read SPEC.md. Build ALL backend files assigned. API routes, middleware, auth, error handling. Run build+tests+lint. Do NOT touch frontend or DB files.",
    'frontend': lambda d: f"FRONTEND dev. Read SPEC.md and existing implementation. Build ALL frontend files assigned. Connect to backend API. Handle loading, empty, error states. Run build+tests+lint.",
    'database': lambda d: f"DATABASE dev. Read SPEC.md and existing implementation. Build ALL database files assigned. Models, migrations, seed data. Schema must match SPEC.md. Run build+tests+lint.",
    'tests': lambda d: f"TESTS dev. Read SPEC.md and ALL implementation. Write tests covering acceptance criteria. Run all tests. Do NOT edit implementation.",
    'qa': lambda d: f"QA agent. Read SPEC.md and ALL implementation. Do NOT edit code. Check: API matches contract, DB matches, frontend connects, tests cover criteria, no security issues. Report PASS or FAIL with file:line.",
}

# ── API Routes ──

@app.route('/api/heartbeat')
def heartbeat():
    db = get_db()
    phases = {r['status']: r['c'] for r in db.execute("SELECT status, count(*) as c FROM pipeline_phases GROUP BY status").fetchall()}
    items = {r['status']: r['c'] for r in db.execute("SELECT status, count(*) as c FROM work_items GROUP BY status").fetchall()}
    return jsonify({'status': 'ok', 'phases': phases, 'work_items': items})

@app.route('/api/projects', methods=['GET', 'POST'])
def projects():
    if request.method == 'POST':
        d = request.json
        slug = d.get('slug') or d.get('name', '').lower().replace(' ', '-')
        db = get_db()
        db.execute("INSERT INTO projects (name, slug, description, project_type, client_name, repo_url, tech_stack) VALUES (?,?,?,?,?,?,?)",
                   (d['name'], slug, d.get('description'), d.get('project_type', 'internal'), d.get('client_name'), d.get('repo_url'), d.get('tech_stack')))
        db.commit(); return jsonify({'created': True})
    return jsonify([dict(r) for r in get_db().execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()])

@app.route('/api/work-items', methods=['GET', 'POST'])
def work_items():
    if request.method == 'POST':
        d = request.json
        db = get_db()
        cur = db.execute("INSERT INTO work_items (project_id, title, description, work_type, priority, assigned_to) VALUES (?,?,?,?,?,?)",
                         (d.get('project_id'), d['title'], d.get('description', ''), d.get('work_type', 'feature'), d.get('priority', 'medium'), d.get('assigned_to')))
        wi_id = cur.lastrowid
        for i, role in enumerate(PIPELINE_ROLES):
            db.execute("INSERT INTO pipeline_phases (work_item_id, phase_order, role, status) VALUES (?,?,?,?)",
                       (wi_id, i, role, 'queued' if i == 0 else 'blocked'))
        db.execute("INSERT INTO comments (work_item_id, author, comment_type, content) VALUES (?, 'system', 'system_log', ?)",
                   (wi_id, f"Created. Type: {d.get('work_type', 'feature')}. Pipeline: {' → '.join(PIPELINE_ROLES)}"))
        db.commit(); return jsonify({'id': wi_id, 'phases': len(PIPELINE_ROLES)})

    db = get_db()
    sql = "SELECT wi.*, p.name as project_name FROM work_items wi LEFT JOIN projects p ON wi.project_id = p.id WHERE 1=1"
    params = []
    for k in ['project_id', 'work_type', 'status']:
        if request.args.get(k) and request.args.get(k) != 'all':
            sql += f" AND wi.{k} = ?"; params.append(request.args[k])
    sql += " ORDER BY wi.created_at DESC LIMIT 50"
    return jsonify([dict(r) for r in db.execute(sql, params).fetchall()])

@app.route('/api/work-items/<int:wi_id>')
def work_item_detail(wi_id):
    db = get_db()
    wi = db.execute("SELECT wi.*, p.name as project_name FROM work_items wi LEFT JOIN projects p ON wi.project_id = p.id WHERE wi.id = ?", (wi_id,)).fetchone()
    if not wi: return jsonify({'error': 'not found'}), 404
    result = dict(wi)
    result['phases'] = [dict(r) for r in db.execute("SELECT * FROM pipeline_phases WHERE work_item_id = ? ORDER BY phase_order", (wi_id,)).fetchall()]
    result['comments'] = [dict(r) for r in db.execute("SELECT * FROM comments WHERE work_item_id = ? ORDER BY created_at DESC LIMIT 20", (wi_id,)).fetchall()]
    return jsonify(result)

@app.route('/api/pipeline/<int:phase_id>/run', methods=['POST'])
def run_phase(phase_id):
    db = get_db()
    phase = db.execute("SELECT * FROM pipeline_phases WHERE id = ?", (phase_id,)).fetchone()
    if not phase: return jsonify({'error': 'Phase not found'}), 404
    if phase['status'] not in ('queued', 'retrying'): return jsonify({'error': f"Phase is {phase['status']}"}), 400

    wi = db.execute("SELECT * FROM work_items WHERE id = ?", (phase['work_item_id'],)).fetchone()
    db.execute("UPDATE pipeline_phases SET status='in_progress', started_at=datetime('now') WHERE id=?", (phase_id,))
    db.execute("UPDATE work_items SET status=?, updated_at=datetime('now') WHERE id=?", (phase['role'], phase['work_item_id']))
    db.commit()

    try:
        prompt = PHASE_PROMPTS[phase['role']](wi['description'])
        start = time.monotonic()
        result = subprocess.run(['qwen', '-p', prompt, '--output-format', 'json', '--yolo', '--auth-type', 'openai'],
                                cwd=REPO_PATH, capture_output=True, text=True, timeout=AGENT_TIMEOUT + 300)
        duration = time.monotonic() - start

        stdout = (result.stdout or '')[-8000:]
        stderr = (result.stderr or '')[-4000:]
        tokens_in = tokens_out = 0
        for line in (result.stdout or '').split('\n'):
            try:
                obj = json.loads(line.strip())
                if 'usage' in obj:
                    tokens_in += obj['usage'].get('input_tokens', 0)
                    tokens_out += obj['usage'].get('output_tokens', 0)
            except: pass

        db.execute("INSERT INTO agent_runs (phase_id, attempt, agent_cmd, stdout_summary, stderr_summary, exit_code, duration_s, tokens_in, tokens_out, finished_at) VALUES (?,1,'qwen',?,?,?,?,?,?,datetime('now'))",
                   (phase_id, stdout, stderr, result.returncode, round(duration, 1), tokens_in, tokens_out))

        if result.returncode == 0:
            db.execute("UPDATE pipeline_phases SET status='completed', completed_at=datetime('now'), duration_s=?, agent_used='qwen', tokens_in=?, tokens_out=? WHERE id=?",
                       (round(duration, 1), tokens_in, tokens_out, phase_id))
            # Unblock next phase
            next_phase = db.execute("SELECT id FROM pipeline_phases WHERE work_item_id=? AND phase_order=? AND status='blocked'",
                                    (phase['work_item_id'], phase['phase_order'] + 1)).fetchone()
            if next_phase:
                db.execute("UPDATE pipeline_phases SET status='queued' WHERE id=?", (next_phase['id'],))
            else:
                db.execute("UPDATE work_items SET status='done', completed_at=datetime('now'), updated_at=datetime('now') WHERE id=?", (phase['work_item_id'],))

            db.execute("INSERT INTO comments (work_item_id, phase_id, author, comment_type, content) VALUES (?,?,'system','system_log',?)",
                       (phase['work_item_id'], phase_id, f"{phase['role']} completed ({round(duration)}s, {tokens_in}+{tokens_out} tokens)"))
            db.commit()
            return jsonify({'success': True, 'role': phase['role'], 'duration': round(duration), 'tokens_in': tokens_in, 'tokens_out': tokens_out})
        else:
            db.execute("UPDATE pipeline_phases SET status='failed', error_log=? WHERE id=?", (stderr[:2000], phase_id))
            db.commit()
            return jsonify({'error': stderr[:500]}), 500
    except Exception as e:
        db.execute("INSERT INTO agent_runs (phase_id, agent_cmd, stderr_summary, exit_code, duration_s, finished_at) VALUES (?,'qwen',?,1,0,datetime('now'))",
                   (phase_id, str(e)[:4000]))
        db.execute("UPDATE pipeline_phases SET status='failed', error_log=? WHERE id=?", (str(e)[:2000], phase_id))
        db.commit()
        return jsonify({'error': str(e)[:500]}), 500

@app.route('/api/runs')
def runs():
    return jsonify([dict(r) for r in get_db().execute("SELECT * FROM agent_runs ORDER BY id DESC LIMIT 50").fetchall()])

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def fallback(e):
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    init_db()
    print(f"\n  SDLC Platform: http://localhost:8080\n")
    app.run(host='0.0.0.0', port=8080, debug=False)