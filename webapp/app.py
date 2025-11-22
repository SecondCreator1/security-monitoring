from flask import Flask, request, jsonify
from pymongo import MongoClient
from elasticsearch import Elasticsearch
import os
from datetime import datetime

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "<h1>Hello Security Logs Monitoring</h1>"

# Directories for saving uploaded files (these should match your Docker volumes)
CSV_TARGET = '/app/logs/csv'
JSON_TARGET = '/app/logs/json'
MONGO_URI = 'mongodb://mongodb:27017/'  # Use 'localhost' if NOT in Docker Compose!
ES_HOST = "http://elasticsearch:9200"

client = MongoClient(MONGO_URI)
db = client['security_monitoring']
uploads_collection = db['uploads']

es = Elasticsearch(ES_HOST)

@app.route('/upload', methods=['POST'])
def upload_log():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    ext = os.path.splitext(uploaded_file.filename)[1].lower()
    if ext == '.csv':
        target_dir = CSV_TARGET
        filetype = 'csv'
    elif ext == '.json':
        target_dir = JSON_TARGET
        filetype = 'json'
    else:
        return jsonify({"error": "File must be .csv or .json"}), 400

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
    meta["_id"] = str(result.inserted_id)

    return jsonify({"success": True, "meta": meta}), 200

@app.route('/uploads', methods=['GET'])
def list_uploads():
    uploads = []
    for doc in uploads_collection.find({}).sort('upload_date', -1):  # Most recent first
        item = dict(doc)
        item['_id'] = str(item['_id'])
        uploads.append(item)
    return jsonify({"uploads": uploads}), 200

@app.route('/search', methods=['GET'])
def search_logs():
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 20))
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
