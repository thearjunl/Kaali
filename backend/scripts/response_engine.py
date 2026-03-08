import sqlite3
import time
import os
import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / 'database' / 'kaali.db'
FIREWALL_LOG_PATH = BASE_DIR / 'database' / 'mock_firewall_blocks.log'

def init_response_columns():
    """Ensure the incidents table has the required Response Automation columns."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if incidents table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'")
    if not cursor.fetchone():
        print("[!] Incidents table not found. Waiting for other engines...")
        return False
        
    try:
        # Add columns if they don't exist
        columns = [
            ("response_action", "TEXT"),
            ("response_time", "TIMESTAMP"),
            ("status", "TEXT DEFAULT 'New'")
        ]
        
        for col_name, col_type in columns:
            try:
                cursor.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
        conn.commit()
    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        conn.close()
    return True

def simulate_firewall_block(ip_address):
    """Simulates a perimeter firewall block by writing to a local log file."""
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] ACTION: BLOCK | IP_ADDRESS: {ip_address} | SOURCE: KAALI Response Engine\n"
    
    try:
        with open(FIREWALL_LOG_PATH, 'a') as f:
            f.write(log_entry)
        print(f"[*] Simulated Firewall Block for IP: {ip_address}")
        return True
    except Exception as e:
        print(f"[!] Alert: Failed to write to firewall log: {e}")
        return False

def simulate_email_alert(incident_id, severity, ip_address, ai_summary):
    """Simulates sending an email to the SOC analysts."""
    print(f"\n{'='*50}")
    print(f"📧 EMAIL ALERT TRIGGERED - SOC TEAM NOTIFIED")
    print(f"{'='*50}")
    print(f"Incident ID : {incident_id}")
    print(f"Severity    : {severity}")
    print(f"Source IP   : {ip_address}")
    print(f"\nExecutive Summary:\n{ai_summary}")
    print(f"{'='*50}\n")
    return True

def run_response_engine():
    print("[*] Starting KAALI Automated Response Engine...")
    
    while True:
        if not init_response_columns():
            time.sleep(10)
            continue
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find incidents that are Critical or High, but haven't been acted upon (status='New' or NULL)
        # We also want to wait until the AI Analysis is finished (ai_analyzed_at IS NOT NULL)
        cursor.execute('''
            SELECT incident_id, severity, source_ip, ai_summary 
            FROM incidents 
            WHERE (severity = 'Critical' OR severity = 'High')
              AND (status = 'New' OR status IS NULL)
              AND ai_analyzed_at IS NOT NULL
        ''')
        
        pending_incidents = cursor.fetchall()
        
        for incident in pending_incidents:
            inc_id = incident['incident_id']
            ip = incident['source_ip']
            severity = incident['severity']
            summary = incident['ai_summary']
            
            print(f"[*] Automating Response for Incident {inc_id} (Severity: {severity})")
            
            actions_taken = []
            
            # Action 1: Block IP
            if simulate_firewall_block(ip):
                actions_taken.append(f"Blocked IP {ip}")
            
            # Action 2: Email Alert
            if simulate_email_alert(inc_id, severity, ip, summary):
                actions_taken.append("Sent Email Alert to SOC")
                
            action_summary = " | ".join(actions_taken)
            current_time = datetime.datetime.now().isoformat()
            
            # Update Database status
            cursor.execute('''
                UPDATE incidents 
                SET status = 'Contained', 
                    response_action = ?, 
                    response_time = ?
                WHERE incident_id = ?
            ''', (action_summary, current_time, inc_id))
            
            print(f"[+] Incident {inc_id} Status Updated to 'Contained'.")
            
        conn.commit()
        conn.close()
        
        # Sleep before checking again
        time.sleep(15)

if __name__ == "__main__":
    try:
        run_response_engine()
    except KeyboardInterrupt:
        print("\n[*] Stopping KAALI Automated Response Engine...")
