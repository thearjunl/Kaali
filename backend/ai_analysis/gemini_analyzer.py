import os
import time
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class GeminiAnalyzer:
    def __init__(self):
        # Setup SQLite Database
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(base_dir, "database", "kaali.db")
        
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        if self.gemini_key and self.gemini_key != "your_gemini_api_key":
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None
            
        self._init_db()

    def _init_db(self):
        """Ensures the incidents table has the necessary columns for AI Analysis."""
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
                ("ai_summary", "TEXT"),
                ("mitre_tactics", "TEXT"),
                ("remediation_steps", "TEXT"),
                ("ai_analyzed_at", "TEXT")
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
        print(f"[*] Initialized AI Analyzer DB connection at {self.db_path}")

    def generate_prompt(self, incident, alerts):
        """Creates the prompt for the LLM based on incident and alert context."""
        # SQLite incidents table columns: incident_id, title, severity, source_ip, status, created_at, updated_at, summary, abuse_score, ti_summary, ti_updated_at, ai_summary, mitre_tactics, remediation_steps, ai_analyzed_at
        incident_id = incident[0]
        title = incident[1]
        severity = incident[2]
        source_ip = incident[3]
        created_at = incident[5]
        summary = incident[7]
        abuse_score = incident[8]
        ti_summary = incident[9]
        
        prompt = f"""You are an expert Senior Security Operations Center (SOC) Analyst.
Analyze the following security incident and provide an executive summary, map it to MITRE ATT&CK tactics, and prescribe remediation steps.

[INCIDENT DETAILS]
ID: {incident_id}
Title: {title}
Severity: {severity}
Source IP: {source_ip}
Created At: {created_at}
Correlation Engine Summary: {summary}

[THREAT INTELLIGENCE]
AbuseIPDB Score: {abuse_score}/100
Context: {ti_summary}

[ASSOCIATED ALERTS]
"""
        for alert in alerts:
            prompt += f"- {alert[0]} [{alert[1]}]: {alert[2]}\n"
            
        prompt += """
Provide your analysis strictly in the following JSON format:
{
  "summary": "A 2-3 sentence executive summary of the attack scenario",
  "mitre_tactics": ["Tactic1", "Tactic2"],
  "remediation": "A concise list of 2-3 immediate actions to investigate or mitigate the threat"
}"""
        return prompt

    def analyze_with_ai(self, prompt, source_ip):
        """Sends the prompt to Gemini or returns a mock response."""
        if not self.model:
            return self._mock_ai_analysis(source_ip)
            
        try:
            response = self.model.generate_content(prompt)
            # Find the JSON block
            text = response.text
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx+1]
                return json.loads(json_str)
            else:
                print(f"[-] Failed to parse JSON from Gemini response: {text}")
                return None
        except Exception as e:
            print(f"[-] Gemini API Error: {e}")
            return None

    def _mock_ai_analysis(self, source_ip):
        """Provides mock AI analysis data if no API key is set."""
        print(f"[*] No valid Gemini API key found. Using mock AI generated analysis for {source_ip}")
        # Pseudo-random logic to generate relevant sounding data
        return {
            "summary": f"This incident involves suspicious activity originating from {source_ip}. The correlated alerts and threat intelligence suggest a potential reconnaissance phase prior to an attack sequence.",
            "mitre_tactics": ["T1589 - Gather Victim Identity Information", "T1078 - Valid Accounts"],
            "remediation": "1. Block the indicator IP at the perimeter firewall.\\n2. Review authentication logs for the targeted user accounts.\\n3. Force password resets if any accounts show successful compromise."
        }

    def process_incidents(self):
        """Finds incidents ready for AI analysis and processes them."""
        print(f"[*] Running AI Analysis engine ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if incidents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'")
        if not cursor.fetchone():
            conn.close()
            return
            
        # Find incidents with TI data but no AI analysis
        cursor.execute('''
            SELECT * 
            FROM incidents 
            WHERE ti_updated_at IS NOT NULL AND ai_analyzed_at IS NULL
        ''')
        analyzable_incidents = cursor.fetchall()
        
        if not analyzable_incidents:
            conn.close()
            return
            
        print(f"[*] Found {len(analyzable_incidents)} incidents ready for AI Analysis.")
        
        for incident in analyzable_incidents:
            incident_id = incident[0]
            source_ip = incident[3]
            
            print(f"[*] Analyzing incident {incident_id}...")
            
            # Fetch associated alerts
            alerts = []
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
            if cursor.fetchone():
                cursor.execute("SELECT type, severity, description FROM alerts WHERE incident_id = ?", (incident_id,))
                alerts_data = cursor.fetchall()
                if alerts_data:
                     alerts = alerts_data
                 
            prompt = self.generate_prompt(incident, alerts)
            analysis_result = self.analyze_with_ai(prompt, source_ip)
            
            if analysis_result:
                summary = analysis_result.get("summary", "Analysis failed.")
                tactics = ", ".join(analysis_result.get("mitre_tactics", []))
                remediation = analysis_result.get("remediation", "Investigate manually.")
                
                cursor.execute('''
                    UPDATE incidents 
                    SET ai_summary = ?, mitre_tactics = ?, remediation_steps = ?, ai_analyzed_at = ?, status = 'Analyzed'
                    WHERE incident_id = ?
                ''', (summary, tactics, remediation, datetime.now().isoformat(), incident_id))
                
                print(f"[+] Successfully generated AI analysis for incident {incident_id}")
            
            # Rate limiting pause (important for real APIs)
            time.sleep(3)
                
        conn.commit()
        conn.close()

def start_ai_analyzer():
    analyzer = GeminiAnalyzer()
    print("[*] Gemini AI Analyzer started. Checking for enriched incidents every 3 minutes...")
    while True:
        try:
            analyzer.process_incidents()
            time.sleep(180)
        except KeyboardInterrupt:
            print("[*] Stopping Gemini AI Analyzer...")
            break
        except Exception as e:
            print(f"[-] Error in AI Analyzer loop: {e}")
            time.sleep(180)

if __name__ == "__main__":
    start_ai_analyzer()
