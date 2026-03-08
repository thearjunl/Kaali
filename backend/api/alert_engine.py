import os
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class AlertEngine:
    def __init__(self):
        self.es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        self.index_name = "kaali-logs"
        self.es = Elasticsearch([self.es_url])
        
        # Setup SQLite Database
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(base_dir, "database", "kaali.db")
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database and the alerts table."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                type TEXT,
                severity TEXT,
                source_ip TEXT,
                timestamp TEXT,
                description TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print(f"[*] Initialized SQLite DB at {self.db_path}")

    def store_alert(self, alert_type, severity, source_ip, description):
        """Stores a new alert in the database."""
        alert_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (alert_id, type, severity, source_ip, timestamp, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (alert_id, alert_type, severity, source_ip, timestamp, description))
        conn.commit()
        conn.close()
        print(f"[!] ALERT TRIGGERED: [{severity}] {alert_type} from {source_ip} - {description}")

    def query_recent_logs(self, minutes_ago=1):
        """Queries Elasticsearch for logs in the last N minutes."""
        now = datetime.now()
        past = now - timedelta(minutes=minutes_ago)
        
        query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": past.isoformat(),
                        "lte": now.isoformat()
                    }
                }
            },
            "size": 10000,
            "sort": [{"timestamp": {"order": "asc"}}]
        }
        
        try:
            if not self.es.indices.exists(index=self.index_name):
                return []
            response = self.es.search(index=self.index_name, body=query)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"[-] Error querying Elasticsearch: {e}")
            return []

    def run_rules(self):
        """Executes detection rules on recent logs."""
        print(f"[*] Checking for alerts ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
        
        # We need the last 2 minutes for Rule 1 (Brute Force)
        logs = self.query_recent_logs(minutes_ago=2)
        if not logs:
            return

        # Track failed logins by IP
        failed_logins = {}
        successful_logins = []

        for log in logs:
            ip = log.get("source_ip")
            event_type = log.get("event_type")
            
            if event_type == "failed_login":
                failed_logins[ip] = failed_logins.get(ip, 0) + 1
            elif event_type == "accepted_login" or log.get("status") == "success":
                successful_logins.append(ip)

        # Rule 1: Brute Force (>5 failed logins from same IP in 2 mins)
        brute_force_ips = set()
        for ip, count in failed_logins.items():
            if count > 5:
                brute_force_ips.add(ip)
                self.store_alert(
                    alert_type="Brute Force",
                    severity="High",
                    source_ip=ip,
                    description=f"Detected {count} failed login attempts in the last 2 minutes."
                )

        # Rule 2: Suspicious Access (Successful login from an IP that had failed attempts)
        for ip in successful_logins:
            if ip in failed_logins:
                self.store_alert(
                    alert_type="Suspicious Access",
                    severity="Critical",
                    source_ip=ip,
                    description=f"Successful login from IP immediately following {failed_logins[ip]} failed attempts."
                )

def start_alert_engine():
    engine = AlertEngine()
    print("[*] Alert Engine started. Querying every 60 seconds...")
    while True:
        try:
            engine.run_rules()
            time.sleep(60)
        except KeyboardInterrupt:
            print("[*] Stopping Alert Engine...")
            break
        except Exception as e:
            print(f"[-] Error in Alert Engine loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_alert_engine()
