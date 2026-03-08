from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os

app = FastAPI(title="KAALI SOC API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(base_dir, "database", "kaali.db")

def get_db_connection():
    if not os.path.exists(db_path):
        raise HTTPException(status_code=500, detail="Database not found")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

@app.get("/api/stats")
def get_dashboard_stats():
    """Returns high-level statistics for the dashboard overview."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total incidents
        cursor.execute("SELECT COUNT(*) FROM incidents")
        total_incidents = cursor.fetchone()[0]
        
        # Critical incidents
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'Critical'")
        critical_incidents = cursor.fetchone()[0]
        
        # Open incidents (assuming status not 'Closed')
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status != 'Closed'")
        open_incidents = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_incidents": total_incidents,
            "critical_incidents": critical_incidents,
            "open_incidents": open_incidents
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents")
def get_incidents():
    """Returns a list of all incidents."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT incident_id, title, severity, source_ip, status, created_at, updated_at
            FROM incidents
            ORDER BY datetime(created_at) DESC
        ''')
        incidents = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return incidents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incidents/{incident_id}")
def get_incident_details(incident_id: str):
    """Returns full details of a specific incident, including alerts and AI analysis."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
        incident_row = cursor.fetchone()
        
        if not incident_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Incident not found")
            
        incident = dict(incident_row)
        
        # Fetch associated alerts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
        if cursor.fetchone():
            cursor.execute('''
                SELECT alert_id, type, severity, description, timestamp
                FROM alerts 
                WHERE incident_id = ?
                ORDER BY datetime(timestamp) DESC
            ''', (incident_id,))
            alerts = [dict(row) for row in cursor.fetchall()]
        else:
            alerts = []
            
        incident["alerts"] = alerts
        
        # Convert mitre tactics from string to list if present
        if incident.get("mitre_tactics"):
            incident["mitre_tactics"] = [t.strip() for t in incident["mitre_tactics"].split(",")]
        
        conn.close()
        return incident
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
