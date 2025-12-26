from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from pymongo import MongoClient
from elasticsearch import Elasticsearch
import os
from datetime import datetime, timedelta
from bson.objectid import ObjectId

# >>> AUTH
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# <<< AUTH

app = Flask(__name__)
app.secret_key = 'CHANGE_THIS_TO_A_SECRET_FOR_FLASH_MESSAGES'

# Configs
CSV_TARGET = '/app/logs/csv'
JSON_TARGET = '/app/logs/json'
MONGO_URI = 'mongodb://mongodb:27017/'
ES_HOST = "http://elasticsearch:9200"

client = MongoClient(MONGO_URI)
db = client['security_monitoring']
users_collection = db['users']
uploads_collection = db['uploads']
es = Elasticsearch(ES_HOST)

# >>> AUTH: ensure admin + decorator + routes
def ensure_default_admin():
    """Create default admin user if it does not exist."""
    admin = users_collection.find_one({"username": "admin"})
    if not admin:
        users_collection.insert_one({
            "username": "admin",
            "password_hash": generate_password_hash("admin123"),
            "role": "admin",
            "created_at": datetime.utcnow().isoformat() + "Z"
        })

ensure_default_admin()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user' not in session:
            # redirect to login, keep original URL in ?next=
            return redirect(url_for('login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = users_collection.find_one({"username": username})
        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid username or password", "danger")
            return redirect(url_for('login'))

        session['user'] = {
            "username": user['username'],
            "role": user.get('role', 'admin')
        }
        next_url = request.args.get('next') or url_for('dashboard')
        return redirect(next_url)

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))
# <<< AUTH

# ------ Alerts API -----
@app.route('/alerts', methods=['GET'])
@login_required
def get_alerts():
    alerts = []
    for doc in db['alerts'].find({}).sort('timestamp', -1).limit(100):
        doc['_id'] = str(doc['_id'])
        alerts.append(doc)
    return jsonify({"alerts": alerts}), 200

# >>> LOGIN FAILURES BREAKDOWN API
@app.route('/login_failures_breakdown', methods=['GET'])
@login_required
def login_failures_breakdown():
    """
    Returns composition of login_failure logs for a given date,
    broken down by message (type).
    """
    date_str = request.args.get('date')  # e.g., "2025-11-22"
    if not date_str:
        return jsonify({"error": "date is required"}), 400

    es_index = "security-logs-*"
    start = f"{date_str}T00:00:00Z"
    end   = f"{date_str}T23:59:59Z"

    body = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"action": "login_failure"}},
                    {"range": {"@timestamp": {"gte": start, "lte": end}}}
                ]
            }
        },
        "size": 0,
        "aggs": {
            # your "type" text is in message, e.g. "Suspicious login failure - possible brute force"
            "by_action": {
                "terms": {"field": "message.keyword", "size": 20}
            }
        }
    }

    res = es.search(index=es_index, body=body)
    actions = [
        {"key": b["key"], "count": b["doc_count"]}
        for b in res["aggregations"]["by_action"]["buckets"]
    ]

    return jsonify({"date": date_str, "by_action": actions}), 200
# <<< LOGIN FAILURES BREAKDOWN API

# ----- Dashboard -----
@app.route("/", methods=["GET"])
@login_required
def dashboard():
    return render_template("dashboard.html")

# ----- Upload Page -----
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_page():
    if request.method == 'POST':
        print("DEBUG -- request.files :", request.files)
        print("DEBUG -- request.form :", request.form)

        if 'file' not in request.files:
            flash("No file part")
            return redirect(url_for('upload_page'))

        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            flash("No selected file")
            return redirect(url_for('upload_page'))

        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext == '.csv':
            target_dir = CSV_TARGET
            filetype = 'csv'
        elif ext == '.json':
            target_dir = JSON_TARGET
            filetype = 'json'
        else:
            flash("File must be .csv or .json")
            return redirect(url_for('upload_page'))

        os.makedirs(target_dir, exist_ok=True)
        save_path = os.path.join(target_dir, uploaded_file.filename)
        uploaded_file.save(save_path)

        meta = {
            "filename": uploaded_file.filename,
            "size": os.path.getsize(save_path),
            "type": filetype,
            "upload_date": datetime.utcnow().isoformat() + "Z",
            "status": "uploaded"
        }
        uploads_collection.insert_one(meta)
        flash(f"Upload successful: {uploaded_file.filename}")
        return redirect(url_for('upload_page'))
    return render_template('upload.html')

# ----- List Uploads -----
@app.route('/uploads', methods=['GET'])
@login_required
def list_uploads():
    uploads = []
    for doc in uploads_collection.find({}).sort('upload_date', -1):
        item = dict(doc)
        item['_id'] = str(item['_id'])
        uploads.append(item)
    return jsonify({"uploads": uploads}), 200

# ----- Search API -----
@app.route('/search', methods=['GET'])
@login_required
def search_logs():
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 50))
    es_index = "security-logs-*"
    es_query = {
        "query": {
            "query_string": {
                "query": query if query else "*"
            }
        },
        "from": (page - 1) * size,
        "size": size
    }
    result = es.search(index=es_index, body=es_query)
    hits = result['hits']['hits']
    total = result['hits']['total']['value']
    logs = [hit['_source'] for hit in hits]
    return jsonify({"results": logs, "total": total, "page": page, "size": size}), 200

# ----- Search Page -----
@app.route('/searchpage', methods=['GET'])
@login_required
def search_page():
    return render_template("search.html")

# ----- Stats API -----
@app.route('/stats', methods=['GET'])
@login_required
def get_stats():
    es_index = "security-logs-*"
    total_logs = es.count(index=es_index)['count']

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_iso = today_start.isoformat() + "Z"

    today_logs = es.count(
        index=es_index,
        body={
            "query": {
                "range": {
                    "@timestamp": {"gte": today_start_iso}
                }
            }
        }
    )["count"]

    severities = ["ERROR", "CRITICAL"]
    error_logs = es.count(
        index=es_index,
        body={"query": {"terms": {"severity": severities}}}
    )["count"]

    uploads_count = uploads_collection.count_documents({})

    # Alerts today (from MongoDB alerts collection)
    alerts_today = db['alerts'].count_documents({
        "timestamp": {"$gte": today_start_iso}
    })

    stats = {
        "total_logs": total_logs,
        "today_logs": today_logs,
        "error_logs": error_logs,
        "uploads_count": uploads_count,
        "alerts_today": alerts_today
    }
    return jsonify(stats), 200

# ----- Alerts Page -----
@app.route('/alertspage', methods=['GET'])
@login_required
def alerts_page():
    return render_template('alerts.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
