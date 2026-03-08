import os
import time
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class ThreatIntelIntegrator:
    def __init__(self):
        # Setup SQLite Database
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(base_dir, "database", "kaali.db")
        
        self.abuseipdb_key = os.getenv("ABUSEIPDB_API_KEY", "")
        self._init_db()

    def _init_db(self):
        """Ensures the incidents table has the necessary columns for Threat Intel."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if incidents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(incidents)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add columns if missing
            new_columns = [
                ("abuse_score", "INTEGER"),
                ("ti_summary", "TEXT"),
                ("ti_updated_at", "TEXT")
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_type}")
                        print(f"[*] Added {col_name} column to incidents table.")
                    except Exception as e:
                        print(f"[-] Could not alter incidents table: {e}")
                        
        conn.commit()
        conn.close()
        print(f"[*] Initialized Threat Intel DB connection at {self.db_path}")

    def query_abuseipdb(self, ip_address):
        """Queries the AbuseIPDB API for information on an IP."""
        if not self.abuseipdb_key or self.abuseipdb_key == "your_abuseipdb_api_key":
            return self._mock_abuseipdb(ip_address)
            
        url = 'https://api.abuseipdb.com/api/v2/check'
        querystring = {
            'ipAddress': ip_address,
            'maxAgeInDays': '90'
        }
        headers = {
            'Accept': 'application/json',
            'Key': self.abuseipdb_key
        }

        try:
            response = requests.request(method='GET', url=url, headers=headers, params=querystring)
            if response.status_code == 200:
                data = response.json().get('data', {})
                return {
                    "score": data.get("abuseConfidenceScore", 0),
                    "country": data.get("countryCode", "Unknown"),
                    "isp": data.get("isp", "Unknown"),
                    "domain": data.get("domain", "Unknown"),
                    "total_reports": data.get("totalReports", 0)
                }
            else:
                print(f"[-] AbuseIPDB API Error: {response.text}")
                return None
        except Exception as e:
            print(f"[-] Failed to query AbuseIPDB: {e}")
            return None

    def _mock_abuseipdb(self, ip_address):
        """Provides mock TI data if no API key is set."""
        print(f"[*] No valid AbuseIPDB API key found. Using mock data for {ip_address}")
        # Pseudo-random mock logic based on the IP string
        score = sum(int(c) for c in ip_address if c.isdigit()) * 5
        score = min(score, 100) # Cap at 100
        
        return {
            "score": score,
            "country": "US",
            "isp": "Mock ISP Inc.",
            "domain": "mock-malicious.com" if score > 50 else "mock-benign.com",
            "total_reports": score * 2
        }

    def enrich_incidents(self):
        """Finds incidents without TI data and enriches them."""
        print(f"[*] Running Threat Intel queries ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if incidents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'")
        if not cursor.fetchone():
            conn.close()
            return
            
        # Find unenriched incidents
        cursor.execute('''
            SELECT incident_id, source_ip 
            FROM incidents 
            WHERE abuse_score IS NULL OR ti_updated_at IS NULL
        ''')
        unenriched = cursor.fetchall()
        
        if not unenriched:
            conn.close()
            return
            
        print(f"[*] Found {len(unenriched)} unenriched incidents. Querying Intel providers...")
        
        for incident_id, source_ip in unenriched:
            print(f"[*] Checking IP {source_ip} for incident {incident_id}...")
            
            ti_data = self.query_abuseipdb(source_ip)
            
            if ti_data:
                score = ti_data["score"]
                
                # Format a summary string
                summary = (
                    f"AbuseIPDB Score: {score}/100 | "
                    f"Country: {ti_data['country']} | "
                    f"ISP: {ti_data['isp']} | "
                    f"Reports: {ti_data['total_reports']}"
                )
                
                cursor.execute('''
                    UPDATE incidents 
                    SET abuse_score = ?, ti_summary = ?, ti_updated_at = ?
                    WHERE incident_id = ?
                ''', (score, summary, datetime.now().isoformat(), incident_id))
                
                print(f"[+] Enriched incident {incident_id} (Score: {score})")
            
            # Rate limiting pause (important for real API)
            time.sleep(2)
                
        conn.commit()
        conn.close()

def start_ti_integrator():
    integrator = ThreatIntelIntegrator()
    print("[*] Threat Intel engine started. Checking for new incidents every 2 minutes...")
    while True:
        try:
            integrator.enrich_incidents()
            time.sleep(120)
        except KeyboardInterrupt:
            print("[*] Stopping Threat Intel engine...")
            break
        except Exception as e:
            print(f"[-] Error in Threat Intel loop: {e}")
            time.sleep(120)

if __name__ == "__main__":
    start_ti_integrator()
