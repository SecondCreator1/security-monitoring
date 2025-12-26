# SecMon – Security & Authentication Monitoring

SecMon is a lightweight security log monitoring stack built on top of the ELK stack with a custom Flask web UI, a simple rules engine, and alert storage in MongoDB.

It lets you:

- Upload security logs (CSV/JSON) and index them into Elasticsearch.
- Search and visualize login failures and other events.
- Generate alerts from log events using custom rules stored in MongoDB.
- View alerts and KPIs in a modern dashboard and embed Kibana for deep analysis.

---

## Architecture

Main components:

- **Elasticsearch** – stores indexed log events and powers search.
- **Logstash** – ingests CSV/JSON logs from mounted folders and pushes them into Elasticsearch and Redis.
- **Redis** – queue (`log_events` list) for events to be processed by the alert worker.
- **MongoDB** – stores alert rules and generated alerts (`security_monitoring` database).
- **Flask webapp** (`/webapp`) – UI and API:
  - Dashboard, search page, upload page, alerts page.
  - Endpoints like `/search`, `/upload`, `/alerts`, `/stats`, `/uploads`.
- **Alert worker** – background process (separate container) that reads events from Redis, applies rules, and inserts alerts into MongoDB.
- **Kibana** – embedded dashboard for advanced Elasticsearch visualizations.

Everything is orchestrated with **Docker Compose**.

---

## Project structure

.
├── docker-compose.yml
├── es-data/ # Elasticsearch persistent data
├── logs/
│ ├── csv/ # CSV log upload directory (mounted into Logstash & webapp)
│ └── json/ # JSON log upload directory
├── logstash/
│ └── pipeline/ # Logstash pipeline config(s)
├── mongo-data/ # MongoDB data files
├── README.md
└── webapp/
├── alert_worker.py
├── app.py
├── Dockerfile
├── init_alert_rules.py
├── push_test_event.py
├── requirements.txt
├── static/
└── templates/


---

## Getting started

### Prerequisites

- Docker
- Docker Compose v2 (or `docker-compose`)

### 1. Clone the repository

git clone https://github.com/SecondCreator1/security-monitoring
cd security-monitoring


### 2. Start the stack

docker compose up --build


This will start:

- `elasticsearch` on `localhost:9200`
- `kibana` on `localhost:5601`
- `mongodb` on `localhost:27017`
- `redis` on `localhost:6379`
- `webapp` (Flask UI) on `localhost:8000`
- `alertworker` (rules engine worker, no exposed port)

---

## Using the application

### Web dashboard

Open:
http://localhost:8000/

Main features:

- **KPIs**: total logs, logs today, error logs, uploads, alerts today, last critical alert.
- **Failed Logins Over Time**: line chart of `login_failure` events over time using Elasticsearch data.
- **Alerts By Severity (All Time)**: bar chart aggregating all alerts from MongoDB by severity.
- **Recent Uploaded Files**: table of latest uploaded log files.
- **Kibana Dashboard**: embedded iframe pointing to a Kibana dashboard.

### Upload logs

Go to **Upload Logs** or directly:

http://localhost:8000/upload


Upload CSV/JSON log files that match your Logstash pipeline format. Files are stored under `logs/csv` or `logs/json` and picked up by Logstash, which indexes them into Elasticsearch and pushes parsed events into Redis.

### Search logs

Go to **Search** (`/searchpage`) to run queries. The UI calls `/search?q=...` which proxies to Elasticsearch.

### Alerts

The `/alerts` endpoint returns alert documents from MongoDB. The dashboard aggregates them client-side to show alert counts by severity and the most recent critical alert.

The alert worker:

- Listens to `log_events` in Redis.
- Loads active rules from `security_monitoring.alert_rules`.
- Inserts matching alerts into `security_monitoring.alerts`.

---

## Development

### Run commands inside containers

Examples:

Tail webapp logs
docker compose logs -f webapp

Tail alert worker logs
docker compose logs -f alertworker

Open Mongo shell
docker compose exec mongodb mongosh

Open Redis CLI
docker compose exec redis redis-cli


### Rebuilding

If you change Python code or dependencies:

docker compose up --build webapp alertworker


---

## Future improvements

- Rule editor in the UI (CRUD for Mongo `alert_rules`).
- Role-based access control for the dashboard.
- More visualizations (top source IPs, countries, resources under attack).
- Export and archival of alerts.

---

## License

Add your preferred license here (MIT, Apache-2.0, etc.).


