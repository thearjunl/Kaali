import os
import re
import time
import json
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from elasticsearch_connector import ElasticsearchConnector

# Log patterns
# Example auth.log: "Mar  8 12:34:56 hostname sshd[1234]: Failed password for invalid user root from 192.168.1.5 port 22 ssh2"
# Example auth.log: "Mar  8 12:34:56 hostname sshd[1234]: Accepted password for admin from 10.0.0.5 port 22 ssh2"
# Example suricata: "03/08/2026-12:34:56.123456  [**] [1:2010935:2] ET EXPLOIT Possible CVE-2014-6271 [**] [Classification: Attempted Administrator Privilege Gain] [Priority: 1] {TCP} 192.168.1.10:54321 -> 10.0.0.5:80"

AUTH_LOG_REGEX = re.compile(
    r'(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}).*sshd\[\d+\]:\s+(?P<action>Failed|Accepted)\s+password\s+for\s+(?:invalid\s+user\s+)?(?P<username>\w+)\s+from\s+(?P<source_ip>\d+\.\d+\.\d+\.\d+)'
)

SURICATA_REGEX = re.compile(
    r'(?P<timestamp>\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+).*\[\*\*\]\s+\[\d+:\d+:\d+\]\s+(?P<event_type>[^\[]+)\s+\[\*\*\]\s+\[Classification:\s+(?P<classification>[^\]]+)\].*?\{\w+\}\s+(?P<source_ip>\d+\.\d+\.\d+\.\d+):\d+\s+->\s+(?P<dest_ip>\d+\.\d+\.\d+\.\d+)'
)

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, filepath, log_type, es_connector):
        self.filepath = filepath
        self.log_type = log_type
        self.es_connector = es_connector
        self.file_pos = 0
        self._set_initial_position()

    def _set_initial_position(self):
        """Set the file pointer to the end of the file, or 0 if it doesn't exist yet."""
        if os.path.exists(self.filepath):
            self.file_pos = os.path.getsize(self.filepath)
        else:
            self.file_pos = 0
            
    def process_new_lines(self):
        """Reads new lines from the tracked file."""
        if not os.path.exists(self.filepath):
            return

        try:
            # Handle log rotation: if current file is smaller than our pointer, it rotated
            if os.path.getsize(self.filepath) < self.file_pos:
                self.file_pos = 0

            with open(self.filepath, 'r') as f:
                f.seek(self.file_pos)
                new_lines = f.readlines()
                self.file_pos = f.tell()

            for line in new_lines:
                self.parse_and_index(line.strip())
        except Exception as e:
            print(f"[-] Error reading {self.filepath}: {e}")

    def parse_and_index(self, line):
        if not line: return
        
        parsed_data = None
        
        if self.log_type == "auth":
            match = AUTH_LOG_REGEX.search(line)
            if match:
                data = match.groupdict()
                status = "failed" if data["action"] == "Failed" else "success"
                event_type = "failed_login" if status == "failed" else "accepted_login"
                
                # We need an ISO 8601 timestamp for elasticsearch (simple approximation using current year)
                current_year = datetime.now().year
                dt_str = f"{current_year} {data['timestamp']}"
                try:
                    dt_obj = datetime.strptime(dt_str, "%Y %b %d %H:%M:%S")
                    iso_timestamp = dt_obj.isoformat()
                except ValueError:
                    iso_timestamp = datetime.now().isoformat()
                    
                parsed_data = {
                    "timestamp": iso_timestamp,
                    "source_ip": data["source_ip"],
                    "username": data["username"],
                    "event_type": event_type,
                    "status": status,
                    "raw_log": line
                }
                
        elif self.log_type == "suricata":
            match = SURICATA_REGEX.search(line)
            if match:
                data = match.groupdict()
                
                try:
                    dt_obj = datetime.strptime(data["timestamp"], "%m/%d/%Y-%H:%M:%S.%f")
                    iso_timestamp = dt_obj.isoformat()
                except ValueError:
                    iso_timestamp = datetime.now().isoformat()
                    
                parsed_data = {
                    "timestamp": iso_timestamp,
                    "source_ip": data["source_ip"],
                    "username": "N/A",  # Suricata events usually don't have usernames
                    "event_type": data["event_type"].strip(),
                    "status": "alert",
                    "raw_log": line
                }

        if parsed_data:
            print(f"[+] Parsed {self.log_type} log: {parsed_data['event_type']} from {parsed_data['source_ip']}")
            self.es_connector.index_log(parsed_data)

    def on_modified(self, event):
        if event.src_path == self.filepath:
            self.process_new_lines()
            
    def on_created(self, event):
        if event.src_path == self.filepath:
            self.file_pos = 0
            self.process_new_lines()

def start_log_monitoring():
    es_connector = ElasticsearchConnector()
    
    # We will monitor these directories/files
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    default_auth_log = os.path.join(base_dir, "mock_logs", "auth.log")
    default_suricata_log = os.path.join(base_dir, "mock_logs", "suricata_fast.log")
    
    auth_log_path = os.getenv("AUTH_LOG_PATH", default_auth_log)
    suricata_log_path = os.getenv("SURICATA_LOG_PATH", default_suricata_log)
    
    # Ensure directories exist for testing
    os.makedirs(os.path.dirname(auth_log_path), exist_ok=True)
    os.makedirs(os.path.dirname(suricata_log_path), exist_ok=True)
    
    # Touch files if they don't exist
    if not os.path.exists(auth_log_path): open(auth_log_path, 'a').close()
    if not os.path.exists(suricata_log_path): open(suricata_log_path, 'a').close()

    observer = Observer()
    
    # Setup handlers
    auth_handler = LogFileHandler(auth_log_path, "auth", es_connector)
    suricata_handler = LogFileHandler(suricata_log_path, "suricata", es_connector)
    
    auth_dir = os.path.dirname(auth_log_path)
    suricata_dir = os.path.dirname(suricata_log_path)
    
    observer.schedule(auth_handler, path=auth_dir, recursive=False)
    if auth_dir != suricata_dir:
        observer.schedule(suricata_handler, path=suricata_dir, recursive=False)
    else:
        # If in same directory, we need a combined handler or watchdog will override the schedule
        pass

    observer.start()
    print("[*] Log Ingestion Engine started. Monitoring logs...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("[*] Stopping Log Ingestion Engine...")
    observer.join()

if __name__ == "__main__":
    start_log_monitoring()
