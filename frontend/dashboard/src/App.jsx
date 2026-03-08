import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, AlertTriangle, Activity, Database, Server, ChevronRight, X, User } from 'lucide-react';
import { formatDistanceToNow, parseISO } from 'date-fns';

const API_BASE = 'http://localhost:8000/api';

const fetchDashboardStats = async () => (await axios.get(`${API_BASE}/stats`)).data;
const fetchIncidents = async () => (await axios.get(`${API_BASE}/incidents`)).data;
const fetchIncidentDetails = async (id) => (await axios.get(`${API_BASE}/incidents/${id}`)).data;

function App() {
  const [stats, setStats] = useState({ total_incidents: 0, critical_incidents: 0, open_incidents: 0 });
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const statsData = await fetchDashboardStats();
        const incidentsData = await fetchIncidents();
        setStats(statsData);
        setIncidents(incidentsData);
      } catch (err) {
        console.error("Error loading SOC data", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
    const interval = setInterval(loadData, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const handleIncidentClick = async (id) => {
    try {
      const details = await fetchIncidentDetails(id);
      setSelectedIncident(details);
    } catch (err) {
      console.error("Failed to fetch incident details", err);
    }
  };

  const getSeverityColor = (sev) => {
    switch (sev?.toLowerCase()) {
      case 'critical': return 'text-[#FF4136] bg-[#FF4136]/10 border-[#FF4136]/30 shadow-[0_0_15px_rgba(255,65,54,0.3)] animate-pulse';
      case 'high': return 'text-[#FF851B] bg-[#FF851B]/10 border-[#FF851B]/30 shadow-[0_0_10px_rgba(255,133,27,0.2)]';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      default: return 'text-[#66FCF1] bg-[#66FCF1]/10 border-[#66FCF1]/30';
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navbar */}
      <header className="glass py-4 px-6 flex justify-between items-center sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Shield className="text-neonGreen w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-wider text-white">KAALI <span className="text-neonGreen text-sm ml-2">SOC PLATFORM</span></h1>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-neonGreen animate-pulse"></div> API Connected</div>
          <div className="flex items-center gap-2 bg-gray-800 px-3 py-1.5 rounded-full border border-gray-700">
            <User className="w-4 h-4 text-gray-400" />
            <span>Senior Analyst</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 absolute inset-0 top-[73px] overflow-hidden">

        {/* Left Column: Stats & Queue */}
        <div className={`col-span-12 lg:col-span-${selectedIncident ? '5' : '12'} flex flex-col gap-6 transition-all duration-500 overflow-y-auto pr-2 scrollbar-hide`}>

          {/* Stats Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="glass p-5 rounded-2xl flex items-center justify-between border-gray-700">
              <div>
                <p className="text-gray-400 text-sm font-medium uppercase tracking-wider">Total Incidents</p>
                <h3 className="text-3xl font-bold text-white mt-1">{stats.total_incidents}</h3>
              </div>
              <div className="bg-gray-800 p-3 rounded-xl"><Database className="w-6 h-6 text-mutedTeal" /></div>
            </div>

            <div className="glass p-5 rounded-2xl flex items-center justify-between border-alertRed/30">
              <div>
                <p className="text-alertRed text-sm font-medium uppercase tracking-wider">Critical Alerts</p>
                <h3 className="text-3xl font-bold text-white mt-1">{stats.critical_incidents}</h3>
              </div>
              <div className="bg-alertRed/10 p-3 rounded-xl"><AlertTriangle className="w-6 h-6 text-alertRed" /></div>
            </div>

            <div className="glass p-5 rounded-2xl flex items-center justify-between border-neonGreen/30">
              <div>
                <p className="text-neonGreen text-sm font-medium uppercase tracking-wider">Open Investigations</p>
                <h3 className="text-3xl font-bold text-white mt-1">{stats.open_incidents}</h3>
              </div>
              <div className="bg-neonGreen/10 p-3 rounded-xl"><Activity className="w-6 h-6 text-neonGreen" /></div>
            </div>
          </div>

          {/* Incident Queue */}
          <div className="glass rounded-2xl border-gray-700 flex-1 flex flex-col overflow-hidden">
            <div className="p-5 border-b border-gray-700/50 flex justify-between items-center bg-gray-800/30">
              <h2 className="text-lg font-semibold text-white tracking-wide">Active Incident Queue</h2>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-hide p-3">
              {loading ? (
                <div className="flex justify-center items-center h-40"><div className="w-8 h-8 border-4 border-neonGreen border-t-transparent rounded-full animate-spin"></div></div>
              ) : incidents.length === 0 ? (
                <div className="text-center text-gray-500 mt-10">No active incidents found.</div>
              ) : (
                <div className="flex flex-col gap-3">
                  {incidents.map(inc => (
                    <div
                      key={inc.incident_id}
                      onClick={() => handleIncidentClick(inc.incident_id)}
                      className={`glass hover:bg-gray-700/40 p-4 rounded-xl cursor-pointer transition-all border ${selectedIncident?.incident_id === inc.incident_id ? 'border-neonGreen shadow-[0_0_15px_rgba(102,252,241,0.15)]' : 'border-gray-700/50'}`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="text-white font-medium truncate pr-4">{inc.title}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs border uppercase tracking-wider font-semibold ${getSeverityColor(inc.severity)}`}>
                          {inc.severity}
                        </span>
                      </div>
                      <div className="flex justify-between items-end mt-4 text-xs text-gray-400">
                        <div className="flex items-center gap-1.5 bg-gray-900 px-2 py-1 rounded">
                          <Server className="w-3 h-3" /> {inc.source_ip}
                        </div>
                        <span className="flex items-center gap-1">
                          {inc.created_at ? formatDistanceToNow(parseISO(inc.created_at), { addSuffix: true }) : 'N/A'}
                          <ChevronRight className="w-3 h-3" />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Incident Details Slide-in */}
        {selectedIncident && (
          <div className="col-span-12 lg:col-span-7 glass rounded-2xl border-gray-700/80 overflow-hidden flex flex-col shadow-2xl animate-in slide-in-from-right-8 duration-300">
            {/* Header */}
            <div className="p-6 border-b border-gray-700/50 bg-gray-800/40 flex justify-between items-start relative">
              <div className="pr-10">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-bold text-white leading-tight">{selectedIncident.title}</h2>
                  <span className={`px-2.5 py-1 rounded text-xs border uppercase tracking-widest font-bold ${getSeverityColor(selectedIncident.severity)}`}>
                    {selectedIncident.severity}
                  </span>
                </div>
                <p className="text-gray-400 text-sm flex items-center gap-2">
                  <span className="font-mono bg-gray-900 px-1.5 rounded">{selectedIncident.incident_id}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedIncident(null)}
                className="p-2 hover:bg-gray-700 rounded-full transition-colors absolute right-4 top-4"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Details Body */}
            <div className="p-6 overflow-y-auto flex-1 scrollbar-hide space-y-8">

              {/* AI Analysis Section */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-5 bg-neonGreen rounded-full"></div>
                  <h3 className="text-lg font-semibold text-white uppercase tracking-wider">AI Executive Summary</h3>
                </div>
                <div className="bg-gray-900/50 p-5 rounded-xl border border-gray-800 leading-relaxed text-gray-300">
                  {selectedIncident.ai_summary ? (
                    <p>{selectedIncident.ai_summary}</p>
                  ) : (
                    <p className="italic text-gray-500">AI Analysis pending or unavailable.</p>
                  )}
                </div>
              </section>

              {/* Threat Intel & MITRE Grid */}
              <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-5 bg-alertRed rounded-full"></div>
                    <h3 className="text-lg font-semibold text-white uppercase tracking-wider">Threat Intel</h3>
                  </div>
                  <div className="bg-gray-900/50 p-5 rounded-xl border border-gray-800 h-full">
                    <div className="mb-4">
                      <div className="text-sm text-gray-400 mb-1">Source Target IP</div>
                      <div className="font-mono text-white text-lg">{selectedIncident.source_ip}</div>
                    </div>
                    {selectedIncident.ti_summary ? (
                      <div>
                        {selectedIncident.abuse_score > 50 ? (
                          <div className="text-alertRed font-semibold mb-2 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4" /> High Abuse Probability ({selectedIncident.abuse_score}/100)
                          </div>
                        ) : (
                          <div className="text-neonGreen font-semibold mb-2">Neutral/Benign Score ({selectedIncident.abuse_score || 0}/100)</div>
                        )}
                        <p className="text-sm text-gray-400 border-t border-gray-800 pt-3 mt-3">{selectedIncident.ti_summary}</p>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">No TI profile currently synced.</p>
                    )}
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-1.5 h-5 bg-blue-500 rounded-full"></div>
                    <h3 className="text-lg font-semibold text-white uppercase tracking-wider">MITRE ATT&CK</h3>
                  </div>
                  <div className="bg-gray-900/50 p-5 rounded-xl border border-gray-800 h-full">
                    {selectedIncident.mitre_tactics && selectedIncident.mitre_tactics.length > 0 ? (
                      <ul className="space-y-2">
                        {selectedIncident.mitre_tactics.map((tactic, i) => (
                          <li key={i} className="bg-blue-500/10 border border-blue-500/20 text-blue-400 px-3 py-2 rounded text-sm">
                            {tactic}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-500 text-sm italic">Not mapped.</p>
                    )}
                  </div>
                </div>
              </section>

              {/* Remediation */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-5 bg-warnOrange rounded-full"></div>
                  <h3 className="text-lg font-semibold text-white uppercase tracking-wider">Recommended Remediation</h3>
                </div>
                <div className="bg-gray-900/50 p-5 rounded-xl border border-gray-800">
                  {selectedIncident.remediation_steps ? (
                    <pre className="whitespace-pre-wrap font-cyber text-gray-300 text-sm leading-relaxed">
                      {selectedIncident.remediation_steps}
                    </pre>
                  ) : (
                    <p className="italic text-gray-500">Pending AI remediation guidelines.</p>
                  )}
                </div>
              </section>

              {/* Raw Alerts Table */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-5 bg-gray-500 rounded-full"></div>
                  <h3 className="text-lg font-semibold text-white uppercase tracking-wider">Correlated Alerts</h3>
                </div>
                <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-400 bg-gray-800/50 uppercase border-b border-gray-800">
                      <tr>
                        <th className="px-4 py-3">Time</th>
                        <th className="px-4 py-3">Type</th>
                        <th className="px-4 py-3">Severity</th>
                        <th className="px-4 py-3">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedIncident.alerts && selectedIncident.alerts.length > 0 ? (
                        selectedIncident.alerts.map(alert => (
                          <tr key={alert.alert_id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                            <td className="px-4 py-3 text-gray-400 whitespace-nowrap">{new Date(alert.timestamp).toLocaleTimeString()}</td>
                            <td className="px-4 py-3 font-medium text-gray-300">{alert.type}</td>
                            <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${getSeverityColor(alert.severity)}`}>{alert.severity}</span></td>
                            <td className="px-4 py-3 text-gray-400">{alert.description}</td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="4" className="px-4 py-6 text-center text-gray-500">No raw alerts found.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
