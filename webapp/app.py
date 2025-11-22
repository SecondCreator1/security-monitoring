from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from pymongo import MongoClient
from elasticsearch import Elasticsearch
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'CHANGE_THIS_TO_A_SECRET_FOR_FLASH_MESSAGES'

# Configs
CSV_TARGET = '/app/logs/csv'
JSON_TARGET = '/app/logs/json'
MONGO_URI = 'mongodb://mongodb:27017/'
ES_HOST = "http://elasticsearch:9200"

client = MongoClient(MONGO_URI)
db = client['security_monitoring']
uploads_collection = db['uploads']
es = Elasticsearch(ES_HOST)

# ----- Dashboard -----
@app.route("/", methods=["GET"])
def dashboard():
    return render_template("dashboard.html")

# ----- Upload Page -----
@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    if request.method == 'POST':
        # DEBUG PRINTS for troubleshooting
        print("DEBUG -- request.files :", request.files)
        print("DEBUG -- request.form :", request.form)
        # --------------------------------
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
        result = uploads_collection.insert_one(meta)
        flash(f"Upload successful: {uploaded_file.filename}")
        return redirect(url_for('upload_page'))
    return render_template('upload.html')

# ----- List Uploads -----
@app.route('/uploads', methods=['GET'])
def list_uploads():
    uploads = []
    for doc in uploads_collection.find({}).sort('upload_date', -1):
        item = dict(doc)
        item['_id'] = str(item['_id'])
        uploads.append(item)
    return jsonify({"uploads": uploads}), 200

# ----- Search API -----
@app.route('/search', methods=['GET'])
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
def search_page():
    return render_template("search.html")

# ----- Stats API -----
@app.route('/stats', methods=['GET'])
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
                    "timestamp": {"gte": today_start_iso}
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
    stats = {
        "total_logs": total_logs,
        "today_logs": today_logs,
        "error_logs": error_logs,
        "uploads_count": uploads_count
    }
    return jsonify(stats), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
