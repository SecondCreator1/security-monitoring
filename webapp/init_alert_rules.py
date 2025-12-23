from pymongo import MongoClient

MONGO_URI = "mongodb://mongodb:27017/"
client = MongoClient(MONGO_URI)
db = client["security_monitoring"]

# Collections
alert_rules = db["alert_rules"]
alerts = db["alerts"]

# Simple rule: trigger alert on any login_failure
rule = {
    "name": "Failed logins rule",
    "type": "action_match",     # simple rule type
    "field": "action",          # field in event to check
    "value": "login_failure",   # value to match
    "severity": "CRITICAL",
    "enabled": True
}

# Insert only if not already present
existing = alert_rules.find_one({"name": rule["name"]})
if not existing:
    alert_rules.insert_one(rule)
    print("Inserted initial alert rule.")
else:
    print("Rule already exists.")

print("Collections ready: alert_rules, alerts")
