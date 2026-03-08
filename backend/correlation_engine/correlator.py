import os
import time
import uuid
import sqlite3
from datetime import datetime

class AlertCorrelator:
    def __init__(self):
        # Setup SQLite Database
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(base_dir, "database", "kaali.db")
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database schema for incidents and updates alerts."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create incidents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                title TEXT,
                severity TEXT,
                source_ip TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                summary TEXT
            )
        ''')
        
        # Check if incident_id column exists in alerts table (if table exists)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(alerts)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'incident_id' not in columns:
                try:
                    cursor.execute("ALTER TABLE alerts ADD COLUMN incident_id TEXT")
                    print("[*] Added incident_id column to alerts table.")
                except Exception as e:
                    print(f"[-] Could not alter alerts table: {e}")
                
        conn.commit()
        conn.close()
        print(f"[*] Initialized Correlator DB at {self.db_path}")

    def correlate_alerts(self):
        """Groups unassigned alerts by source IP to form incidents."""
        print(f"[*] Running correlation engine ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if alerts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
        if not cursor.fetchone():
            conn.close()
            return
            
        # Find all unassigned alerts
        cursor.execute('''
            SELECT alert_id, type, severity, source_ip, timestamp, description 
            FROM alerts 
            WHERE incident_id IS NULL
        ''')
        unassigned_alerts = cursor.fetchall()
        
        if not unassigned_alerts:
            conn.close()
            return
            
        print(f"[*] Found {len(unassigned_alerts)} new unassigned alerts. Correlating...")
        
        # Group by source_ip
        grouped_alerts = {}
        for alert in unassigned_alerts:
            alert_id, atype, severity, source_ip, timestamp, description = alert
            if source_ip not in grouped_alerts:
                grouped_alerts[source_ip] = []
            grouped_alerts[source_ip].append(alert)
            
        for source_ip, alerts in grouped_alerts.items():
            # Check if there is an open incident for this IP
            cursor.execute('''
                SELECT incident_id, severity FROM incidents 
                WHERE source_ip = ? AND status != 'Closed'
            ''', (source_ip,))
            existing_incident = cursor.fetchone()
            
            # Determine highest severity among new alerts
            severities = [a[2] for a in alerts]
            highest_severity = "Low"
            if "Critical" in severities:
                highest_severity = "Critical"
            elif "High" in severities:
                highest_severity = "High"
            elif "Medium" in severities:
                highest_severity = "Medium"
                
            if existing_incident:
                incident_id = existing_incident[0]
                current_severity = existing_incident[1]
                
                # Upgrade severity if needed
                severity_ranks = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
                if severity_ranks.get(highest_severity, 0) > severity_ranks.get(current_severity, 0):
                    cursor.execute('''
                        UPDATE incidents SET severity = ?, updated_at = ?
                        WHERE incident_id = ?
                    ''', (highest_severity, datetime.now().isoformat(), incident_id))
                    
                print(f"[*] Added {len(alerts)} alerts to existing incident {incident_id} (IP: {source_ip})")
            else:
                # Create a new incident
                incident_id = str(uuid.uuid4())
                title = f"Multiple Alerts from {source_ip}"
                if len(alerts) == 1:
                    title = f"{alerts[0][1]} from {source_ip}"
                    
                cursor.execute('''
                    INSERT INTO incidents (incident_id, title, severity, source_ip, status, created_at, updated_at, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    incident_id, 
                    title, 
                    highest_severity, 
                    source_ip, 
                    "New", 
                    datetime.now().isoformat(), 
                    datetime.now().isoformat(),
                    f"Correlated {len(alerts)} alerts from {source_ip}."
                ))
                print(f"[!] NEW INCIDENT CREATED: {title} [Severity: {highest_severity}]")
                
            # Update alerts with the incident_id
            for alert in alerts:
                cursor.execute("UPDATE alerts SET incident_id = ? WHERE alert_id = ?", (incident_id, alert[0]))
                
        conn.commit()
        conn.close()

def start_correlator():
    correlator = AlertCorrelator()
    print("[*] Alert Correlation Engine started. Running every 60 seconds...")
    while True:
        try:
            correlator.correlate_alerts()
            time.sleep(60)
        except KeyboardInterrupt:
            print("[*] Stopping Alert Correlation Engine...")
            break
        except Exception as e:
            print(f"[-] Error in Correlation Engine loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_correlator()
