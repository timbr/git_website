"""
flask_app.py  –  Naphtha Plastics form handler
================================================
Receives POST submissions from the contact and order forms on the
static Pelican site, stores them in SQLite, and exposes a simple
password-protected admin view.

PythonAnywhere setup
--------------------
Point your WSGI file at this module.  Set the three environment
variables below in the PythonAnywhere "Environment variables" panel
(or in a .env file you load manually):

    FLASK_SECRET_KEY   – any long random string
    ADMIN_PASSWORD     – password for /admin
    ALLOWED_ORIGIN     – full origin of the static site, e.g.
                         https://timbr.pythonanywhere.com
                         (used for CORS so the static pages can POST here)
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import (Flask, request, jsonify, g,
                   render_template_string, session, redirect, url_for)

app = Flask(__name__)

# ── configuration ────────────────────────────────────────────────────────────

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-in-production')
ADMIN_PASSWORD  = os.environ.get('ADMIN_PASSWORD',  'change-me-in-production')
ALLOWED_ORIGIN  = os.environ.get('ALLOWED_ORIGIN',  '*')

# SQLite DB lives next to this file on PythonAnywhere
DB_PATH = os.path.join(os.path.dirname(__file__), 'submissions.db')


# ── 301 redirects ─────────────────────────────────────────────────────────────
# Add old-slug → new-slug mappings here whenever a page URL changes.
# Paths are relative to the site root (no leading slash needed on the key).
# Example:
#   'old-page-name/': 'new-page-name/',
REDIRECTS = {
    # 'old-slug/': 'new-slug/',
    'polymers-we-supply': 'blog',
}


@app.route('/<path:old_path>')
def legacy_redirect(old_path):
    target = REDIRECTS.get(old_path) or REDIRECTS.get(old_path + '/')
    if target:
        return redirect('/' + target, code=301)
    return app.make_response(('', 404))


# ── database helpers ─────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS contact_submissions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_at TEXT    NOT NULL,
            firstname   TEXT    NOT NULL,
            lastname    TEXT    NOT NULL,
            email       TEXT    NOT NULL,
            phone       TEXT    NOT NULL,
            message     TEXT    NOT NULL,
            page_url    TEXT
        );

        CREATE TABLE IF NOT EXISTS order_submissions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_at TEXT    NOT NULL,
            firstname   TEXT    NOT NULL,
            lastname    TEXT    NOT NULL,
            email       TEXT    NOT NULL,
            phone       TEXT    NOT NULL,
            postcode    TEXT,
            message     TEXT    NOT NULL,
            page_url    TEXT
        );
    """)
    # Migrate existing databases that pre-date the page_url column
    for table in ('contact_submissions', 'order_submissions'):
        cols = [row[1] for row in db.execute(f'PRAGMA table_info({table})').fetchall()]
        if 'page_url' not in cols:
            db.execute(f'ALTER TABLE {table} ADD COLUMN page_url TEXT')
    db.commit()
    db.close()


# Initialise DB tables on first import
init_db()


# ── CORS helper ───────────────────────────────────────────────────────────────

def add_cors(response):
    response.headers['Access-Control-Allow-Origin']  = ALLOWED_ORIGIN
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.after_request
def apply_cors(response):
    return add_cors(response)


# Handle pre-flight OPTIONS requests for both endpoints
@app.route('/submit/contact', methods=['OPTIONS'])
@app.route('/submit/order',   methods=['OPTIONS'])
def options_handler():
    return add_cors(app.make_default_options_response())


# ── form endpoints ────────────────────────────────────────────────────────────

@app.route('/submit/contact', methods=['POST'])
def submit_contact():
    data = request.form

    firstname = data.get('firstname', '').strip()
    lastname  = data.get('lastname',  '').strip()
    email     = data.get('email',     '').strip()
    phone     = data.get('mobilephone', '').strip()
    message   = data.get('message',   '').strip()
    page_url  = data.get('page_url',  '').strip() or None

    if not all([firstname, lastname, email, phone, message]):
        return jsonify({'ok': False, 'error': 'All fields are required.'}), 400

    db = get_db()
    db.execute(
        """INSERT INTO contact_submissions
           (submitted_at, firstname, lastname, email, phone, message, page_url)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (datetime.utcnow().isoformat(sep=' ', timespec='seconds'),
         firstname, lastname, email, phone, message, page_url)
    )
    db.commit()

    return jsonify({'ok': True, 'message': "Thanks! We'll be in touch shortly."})


@app.route('/submit/order', methods=['POST'])
def submit_order():
    data = request.form

    firstname = data.get('firstname', '').strip()
    lastname  = data.get('lastname',  '').strip()
    email     = data.get('email',     '').strip()
    phone     = data.get('phone',     '').strip()
    postcode  = data.get('postcode',  '').strip()
    message   = data.get('message',   '').strip()
    page_url  = data.get('page_url',  '').strip() or None

    if not all([firstname, lastname, email, phone, message]):
        return jsonify({'ok': False, 'error': 'All fields are required.'}), 400

    db = get_db()
    db.execute(
        """INSERT INTO order_submissions
           (submitted_at, firstname, lastname, email, phone, postcode, message, page_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.utcnow().isoformat(sep=' ', timespec='seconds'),
         firstname, lastname, email, phone, postcode or None, message, page_url)
    )
    db.commit()

    return jsonify({'ok': True, 'message': "Thanks! We'll be in touch shortly."})


# ── admin views ───────────────────────────────────────────────────────────────

ADMIN_LOGIN_HTML = """
<!doctype html>
<title>Admin Login</title>
<style>
  body { font-family: sans-serif; display: flex; justify-content: center;
         padding-top: 80px; background: #f4f4f4; }
  form { background: #fff; padding: 40px; border-radius: 8px;
         box-shadow: 0 2px 8px rgba(0,0,0,.1); min-width: 300px; }
  input { display: block; width: 100%; margin: 10px 0 20px;
          padding: 8px; box-sizing: border-box; font-size: 1rem; }
  button { background: #800080; color: #fff; border: none;
           padding: 10px 24px; font-size: 1rem; cursor: pointer; border-radius: 4px; }
  .error { color: red; margin-bottom: 12px; }
</style>
<form method="post">
  <h2>Admin Login</h2>
  {% if error %}<p class="error">{{ error }}</p>{% endif %}
  <label>Password</label>
  <input type="password" name="password" autofocus>
  <button type="submit">Log in</button>
</form>
"""

ADMIN_HTML = """
<!doctype html>
<title>Naphtha – Form Submissions</title>
<style>
  body { font-family: sans-serif; padding: 30px; background: #f4f4f4; }
  h1   { color: #100030; }
  h2   { color: #800080; margin-top: 40px; }
  table { border-collapse: collapse; width: 100%; background: #fff;
          margin-bottom: 40px; border-radius: 8px; overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }
  th { background: #100030; color: #fff; font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  td.msg { max-width: 400px; white-space: pre-wrap; word-break: break-word; }
  td.url { max-width: 260px; word-break: break-all; font-size: .85rem; }
  .logout { float: right; background: #FF3952; color: #fff; border: none;
            padding: 8px 18px; border-radius: 4px; cursor: pointer;
            font-size: .9rem; text-decoration: none; }
  .none { color: #888; font-style: italic; }
</style>
<h1>Form Submissions <a class="logout" href="{{ url_for('admin_logout') }}">Log out</a></h1>

<h2>Contact Enquiries ({{ contacts|length }})</h2>
{% if contacts %}
<table>
  <tr><th>Date</th><th>Name</th><th>Email</th><th>Phone</th><th>Page</th><th>Message</th></tr>
  {% for r in contacts %}
  <tr>
    <td>{{ r['submitted_at'] }}</td>
    <td>{{ r['firstname'] }} {{ r['lastname'] }}</td>
    <td><a href="mailto:{{ r['email'] }}">{{ r['email'] }}</a></td>
    <td>{{ r['phone'] }}</td>
    <td class="url">{% if r['page_url'] %}<a href="{{ r['page_url'] }}" target="_blank" rel="noopener">{{ r['page_url'] }}</a>{% else %}–{% endif %}</td>
    <td class="msg">{{ r['message'] }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p class="none">No contact submissions yet.</p>
{% endif %}

<h2>Order Requests ({{ orders|length }})</h2>
{% if orders %}
<table>
  <tr><th>Date</th><th>Name</th><th>Email</th><th>Phone</th><th>Postcode</th><th>Page</th><th>Order Request</th></tr>
  {% for r in orders %}
  <tr>
    <td>{{ r['submitted_at'] }}</td>
    <td>{{ r['firstname'] }} {{ r['lastname'] }}</td>
    <td><a href="mailto:{{ r['email'] }}">{{ r['email'] }}</a></td>
    <td>{{ r['phone'] }}</td>
    <td>{{ r['postcode'] or '–' }}</td>
    <td class="url">{% if r['page_url'] %}<a href="{{ r['page_url'] }}" target="_blank" rel="noopener">{{ r['page_url'] }}</a>{% else %}–{% endif %}</td>
    <td class="msg">{{ r['message'] }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p class="none">No order submissions yet.</p>
{% endif %}
"""


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        error = 'Incorrect password.'
    return render_template_string(ADMIN_LOGIN_HTML, error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin():
    db = get_db()
    contacts = db.execute(
        'SELECT * FROM contact_submissions ORDER BY submitted_at DESC'
    ).fetchall()
    orders = db.execute(
        'SELECT * FROM order_submissions ORDER BY submitted_at DESC'
    ).fetchall()
    return render_template_string(ADMIN_HTML, contacts=contacts, orders=orders)


# ── error handlers ────────────────────────────────────────────────────────────

ERROR_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ code }} – Naphtha Plastics</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:Helvetica,Arial,sans-serif;background:#fafafa;
       display:flex;align-items:center;justify-content:center;
       min-height:100vh;padding:40px 20px;text-align:center}
  .wrap{max-width:520px}
  .code{font-size:5rem;font-weight:700;color:#fbc02d;line-height:1;margin-bottom:16px}
  h1{font-size:1.5rem;font-weight:700;color:#100030;text-transform:uppercase;margin-bottom:16px}
  p{color:#555;line-height:1.6;margin-bottom:36px}
  a{display:inline-block;background:#100030;color:#fff;text-decoration:none;
    padding:12px 28px;border-radius:8px;font-weight:600}
  a:hover{background:#fbc02d}
</style>
</head>
<body>
  <div class="wrap">
    <div class="code">{{ code }}</div>
    <h1>{{ title }}</h1>
    <p>{{ message }}</p>
    <a href="/">Back to Home</a>
  </div>
</body>
</html>"""


@app.errorhandler(404)
def not_found(e):
    html = render_template_string(ERROR_HTML,
        code=404,
        title='Page Not Found',
        message='Sorry, the page you were looking for at this URL was not found.')
    return html, 404


@app.errorhandler(500)
def server_error(e):
    html = render_template_string(ERROR_HTML,
        code=500,
        title='Server Error',
        message='Something went wrong on our end. Please try again in a moment.')
    return html, 500


# ── dev entry point ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)
