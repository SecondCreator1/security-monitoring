from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from datetime import datetime

app = Flask(__name__)

# Add a homepage route so localhost:8000/ works!
@app.route("/", methods=["GET"])
def home():
    return "<h1>Hello Security Logs Monitoring</h1>"

# Directories for saving uploaded files
CSV_TARGET = '/app/logs/csv'
JSON_TARGET = '/app/logs/json'
MONGO_URI = 'mongodb://mongodb:27017/'  # Use 'localhost' if NOT in Docker Compose!

client = MongoClient(MONGO_URI)
db = client['security_monitoring']
uploads_collection = db['uploads']

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

    # Insert and fetch the MongoDB-generated _id, returned as a string
    result = uploads_collection.insert_one(meta)
    meta["_id"] = str(result.inserted_id)

    return jsonify({"success": True, "meta": meta}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
