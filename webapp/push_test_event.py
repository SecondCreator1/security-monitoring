import json
import redis

r = redis.Redis(host="redis", port=6379, decode_responses=True)

event = {
    "timestamp": "2025-12-23T18:15:00Z",
    "username": "alice",
    "source_ip": "192.168.1.10",
    "action": "login_failure",
    "severity": "ERROR"
}

r.rpush("log_events", json.dumps(event))
print("Pushed test event to Redis log_events")
