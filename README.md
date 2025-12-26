# 🔐 SecMon – Security & Authentication Monitoring

SecMon is a lightweight **security log monitoring and alerting platform** built on top of the **ELK stack**, enhanced with a **custom Flask web UI**, a **simple rules engine**, and **MongoDB-backed alert storage**.

It is designed to help security teams and students **ingest, analyze, and respond to authentication and security events** in a clear, scalable, and containerized environment.

---

## ✨ Key Features

- 📥 Upload security logs (**CSV / JSON**) and index them into Elasticsearch  
- 🔍 Search and visualize login failures and security-related events  
- 🚨 Generate alerts from log events using custom rules stored in MongoDB  
- 📊 Monitor KPIs and alerts in a modern web dashboard  
- 📈 Embed Kibana dashboards for advanced analysis  
- 🐳 Fully containerized architecture using Docker Compose  

---

## 🧱 Architecture

SecMon is composed of the following main components:

- **Elasticsearch**  
  Stores indexed log events and powers fast search and aggregation.

- **Logstash**  
  Ingests CSV/JSON logs from mounted folders and pushes parsed events into:
  - Elasticsearch
  - Redis

- **Redis**  
  Acts as a queue (`log_events`) for events to be processed by the alert worker.

- **MongoDB**  
  Stores alert rules and generated alerts in the  
  `security_monitoring` database.

- **Flask Web Application (`/webapp`)**  
  Provides UI and API endpoints:
  - Dashboard
  - Log upload
  - Log search
  - Alerts overview  
  - API endpoints: `/search`, `/upload`, `/alerts`, `/stats`, `/uploads`

- **Alert Worker**  
  Background service (separate container) that:
  - consumes events from Redis
  - applies active alert rules
  - inserts matching alerts into MongoDB

- **Kibana**  
  Embedded dashboard for advanced Elasticsearch visualizations.

All components are orchestrated using **Docker Compose**.

---

## 📁 Project Structure

```text
.
├── docker-compose.yml
├── es-data/               # Elasticsearch persistent data
├── mongo-data/            # MongoDB data files
├── logs/
│   ├── csv/               # CSV log upload directory
│   └── json/              # JSON log upload directory
├── logstash/
│   └── pipeline/          # Logstash pipeline configurations
├── webapp/
│   ├── app.py             # Flask application
│   ├── alert_worker.py    # Alert processing worker
│   ├── init_alert_rules.py
│   ├── push_test_event.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── static/
│   └── templates/
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Docker  
- Docker Compose v2 (or `docker-compose`)

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/SecondCreator1/security-monitoring
cd security-monitoring
```

---

### 2️⃣ Start the Stack

```bash
docker compose up --build
```

This will start the following services:

| Service        | URL / Port |
|---------------|------------|
| Elasticsearch | http://localhost:9200 |
| Kibana        | http://localhost:5601 |
| MongoDB       | localhost:27017 |
| Redis         | localhost:6379 |
| Web App       | http://localhost:8000 |
| Alert Worker  | Internal |

---

## 🖥️ Using the Application

### 📊 Web Dashboard

Open:

```
http://localhost:8000/
```

The dashboard provides:

- **KPIs**
  - Total logs
  - Logs today
  - Error logs
  - Uploaded files
  - Alerts today
  - Last critical alert

- **Failed Logins Over Time**
  - Line chart based on `login_failure` events

- **Alerts by Severity**
  - Aggregation of alerts stored in MongoDB

- **Recent Uploaded Files**
  - List of the latest ingested log files

- **Embedded Kibana Dashboard**
  - Advanced Elasticsearch visualizations

---

### 📤 Upload Logs

Access:

```
http://localhost:8000/upload
```

- Upload CSV or JSON files matching the Logstash pipeline format  
- Files are stored in `logs/csv` or `logs/json`  
- Logstash automatically ingests and indexes them

---

### 🔎 Search Logs

Use the search page:

```
/searchpage
```

The UI sends queries to:

```
/search?q=...
```

which proxies requests to Elasticsearch.

---

### 🚨 Alerts

- Alerts are retrieved from MongoDB via the `/alerts` endpoint  
- The dashboard aggregates alerts by severity and highlights the most recent critical alert  

#### Alert Processing Flow

1. Logstash pushes events to Redis  
2. Alert worker listens to the `log_events` queue  
3. Active rules are loaded from `security_monitoring.alert_rules`  
4. Matching alerts are inserted into `security_monitoring.alerts`  

---

## 🛠️ Development & Debugging

### Useful Commands

Tail web app logs:
```bash
docker compose logs -f webapp
```

Tail alert worker logs:
```bash
docker compose logs -f alertworker
```

Open MongoDB shell:
```bash
docker compose exec mongodb mongosh
```

Open Redis CLI:
```bash
docker compose exec redis redis-cli
```

---

### 🔁 Rebuilding Services

If you change Python code or dependencies:

```bash
docker compose up --build webapp alertworker
```

---

## 🔮 Future Improvements

- Rule editor UI (CRUD for `alert_rules`)
- Role-based access control (RBAC)
- Advanced visualizations (top IPs, countries, attacked resources)
- Alert export and archival

---

## 📜 License

Add your preferred license here (MIT, Apache-2.0, etc.).
