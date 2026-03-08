# KAALI (Knowledge-based AI Assistant for Log Investigation)

KAALI – AI Powered SOC Alert Correlation & Investigation Assistant. KAALI analyzes security logs, detects suspicious activity, correlates alerts, integrates threat intelligence, and uses AI to explain cyber attacks and recommend response actions. Built to simulate real SOC workflows using Python, FastAPI, Elasticsearch, and AI models.

## 🏗️ Architecture Overview

The KAALI system is divided into modular components to handle the entire lifecycle of a security event.

### 1. Log Ingestion Engine (`backend/log_ingestion`)
Parses raw text logs (like Linux `auth.log` or Suricata IDS logs) in real-time, extracts key fields via regex, and forwards them as structured JSON documents into Elasticsearch. 

### 2. Alert Detection Engine (`backend/api` - *To be developed*)
Periodically queries structured logs to find anomalies or known-bad patterns (e.g., repeating failed logins from a single IP indicative of Brute Force attacks), creating **Alerts** in a local SQLite database.

### 3. Alert Correlation Engine (`backend/correlation_engine`)
Operates on the Alerts table to detect multi-stage attack scenarios. For instance, linking a sequence of failed logins followed by a successful login into a single **Account Compromise Incident**.

### 4. Threat Intelligence Integration (`backend/threat_intel`)
Automatically investigates the IPs and indicators found in Incidents by querying external reputation APIs like **AbuseIPDB** and **VirusTotal**, augmenting the Incident with threat context.

### 5. AI Incident Explanation (`backend/ai_analysis`)
Once an Incident is enriched with Threat Intel, the entire context is sent to the **Google Gemini API**. Gemini acts as an autonomous Senior SOC Analyst, producing an executive summary, mapping to the MITRE ATT&CK framework, and providing actionable remediation steps.

### 6. SOC Dashboard (`frontend/dashboard`)
A React (Tailwind CSS) frontend for human analysts to review statistics, investigate Incidents, read AI summaries, and monitor metrics via an intuitive user interface.

### 7. Automation & Response (`scripts` and backend)
Takes defensive action against critical incidents, such as modifying `iptables` to block attacker IPs and sending email notifications to administrators.

## 🚀 Getting Started

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy the `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```
