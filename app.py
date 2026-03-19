"""
CodeGenie - AI Code Generator Backend
Flask application with SQLite database + Hugging Face integration
"""

# ── Load .env FIRST, before anything else reads os.getenv ────────────────────
from dotenv import load_dotenv
load_dotenv()   # reads .env file in the same folder automatically

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "codegenie-secret-change-in-production")
CORS(app, supports_credentials=True)

# ─── SQLite Database Configuration ───────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'codegenie.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(120), nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    password       = db.Column(db.String(256), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    last_active    = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin       = db.Column(db.Boolean, default=False)
    feedback_count = db.Column(db.Integer, default=0)   # counts feedbacks given (max 15 tracked)
    is_verified    = db.Column(db.Boolean, default=False)  # True once feedback_count >= 10


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id         = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    user_name  = db.Column(db.String(120), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)
    message    = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False, index=True)
    action     = db.Column(db.String(64), nullable=False)
    language   = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Snippet(db.Model):
    __tablename__ = 'snippets'

    id         = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False, index=True)
    prompt     = db.Column(db.Text, nullable=False)
    code       = db.Column(db.Text, nullable=False)
    output     = db.Column(db.Text, nullable=True)
    language   = db.Column(db.String(32), nullable=False, default="plaintext")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# Create tables + seed accounts
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='demo@codegenie.dev').first():
        db.session.add(User(
            name='Demo User',
            email='demo@codegenie.dev',
            password=generate_password_hash('Demo2024!')
        ))
        logger.info("Demo account created: demo@codegenie.dev / Demo2024!")
    if not User.query.filter_by(email='admin@codegenie.dev').first():
        db.session.add(User(
            name='Admin',
            email='admin@codegenie.dev',
            password=generate_password_hash('Admin2024!'),
            is_admin=True
        ))
        logger.info("Admin account created: admin@codegenie.dev / Admin2024!")
    db.session.commit()

# ─── Helpers ─────────────────────────────────────────────────────────────────
def log_activity(email, action, language=None):
    try:
        db.session.add(ActivityLog(user_email=email, action=action, language=language))
        user = User.query.filter_by(email=email).first()
        if user:
            user.last_active = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        logger.error(f"Activity log error: {e}")
        db.session.rollback()


# ─── Hugging Face Configuration ───────────────────────────────────────────────
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "").strip()

if HUGGINGFACE_API_TOKEN:
    logger.info(f"✅ HuggingFace token loaded: {HUGGINGFACE_API_TOKEN[:8]}…")
else:
    logger.warning("⚠️  HUGGINGFACE_API_TOKEN not set — create a .env file (see SETUP.md)")

# ============= Routes =============

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/homepage')
def homepage():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('homepage.html', user=session['user'])


@app.route('/admin')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))
    if not session['user'].get('is_admin'):
        return redirect(url_for('homepage'))
    return render_template('admin.html', user=session['user'])


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))

    user = session['user']
    snippets = (Snippet.query
                .filter_by(user_email=user['email'])
                .order_by(Snippet.created_at.desc())
                .limit(50)
                .all())
    return render_template('dashboard.html', user=user, snippets=snippets)

# ─── NEW: token status endpoint so the frontend can warn the user ─────────────
@app.route('/api/status')
def api_status():
    return jsonify({
        'api_token_configured': bool(HUGGINGFACE_API_TOKEN),
        'demo_mode': not bool(HUGGINGFACE_API_TOKEN)
    })

# ============= API Endpoints =============

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data     = request.json
        email    = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user'] = {
                'email':          user.email,
                'name':           user.name,
                'is_admin':       bool(user.is_admin),
                'is_verified':    bool(user.is_verified),
                'feedback_count': user.feedback_count or 0,
            }
            log_activity(email, 'login')
            logger.info(f"Login OK: {email}")
            return jsonify({
                'success':        True,
                'message':        'Login successful',
                'user':           session['user'],
                'is_admin':       bool(user.is_admin),
                'is_verified':    bool(user.is_verified),
                'feedback_count': user.feedback_count or 0,
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred during login'}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user' in session:
        log_activity(session['user']['email'], 'logout')
    session.pop('user', None)
    return jsonify({'success': True, 'message': 'Logged out'})


@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data     = request.json
        name     = data.get('name', '').strip()
        email    = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not all([name, email, password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'message': 'Please enter a valid email address'}), 400
        if len(password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'}), 400

        db.session.add(User(name=name, email=email, password=generate_password_hash(password)))
        db.session.commit()
        logger.info(f"Signup OK: {email}")
        return jsonify({'success': True, 'message': 'Account created successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Signup error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An error occurred during registration'}), 500


@app.route('/api/generate', methods=['POST'])
def generate_code():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data     = request.json
        prompt   = data.get('prompt', '').strip()
        language = data.get('language', 'python')

        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        log_activity(session['user']['email'], 'generate', language)
        generated_code, explanation = call_huggingface_api(prompt, language)
        is_demo = generated_code.startswith('# Task:') or generated_code.startswith('// Task:')

        return jsonify({
            'success': True,
            'code': generated_code,
            'explanation': explanation,
            'language': language,
            'is_demo': is_demo,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to generate code. Please try again.'}), 500


@app.route('/api/snippets', methods=['POST'])
def save_snippet():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        data     = request.json or {}
        prompt   = (data.get('prompt') or '').strip()
        code     = (data.get('code') or '').strip()
        output   = (data.get('output') or '').strip()
        language = (data.get('language') or 'plaintext').strip() or 'plaintext'

        if not prompt or not code:
            return jsonify({'success': False, 'message': 'Prompt and code are required.'}), 400

        snippet = Snippet(
            user_email=session['user']['email'],
            prompt=prompt,
            code=code,
            output=output,
            language=language,
        )
        db.session.add(snippet)
        db.session.commit()

        log_activity(session['user']['email'], 'save', language)
        return jsonify({'success': True, 'message': 'Saved to dashboard.', 'id': snippet.id})
    except Exception as e:
        logger.error(f"Save snippet error: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to save snippet.'}), 500

# ============= Hugging Face Helper =============

def call_huggingface_api(prompt: str, language: str = 'python') -> tuple:
    """
    Calls the Hugging Face Router (OpenAI-compatible API).
    Returns (code, explanation) where explanation is 3-4 simple lines.
    """
    if not HUGGINGFACE_API_TOKEN:
        logger.warning("No token — demo mode")
        return get_demo_code(prompt, language), get_demo_explanation(prompt, language)

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    lang_label = "C" if language == "c" else language.capitalize()
    models = [
        "Qwen/Qwen2.5-Coder-7B-Instruct",
        "Qwen/Qwen2.5-Coder-32B-Instruct",
    ]

    for model in models:
        url = "https://router.huggingface.co/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are CodeGenie, an expert coding assistant. "
                        "Reply in this exact format only — no markdown code blocks:\n\n"
                        "CODE:\n<complete runnable code>\n\n"
                        "EXPLANATION:\n<2 to 4 short, simple lines in plain English explaining what the code does>"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Write complete, working {lang_label} code for the following task.\n\n"
                        f"Task: {prompt}\n\n"
                        f"Output in this format:\nCODE:\n<your code>\n\nEXPLANATION:\n<2-4 simple lines>"
                    ),
                },
            ],
            "max_tokens": 600,
            "temperature": 0.2,
            "top_p": 0.95,
        }

        try:
            logger.info(f"Trying model (chat-completions): {model}")
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.debug(f"  status={resp.status_code}  body={resp.text[:200]}")

            if resp.status_code == 200:
                result = resp.json()
                try:
                    raw = result["choices"][0]["message"]["content"]
                except Exception:
                    raw = str(result)

                code, explanation = _parse_code_and_explanation(raw)
                code = _strip_fences(code)

                if code and len(code) > 10:
                    logger.info(f"✅ Got code from {model} ({len(code)} chars)")
                    return code, (explanation or "Generated code for your task.")
                logger.warning(f"  Empty/short response from {model}, trying next…")

            elif resp.status_code == 401:
                logger.error("  401 — token rejected. Check HUGGINGFACE_API_TOKEN in .env")
                err_msg = (
                    f"# ❌ Token rejected (401).\n"
                    f"# Your token was read but HuggingFace says it is invalid.\n"
                    f"# Steps:\n"
                    f"#   1. Go to https://huggingface.co/settings/tokens\n"
                    f"#   2. Delete the old token and create a NEW one (role: Read)\n"
                    f"#   3. Paste the new token in your .env file\n"
                    f"#   4. Restart the app\n\n"
                    f"# Prompt: {prompt}"
                )
                return err_msg, "Token invalid. Update HUGGINGFACE_API_TOKEN in .env and restart."

            elif resp.status_code == 403:
                logger.warning(f"  403 on {model} — no access, trying next…")
                continue

            elif resp.status_code == 404:
                logger.warning(f"  404 on {model} — model not found at router, trying next…")
                continue

            elif resp.status_code == 429:
                logger.warning(f"  429 on {model} — rate limited, trying next…")
                continue

            elif resp.status_code == 503:
                logger.warning(f"  503 on {model} — service unavailable, trying next…")
                continue

            else:
                logger.warning(f"  {resp.status_code}: {resp.text[:300]}")

        except requests.exceptions.Timeout:
            logger.warning(f"  {model} timed out after 60s, trying next…")
        except Exception as e:
            logger.warning(f"  {model} error: {e}")

    logger.warning("All models failed — returning demo code")
    return get_demo_code(prompt, language), get_demo_explanation(prompt, language)


def _parse_code_and_explanation(raw: str) -> tuple:
    """Parse model output into code and explanation using CODE: and EXPLANATION: markers."""
    code, explanation = "", ""
    raw = (raw or "").strip()
    rlower = raw.lower()

    if "explanation:" in rlower:
        idx = rlower.index("explanation:")
        before_expl = raw[:idx].strip()
        explanation = raw[idx + 11:].strip()
        if "code:" in before_expl.lower():
            cidx = before_expl.lower().index("code:")
            code = before_expl[cidx + 5:].strip()
        else:
            code = before_expl
    elif "code:" in rlower:
        cidx = rlower.index("code:")
        code = raw[cidx + 5:].strip()
    else:
        code = raw

    lines = [l.strip() for l in explanation.split("\n") if l.strip()]
    if lines and lines[0].rstrip(":").lower() == "explanation":
        lines = lines[1:]
    explanation = "\n".join(lines)[:500].strip()
    if explanation and explanation.startswith(":"):
        explanation = explanation.lstrip(":").strip()
    return code.strip(), explanation if explanation else ""


def _strip_fences(code: str) -> str:
    """Strip markdown ```lang ... ``` fences if model included them."""
    lines = code.split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def get_demo_explanation(prompt: str, language: str) -> str:
    """Short explanation stub when in demo mode."""
    return (
        "Demo mode: no API token set. "
        "Add HUGGINGFACE_API_TOKEN to your .env to get real code and explanations."
    )


def get_demo_code(prompt: str, language: str) -> str:
    """Stub returned when token is missing."""
    demos = {
        'python': f'''# Task: {prompt}
# ⚠️  DEMO MODE — set HUGGINGFACE_API_TOKEN in .env to get real AI-generated code.
# See SETUP.md for instructions.

def solution():
    """Implementation for: {prompt}"""
    # TODO: implement
    pass

if __name__ == "__main__":
    print(solution())
''',
        'javascript': f'''// Task: {prompt}
// ⚠️  DEMO MODE — set HUGGINGFACE_API_TOKEN in .env to get real AI-generated code.

function solution() {{
    // TODO: {prompt}
}}

console.log(solution());
''',
        'java': f'''// Task: {prompt}
// ⚠️  DEMO MODE — set HUGGINGFACE_API_TOKEN in .env to get real AI-generated code.

public class Solution {{
    public static void main(String[] args) {{
        // TODO: {prompt}
    }}
}}
''',
        'cpp': f'''// Task: {prompt}
// ⚠️  DEMO MODE — set HUGGINGFACE_API_TOKEN in .env to get real AI-generated code.

#include <iostream>
using namespace std;

int main() {{
    // TODO: {prompt}
    return 0;
}}
''',
        'c': f'''// Task: {prompt}
// ⚠️  DEMO MODE — set HUGGINGFACE_API_TOKEN in .env to get real AI-generated code.

#include <stdio.h>

int main(void) {{
    // TODO: {prompt}
    return 0;
}}
''',
    }
    return demos.get(language, f"# Task: {prompt}\n# Set HUGGINGFACE_API_TOKEN for AI generation")

# ============= Code Runner =============

@app.route('/api/run', methods=['POST'])
def run_code():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    import subprocess, tempfile, os, sys, shutil

    data     = request.json
    code     = data.get('code', '').strip()
    language = data.get('language', 'python')
    stdin    = data.get('stdin', '')   # user-provided console input

    if not code:
        return jsonify({'success': False, 'error': 'No code to run'}), 400

    try:
        if language == 'python':
            with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False, encoding='utf-8') as f:
                f.write(code); fname = f.name
            result = subprocess.run(
                [sys.executable, fname],
                input=stdin, capture_output=True, text=True, timeout=10
            )
            os.unlink(fname)

        elif language == 'javascript':
            if not shutil.which('node'):
                return jsonify({'success': False, 'error': 'Node.js is not installed on this server.'})
            with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False, encoding='utf-8') as f:
                f.write(code); fname = f.name
            result = subprocess.run(
                ['node', fname],
                input=stdin, capture_output=True, text=True, timeout=10
            )
            os.unlink(fname)

        elif language in ('c', 'cpp'):
            compiler = 'g++' if language == 'cpp' else 'gcc'
            if not shutil.which(compiler):
                return jsonify({'success': False, 'error': f'{compiler} is not installed on this server.'})
            with tempfile.NamedTemporaryFile(suffix='.cpp' if language == 'cpp' else '.c',
                                             mode='w', delete=False, encoding='utf-8') as f:
                f.write(code); src = f.name
            out_bin = src + '.out'
            compile_result = subprocess.run(
                [compiler, src, '-o', out_bin],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(src)
            if compile_result.returncode != 0:
                return jsonify({'success': True, 'stdout': '', 'stderr': compile_result.stderr, 'exit_code': compile_result.returncode})
            result = subprocess.run(
                [out_bin],
                input=stdin, capture_output=True, text=True, timeout=10
            )
            os.unlink(out_bin)

        elif language == 'java':
            if not shutil.which('javac'):
                return jsonify({'success': False, 'error': 'Java (javac) is not installed on this server.'})
            import re
            class_match = re.search(r'public\s+class\s+(\w+)', code)
            class_name  = class_match.group(1) if class_match else 'Solution'
            tmpdir = tempfile.mkdtemp()
            src = os.path.join(tmpdir, f'{class_name}.java')
            with open(src, 'w', encoding='utf-8') as f:
                f.write(code)
            compile_result = subprocess.run(
                ['javac', src],
                capture_output=True, text=True, timeout=15
            )
            if compile_result.returncode != 0:
                shutil.rmtree(tmpdir, ignore_errors=True)
                return jsonify({'success': True, 'stdout': '', 'stderr': compile_result.stderr, 'exit_code': compile_result.returncode})
            result = subprocess.run(
                ['java', '-cp', tmpdir, class_name],
                input=stdin, capture_output=True, text=True, timeout=10
            )
            shutil.rmtree(tmpdir, ignore_errors=True)

        else:
            return jsonify({'success': False, 'error': f'Run not supported for {language}.'})

        return jsonify({
            'success':   True,
            'stdout':    result.stdout,
            'stderr':    result.stderr,
            'exit_code': result.returncode,
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Execution timed out (10s limit).'})
    except Exception as e:
        logger.error(f"Run error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


# ─── Feedback ────────────────────────────────────────────────────────────────
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        data    = request.json or {}
        rating  = int(data.get('rating', 0))
        message = (data.get('message') or '').strip()

        if not 1 <= rating <= 5:
            return jsonify({'success': False, 'message': 'Rating must be 1-5'}), 400

        email = session['user']['email']
        user  = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        # Only count feedback up to 15 times
        if user.feedback_count < 15:
            db.session.add(Feedback(
                user_email=email,
                user_name=user.name,
                rating=rating,
                message=message
            ))
            user.feedback_count = (user.feedback_count or 0) + 1
            # Verify once count hits 10
            if user.feedback_count >= 10 and not user.is_verified:
                user.is_verified = True
                logger.info(f"User {email} is now VERIFIED (10 feedbacks given)")
            # Update session
            session['user']['feedback_count'] = user.feedback_count
            session['user']['is_verified']    = bool(user.is_verified)
            session.modified = True
            db.session.commit()

        return jsonify({
            'success':        True,
            'feedback_count': user.feedback_count,
            'is_verified':    bool(user.is_verified),
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Feedback error: {e}")
        return jsonify({'success': False, 'message': 'Failed to save feedback'}), 500


# ─── Me endpoint — lets frontend check current verified status ────────────────
@app.route('/api/me')
def me():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    email = session['user']['email']
    user  = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'email':          user.email,
        'name':           user.name,
        'is_verified':    bool(user.is_verified),
        'feedback_count': user.feedback_count or 0,
        'is_admin':       bool(user.is_admin),
    })


# ─── Admin stats ──────────────────────────────────────────────────────────────
@app.route('/api/admin/stats')
def admin_stats():
    if 'user' not in session or not session['user'].get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    from sqlalchemy import func

    users = User.query.filter_by(is_admin=False).order_by(User.last_active.desc()).all()

    lang_stats = (db.session.query(ActivityLog.language, func.count(ActivityLog.id))
                  .filter(ActivityLog.language != None)
                  .group_by(ActivityLog.language)
                  .all())

    from datetime import timedelta
    fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
    daily_activity = (db.session.query(
        func.date(ActivityLog.created_at).label('day'),
        func.count(ActivityLog.id).label('count')
    ).filter(ActivityLog.created_at >= fourteen_days_ago)
     .group_by(func.date(ActivityLog.created_at))
     .order_by('day').all())

    feedbacks  = Feedback.query.order_by(Feedback.created_at.desc()).limit(50).all()
    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar()

    verified_count = User.query.filter_by(is_admin=False, is_verified=True).count()
    regular_count  = User.query.filter_by(is_admin=False, is_verified=False).count()

    # Per-user real feedback count from the feedback table (not the capped column)
    from sqlalchemy import func as safunc
    fb_counts = dict(
        db.session.query(Feedback.user_email, safunc.count(Feedback.id))
        .group_by(Feedback.user_email).all()
    )
    fb_ratings = dict(
        db.session.query(Feedback.user_email, safunc.avg(Feedback.rating))
        .group_by(Feedback.user_email).all()
    )

    return jsonify({
        'users': [{
            'name':           u.name,
            'email':          u.email,
            'created_at':     u.created_at.isoformat(),
            'last_active':    u.last_active.isoformat() if u.last_active else None,
            'snippet_count':  Snippet.query.filter_by(user_email=u.email).count(),
            'feedback_count': fb_counts.get(u.email, 0),
            'avg_feedback':   round(float(fb_ratings[u.email]), 1) if u.email in fb_ratings else None,
            'is_verified':    bool(u.is_verified),
        } for u in users],
        'language_stats':  [{'language': l, 'count': c} for l, c in lang_stats],
        'daily_activity':  [{'day': str(d), 'count': c} for d, c in daily_activity],
        'feedback': [{
            'user_name':  f.user_name,
            'user_email': f.user_email,
            'rating':     f.rating,
            'message':    f.message,
            'created_at': f.created_at.isoformat(),
        } for f in feedbacks],
        'avg_rating':      round(float(avg_rating), 1) if avg_rating else None,
        'total_users':     len(users),
        'total_snippets':  Snippet.query.count(),
        'total_feedback':  Feedback.query.count(),
        'verified_count':  verified_count,
        'regular_count':   regular_count,
    })


# ============= Error Handlers =============

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Route not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ============= Main =============

if __name__ == '__main__':
    logger.info("Starting CodeGenie…")
    logger.info(f"HF token configured: {bool(HUGGINGFACE_API_TOKEN)}")
    app.run(debug=True, host='0.0.0.0', port=5000)