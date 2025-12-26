import json
import time
from datetime import datetime

import redis
from pymongo import MongoClient

# Redis and Mongo connections
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
mongo_client = MongoClient("mongodb://mongodb:27017/")
db = mongo_client["security_monitoring"]

rules_col = db["alert_rules"]
alerts_col = db["alerts"]


def load_rules():
    """Load all enabled alert rules."""
    return list(rules_col.find({"enabled": True}))


def process_event(event, rules):
    """Apply rules to a single event and insert alerts if they match."""
    for rule in rules:
        if rule["type"] == "action_match":
            field = rule["field"]
            if event.get(field) == rule["value"]:
                # Prefer @timestamp (real event time); fallback to timestamp or now
                ts = (
                    event.get("@timestamp")
                    or event.get("timestamp")
                    or datetime.utcnow().isoformat() + "Z"
                )

                alert = {
                    "timestamp": ts,
                    "username": event.get("username"),
                    "source_ip": event.get("source_ip"),
                    "action": event.get("action"),
                    "severity": rule.get("severity", "CRITICAL"),
                    "message": (
                        f"Rule '{rule['name']}' matched for user "
                        f"{event.get('username')} from {event.get('source_ip')}"
                    ),
                    "rule_name": rule["name"],
                    "status": "open",
                }
                alerts_col.insert_one(alert)
                print("ALERT CREATED:", alert)


def main():
    print("Alert worker started, waiting for events...")
    rules = load_rules()

    while True:
        data = redis_client.lpop("log_events")
        if not data:
            time.sleep(1)
            continue

        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            print("Invalid JSON event, skipping:", data)
            continue

        process_event(event, rules)


if __name__ == "__main__":
    main()

