import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Pause, RefreshCw, Cpu, Activity, AlertTriangle, CheckCircle, 
  Sparkles, ShieldAlert, Wrench, BarChart2, MessageSquare, Database, ListFilter, Send
} from 'lucide-react';
import './App.css';

// Endpoint mapping to Flask server
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:5000/api';

// ==========================================
// TELEMETRY CHART COMPONENT
// ==========================================
// A custom SVG line chart that auto-scales values and draws neon graphs.
// Highly stable and independent of heavy visual JS charting libraries.
const TelemetryChart = ({ data, dataKey, label, color, baseline }) => {
  if (!data || data.length === 0) {
    return (
      <div className="chart-placeholder">
        <span>Awaiting telemetry stream...</span>
      </div>
    );
  }

  const padding = { top: 20, right: 15, bottom: 20, left: 45 };
  const width = 380;
  const height = 150;

  // Extract values to scale axes
  const values = data.map(d => d[dataKey] || 0);
  let minVal = Math.min(...values);
  let maxVal = Math.max(...values);
  
  if (baseline !== undefined) {
    minVal = Math.min(minVal, baseline);
    maxVal = Math.max(maxVal, baseline);
  }

  const range = maxVal - minVal;
  const yMin = minVal - (range * 0.1 || 1);
  const yMax = maxVal + (range * 0.1 || 1);

  // Map data to SVG points
  const points = data.map((d, i) => {
    const x = padding.left + (i / (data.length - 1)) * (width - padding.left - padding.right);
    const y = padding.top + (1 - (d[dataKey] - yMin) / (yMax - yMin)) * (height - padding.top - padding.bottom);
    return { x, y, val: d[dataKey] };
  });

  const pathD = points.reduce((acc, p, i) => {
    return i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  const areaD = points.length > 0 
    ? `${pathD} L ${points[points.length - 1].x} ${height - padding.bottom} L ${points[0].x} ${height - padding.bottom} Z`
    : '';

  // Calculate 3 grid ticks on Y axis
  const gridLines = [yMin + (yMax - yMin) * 0.25, yMin + (yMax - yMin) * 0.5, yMin + (yMax - yMin) * 0.75];

  return (
    <div className="chart-box">
      <div className="chart-title">
        <span>{label}</span>
        <span className={`value-text ${color}`}>{points[points.length - 1]?.val.toFixed(2)}</span>
      </div>
      <div className="chart-wrapper">
        <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
          <defs>
            <linearGradient id={`${dataKey}-gradient`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={`var(--color-${color})`} stopOpacity="0.15" />
              <stop offset="100%" stopColor={`var(--color-${color})`} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          
          {/* Horizontal grid markings */}
          {gridLines.map((yVal, idx) => {
            const y = padding.top + (1 - (yVal - yMin) / (yMax - yMin)) * (height - padding.top - padding.bottom);
            return (
              <g key={idx}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="chart-grid-line" />
                <text x={padding.left - 8} y={y + 3} className="chart-axis-label" textAnchor="end">
                  {yVal.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Area shade */}
          <path d={areaD} fill={`url(#${dataKey}-gradient)`} />

          {/* Baseline limit line */}
          {baseline !== undefined && (
            <line 
              x1={padding.left} 
              y1={padding.top + (1 - (baseline - yMin) / (yMax - yMin)) * (height - padding.top - padding.bottom)} 
              x2={width - padding.right} 
              y2={padding.top + (1 - (baseline - yMin) / (yMax - yMin)) * (height - padding.top - padding.bottom)} 
              stroke="#475569" 
              strokeDasharray="4 4" 
              opacity="0.6"
            />
          )}

          {/* Main neon line */}
          <path d={pathD} className={`chart-line ${color}`} />

          {/* Endpoint highlight dot */}
          {points.length > 0 && (
            <circle 
              cx={points[points.length - 1].x} 
              cy={points[points.length - 1].y} 
              r="4" 
              fill={`var(--color-${color})`} 
            />
          )}
        </svg>
      </div>
    </div>
  );
};

// ==========================================
// MAIN APP COMPONENT
// ==========================================
export default function App() {
  // Navigation Router state
  const [activeTab, setActiveTab] = useState('fleet'); // fleet, twin, whatif, chat, dataset

  // Fleet data states
  const [fleet, setFleet] = useState([]);
  const [stats, setStats] = useState({
    total_engines: 0,
    average_rul: 0,
    average_health: 0,
    critical_count: 0,
    warning_count: 0,
    healthy_count: 0
  });
  
  // Selection states
  const [selectedEngineId, setSelectedEngineId] = useState(1);
  const [engineData, setEngineData] = useState(null);
  
  // Simulation control
  const [simPlaying, setSimPlaying] = useState(false);
  const simRef = useRef(null);

  // Chatbot conversation state
  const [chatMessages, setChatMessages] = useState([
    { sender: 'assistant', text: 'Hello! I am your AeroGuard AI Copilot. Select an engine, and ask me any questions about its telemetry anomalies, remaining useful life, or recommend maintenance procedures.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatBottomRef = useRef(null);

  // Raw Dataset Explorer states
  const [rawDataset, setRawDataset] = useState([]);
  const [datasetPage, setDatasetPage] = useState(1);
  const [datasetTotalPages, setDatasetTotalPages] = useState(1);
  const [datasetFilterUnit, setDatasetFilterUnit] = useState('all');
  const [datasetLoading, setDatasetLoading] = useState(false);

  // What-If result alert state
  const [whatIfAlert, setWhatIfAlert] = useState(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);

  // Auto-scroll chat box when new message arrives
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Fetch Fleet overview
  const fetchFleet = async () => {
    try {
      const res = await fetch(`${API_BASE}/fleet`);
      const data = await res.json();
      setFleet(data.engines || []);
      setStats(data.stats || {});
    } catch (err) {
      console.error("Error loading fleet stats:", err);
    }
  };

  // Fetch telemetry history for selected engine
  const fetchEngineData = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/engine/${id}`);
      const data = await res.json();
      setEngineData(data);
    } catch (err) {
      console.error(`Error loading details for engine ${id}:`, err);
    }
  };

  // Fetch raw dataset rows
  const fetchDataset = async () => {
    setDatasetLoading(true);
    try {
      let url = `${API_BASE}/dataset?page=${datasetPage}&page_size=12`;
      if (datasetFilterUnit !== 'all') {
        url += `&unit_number=${datasetFilterUnit}`;
      }
      const res = await fetch(url);
      const data = await res.json();
      setRawDataset(data.data || []);
      setDatasetTotalPages(data.pages || 1);
    } catch (err) {
      console.error("Error loading raw dataset:", err);
    } finally {
      setDatasetLoading(false);
    }
  };

  // Run simulation tick (advances operational cycle by 1)
  const handleSimulationTick = async () => {
    try {
      await fetch(`${API_BASE}/fleet/tick`, { method: 'POST' });
      await fetchFleet();
      if (selectedEngineId) {
        await fetchEngineData(selectedEngineId);
      }
    } catch (err) {
      console.error("Simulation tick failed:", err);
    }
  };

  // Reset fleet simulation status
  const resetSimulation = async () => {
    setSimPlaying(false);
    try {
      await fetch(`${API_BASE}/fleet/reset`, { method: 'POST' });
      await fetchFleet();
      if (selectedEngineId) {
        await fetchEngineData(selectedEngineId);
      }
      setChatMessages([
        { sender: 'assistant', text: `Simulation reset. Engine #${selectedEngineId} is re-initialized. What telemetry should we explore?` }
      ]);
      setWhatIfAlert(null);
    } catch (err) {
      console.error("Reset failed:", err);
    }
  };

  // Send message to the interactive chatbot endpoint
  const sendChatMessage = async (customText = null) => {
    const textToSend = customText || chatInput;
    if (!textToSend.trim() || chatLoading) return;

    // Append user bubble
    const updatedMessages = [...chatMessages, { sender: 'user', text: textToSend }];
    setChatMessages(updatedMessages);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/copilot/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unit_number: selectedEngineId,
          messages: updatedMessages
        })
      });
      const data = await res.json();
      
      // Append assistant bubble
      setChatMessages(prev => [...prev, { sender: 'assistant', text: data.reply || 'Diagnostics offline. Verify server API connection.' }]);
    } catch (err) {
      console.error("Chat failure:", err);
      setChatMessages(prev => [...prev, { sender: 'assistant', text: 'Connection issue. Could not reach Copilot gateway.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Run What-If maintenance scenarios
  const triggerWhatIfScenario = async (type) => {
    setWhatIfLoading(true);
    setWhatIfAlert(null);
    try {
      const res = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit_number: selectedEngineId, type })
      });
      const data = await res.json();
      if (data.success) {
        setWhatIfAlert({
          type,
          extended: data.extended_cycles,
          desc: data.description,
          before: data.before,
          after: data.after
        });
        await fetchEngineData(selectedEngineId);
        await fetchFleet();
      }
    } catch (err) {
      console.error("What-if execution error:", err);
    } finally {
      setWhatIfLoading(false);
    }
  };

  // Fetch initial fleet overview
  useEffect(() => {
    fetchFleet();
  }, []);

  // Fetch engine details when ID changes
  useEffect(() => {
    if (selectedEngineId) {
      fetchEngineData(selectedEngineId);
    }
  }, [selectedEngineId]);

  // Fetch dataset explorer page when filters or pages change
  useEffect(() => {
    if (activeTab === 'dataset') {
      fetchDataset();
    }
  }, [activeTab, datasetPage, datasetFilterUnit]);

  // Play/Pause ticker hook
  useEffect(() => {
    if (simPlaying) {
      simRef.current = setInterval(handleSimulationTick, 2000);
    } else {
      if (simRef.current) clearInterval(simRef.current);
    }
    return () => {
      if (simRef.current) clearInterval(simRef.current);
    };
  }, [simPlaying, selectedEngineId]);

  const activeMetadata = engineData?.metadata || {};
  const activeAnomalies = engineData?.anomalies || [];
  const telemetryHistory = engineData?.telemetry_history || [];

  // ==========================================
  // VIEW RENDERING: 1. FLEET OVERVIEW
  // ==========================================
  const renderFleetOverview = () => {
    return (
      <div className="tab-view-container animate-fade">
        <div className="view-header">
          <h2>Active Fleet Asset Queue</h2>
          <p>Double-click or click "Analyze" on any engine to view its Digital Twin details.</p>
        </div>
        
        <div className="table-wrapper glass-panel">
          <table className="fleet-table">
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Status</th>
                <th>Cycles Completed</th>
                <th>Predicted RUL</th>
                <th>Health Index</th>
                <th>Urgency Priority</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {fleet.map((engine) => (
                <tr 
                  key={engine.unit_number} 
                  className={selectedEngineId === engine.unit_number ? 'selected-row' : ''}
                  onClick={() => setSelectedEngineId(engine.unit_number)}
                >
                  <td className="font-mono">Engine #{engine.unit_number}</td>
                  <td>
                    <span className={`badge-risk ${engine.risk_level.toLowerCase()}`}>
                      {engine.risk_level}
                    </span>
                  </td>
                  <td className="font-mono">{engine.current_cycle}</td>
                  <td className="font-mono">{engine.predicted_rul} cycles</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div className="progress-bar-bg">
                        <div 
                          className={`progress-bar-fill ${engine.risk_level.toLowerCase()}`} 
                          style={{ width: `${engine.health_score}%` }}
                        ></div>
                      </div>
                      <span className="font-mono">{engine.health_score}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge-priority ${engine.priority.toLowerCase()}`}>
                      {engine.priority}
                    </span>
                  </td>
                  <td>
                    <button 
                      className="btn-action-sm"
                      onClick={() => {
                        setSelectedEngineId(engine.unit_number);
                        setActiveTab('twin');
                      }}
                    >
                      Analyze Twin
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ==========================================
  // VIEW RENDERING: 2. DIGITAL TWIN ANALYST
  // ==========================================
  const renderDigitalTwin = () => {
    return (
      <div className="tab-view-container animate-fade split-layout">
        {/* Left Column: Asset selector & Digital Twin */}
        <div className="left-panel">
          <div className="card-header glass-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span className="panel-label">Asset Explorer</span>
                <select 
                  className="dropdown-selector"
                  value={selectedEngineId}
                  onChange={(e) => setSelectedEngineId(Number(e.target.value))}
                >
                  {fleet.map(e => (
                    <option key={e.unit_number} value={e.unit_number}>Engine #{e.unit_number}</option>
                  ))}
                </select>
              </div>
              <span className="badge-risk healthy font-mono">CYCLE {activeMetadata.current_cycle}</span>
            </div>

            {/* Interactive schematic visualizer */}
            <div className="digital-twin-canvas" style={{ marginTop: '24px' }}>
              <div className="twin-schematic">
                <svg viewBox="0 0 500 160" className="schematic-svg">
                  <rect x="50" y="45" width="400" height="70" rx="35" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="3" />
                  <path d="M 30,30 L 70,45 L 70,115 L 30,130 Z" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="2" />
                  <path d="M 430,45 L 470,30 L 470,130 L 430,115 Z" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="2" />
                  <line x1="50" y1="80" x2="450" y2="80" stroke="rgba(255,255,255,0.3)" strokeWidth="2" strokeDasharray="5 5" />
                  <line x1="120" y1="47" x2="120" y2="113" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
                  <line x1="160" y1="47" x2="160" y2="113" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
                  <line x1="260" y1="47" x2="260" y2="113" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
                  <line x1="360" y1="47" x2="360" y2="113" stroke="rgba(255,255,255,0.15)" strokeWidth="2" />
                </svg>
                
                <div className={`diagnostic-ring ring-lpc ${activeMetadata.risk_level?.toLowerCase() || 'healthy'}`}></div>
                <div className={`diagnostic-ring ring-hpc ${activeMetadata.risk_level?.toLowerCase() || 'healthy'}`}></div>
                <div className={`diagnostic-ring ring-lpt ${activeMetadata.risk_level?.toLowerCase() || 'healthy'}`}></div>

                <div className="sensor-callout callout-lpc">LPC Fan</div>
                <div className="sensor-callout callout-hpc">HPC Compressor</div>
                <div className="sensor-callout callout-lpt">LPT Exhaust</div>
              </div>
            </div>
            
            {/* Asset quick status cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '24px' }}>
              <div className="glass-panel" style={{ padding: '12px 16px' }}>
                <span className="stat-label">Predicted RUL</span>
                <h3 className="font-mono text-cyan" style={{ fontSize: '1.5rem', marginTop: '4px' }}>{activeMetadata.predicted_rul} cycles</h3>
              </div>
              <div className="glass-panel" style={{ padding: '12px 16px' }}>
                <span className="stat-label">Health score</span>
                <h3 className="font-mono text-green" style={{ fontSize: '1.5rem', marginTop: '4px' }}>{activeMetadata.health_score}%</h3>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Telemetry curves & anomalies */}
        <div className="right-panel">
          <div className="card-header glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
            <h3>Telemetry Waveform Curves</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <TelemetryChart 
                data={telemetryHistory} 
                dataKey="sensor_3" 
                label="T30 Exhaust Temp (Combustion Heat)" 
                color="indigo" 
                baseline={1589.0}
              />
              <TelemetryChart 
                data={telemetryHistory} 
                dataKey="sensor_7" 
                label="P30 Core Pressure (Internal Airflow)" 
                color="cyan" 
                baseline={554.0}
              />
            </div>

            {/* Anomaly alarms */}
            <div style={{ marginTop: 'auto' }}>
              <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                <ShieldAlert size={14} style={{ color: 'var(--color-red)' }} />
                <span>ACTIVE SENSOR ANOMALY ALARMS</span>
              </h4>
              {activeAnomalies.length > 0 ? (
                <div className="anomalies-list">
                  {activeAnomalies.map((anom, idx) => (
                    <div className="anomaly-alert-card" key={idx}>
                      <span className="anomaly-alert-name">{anom.label}</span>
                      <span className="anomaly-alert-dev">{anom.deviation_pct > 0 ? '+' : ''}{anom.deviation_pct}% deviation</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '10px', background: 'rgba(255,255,255,0.01)', border: '1px dashed rgba(255,255,255,0.05)', borderRadius: '6px', textAlign: 'center' }}>
                  No sensor drift flags triggered. Core pressures stable.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ==========================================
  // VIEW RENDERING: 3. WHAT-IF SANDBOX
  // ==========================================
  const renderWhatIfSandbox = () => {
    return (
      <div className="tab-view-container animate-fade split-layout">
        
        {/* Left Column: Maintenance actions selection */}
        <div className="left-panel">
          <div className="card-header glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <span className="panel-label">Target Asset</span>
              <select 
                className="dropdown-selector"
                value={selectedEngineId}
                onChange={(e) => setSelectedEngineId(Number(e.target.value))}
              >
                {fleet.map(e => (
                  <option key={e.unit_number} value={e.unit_number}>Engine #{e.unit_number}</option>
                ))}
              </select>
            </div>

            <h3 style={{ marginTop: '12px' }}>Simulate Preventative Servicing</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Choose a repair action to apply to Engine #{selectedEngineId}. Our ML pipeline will instantly project the new lifetime metrics.
            </p>
            
            <div className="sim-actions" style={{ marginTop: '12px' }}>
              <button 
                className="btn-action-card" 
                onClick={() => triggerWhatIfScenario('compressor_wash')}
                disabled={whatIfLoading}
              >
                <div className="action-title">
                  <span>Compressor Core Wash</span>
                  <span className="action-impact">+35 Cycles</span>
                </div>
                <div className="action-desc">Flushes carbon deposits. Lowers core exhaust temperatures.</div>
              </button>

              <button 
                className="btn-action-card" 
                onClick={() => triggerWhatIfScenario('bearing_replace')}
                disabled={whatIfLoading}
              >
                <div className="action-title">
                  <span>Main Shaft Bearing Replacement</span>
                  <span className="action-impact">+60 Cycles</span>
                </div>
                <div className="action-desc">Swaps main bearings. Minimizes core shaft vibrations.</div>
              </button>

              <button 
                className="btn-action-card" 
                onClick={() => triggerWhatIfScenario('core_overhaul')}
                disabled={whatIfLoading}
              >
                <div className="action-title">
                  <span>Full Engine Core Overhaul</span>
                  <span className="action-impact">Reset to 100% Health</span>
                </div>
                <div className="action-desc">Performs rebuild. Resets sensor wear factors back to pristine levels.</div>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Comparison results */}
        <div className="right-panel">
          <div className="card-header glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {!whatIfAlert ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px' }}>
                <Wrench size={36} style={{ color: 'rgba(255,255,255,0.1)', marginBottom: '16px' }} />
                <h3>No maintenance simulated yet.</h3>
                <p style={{ fontSize: '0.75rem', marginTop: '6px' }}>Select an action on the left to see comparative lifespan changes.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', animation: 'fade-in 0.4s' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-green)' }}>
                  <CheckCircle size={20} />
                  <h3 style={{ textTransform: 'uppercase' }}>Simulation Completed</h3>
                </div>
                
                <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                  <strong style={{ display: 'block', fontSize: '0.85rem', color: 'white' }}>Action Performed:</strong>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{whatIfAlert.desc}</span>
                </div>

                <div className="sim-comparison-grid">
                  <div className="comparison-box before">
                    <span className="label">PRE-MAINTENANCE</span>
                    <div className="val font-mono">{whatIfAlert.before.predicted_rul}c</div>
                    <span className="desc">RUL Remaining</span>
                    <div className="sub font-mono">{whatIfAlert.before.health_score}% health</div>
                  </div>

                  <div className="comparison-box after">
                    <span className="label">POST-MAINTENANCE</span>
                    <div className="val font-mono text-green">{whatIfAlert.after.predicted_rul}c</div>
                    <span className="desc text-green">RUL Projected</span>
                    <div className="sub font-mono text-green">{whatIfAlert.after.health_score}% health</div>
                  </div>
                </div>

                <div style={{ textAlign: 'center', padding: '12px', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '8px', color: 'var(--color-green)', fontWeight: 700, fontSize: '0.85rem' }}>
                  Lifespan extended by {whatIfAlert.extended} cycles!
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ==========================================
  // VIEW RENDERING: 4. AI COPILOT CHATBOT
  // ==========================================
  const renderAICopilot = () => {
    // Quick template questions
    const quickPrompts = [
      { text: "Why is this engine critical?", query: "Why is Engine health critical at this cycle?" },
      { text: "How does compressor wash help?", query: "Can you explain how a compressor wash extends predicted RUL?" },
      { text: "Explain sensor 11 static pressure", query: "What is Sensor 11 static pressure, and why does it drift?" },
      { text: "Draft servicing schedule", query: "Draft a recommended servicing plan based on current sensor deviations." }
    ];

    return (
      <div className="tab-view-container animate-fade chat-tab-layout">
        <div className="chat-control-header glass-panel">
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <span className="panel-label">Asset Focus</span>
            <select 
              className="dropdown-selector"
              value={selectedEngineId}
              onChange={(e) => {
                setSelectedEngineId(Number(e.target.value));
                setChatMessages([
                  { sender: 'assistant', text: `Loaded Engine #${e.target.value} metrics. Let me know what diagnostics you need.` }
                ]);
              }}
            >
              {fleet.map(e => (
                <option key={e.unit_number} value={e.unit_number}>Engine #{e.unit_number}</option>
              ))}
            </select>
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>GEMINI COGNITIVE INTERFACE</span>
        </div>

        {/* Chat History Panel */}
        <div className="chat-interface-card glass-panel">
          
          {/* Quick chips templates */}
          <div className="chat-chips-row">
            {quickPrompts.map((p, idx) => (
              <button 
                key={idx} 
                className="chip-btn" 
                onClick={() => sendChatMessage(p.query)}
                disabled={chatLoading}
              >
                {p.text}
              </button>
            ))}
          </div>

          {/* Messages list */}
          <div className="chat-log-body">
            {chatMessages.map((m, idx) => (
              <div key={idx} className={`chat-message-bubble ${m.sender}`}>
                <div className="bubble-avatar">
                  {m.sender === 'user' ? 'U' : <Sparkles size={12} fill="var(--color-cyan)" />}
                </div>
                <div className="bubble-content">
                  {m.text.split('\n').map((line, lIdx) => {
                    const cleanLine = line.trim();
                    // Basic parse of bullet headers
                    if (cleanLine.startsWith('* **') || cleanLine.startsWith('- **')) {
                      const boldMatch = cleanLine.match(/[\*\-]\s+\*\*(.*?)\*\*:(.*)/);
                      if (boldMatch) {
                        return (
                          <div key={lIdx} style={{ display: 'flex', gap: '8px', margin: '4px 0' }}>
                            <span style={{ color: 'var(--color-cyan)' }}>•</span>
                            <span>
                              <strong>{boldMatch[1]}:</strong> {boldMatch[2]}
                            </span>
                          </div>
                        );
                      }
                    }
                    return <p key={lIdx} style={{ margin: '0 0 6px 0' }}>{line}</p>;
                  })}
                </div>
              </div>
            ))}
            
            {chatLoading && (
              <div className="chat-message-bubble assistant loading">
                <div className="bubble-avatar">
                  <Activity size={12} className="spinner" style={{ color: 'var(--color-cyan)' }} />
                </div>
                <div className="bubble-content font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  AeroGuard Copilot reasoning...
                </div>
              </div>
            )}
            
            <div ref={chatBottomRef} />
          </div>

          {/* Send Input Bar */}
          <div className="chat-input-bar">
            <input 
              type="text" 
              className="chat-text-input"
              placeholder="Ask the AI maintenance bot (e.g. why is exhaust temp rising?)..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') sendChatMessage();
              }}
              disabled={chatLoading}
            />
            <button 
              className="btn-send-chat" 
              onClick={() => sendChatMessage()}
              disabled={chatLoading || !chatInput.trim()}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    );
  };

  // ==========================================
  // VIEW RENDERING: 5. RAW DATASET EXPLORER
  // ==========================================
  const renderDatasetExplorer = () => {
    return (
      <div className="tab-view-container animate-fade">
        <div className="view-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '16px' }}>
          <div>
            <h2>NASA CMAPSS Dataset Viewer</h2>
            <p>Inspect raw sensor timeseries telemetry lines used to train our XGBoost model.</p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Filter Engine ID:</span>
            <select 
              className="dropdown-selector" 
              style={{ width: '110px' }}
              value={datasetFilterUnit}
              onChange={(e) => {
                setDatasetFilterUnit(e.target.value);
                setDatasetPage(1); // reset to page 1
              }}
            >
              <option value="all">All Engines</option>
              {Array.from({ length: 100 }, (_, i) => i + 1).map(num => (
                <option key={num} value={num}>Engine #{num}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Paginated data table */}
        <div className="table-wrapper glass-panel">
          {datasetLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-muted)' }}>
              <Activity className="spinner" size={24} style={{ color: 'var(--color-indigo)' }} />
              <span>Loading telemetry rows...</span>
            </div>
          ) : (
            <>
              <table className="fleet-table dataset-table">
                <thead>
                  <tr>
                    <th>Unit ID</th>
                    <th>Cycle</th>
                    <th>Setting 1</th>
                    <th>Setting 2</th>
                    <th>T24 LPC Temp</th>
                    <th>T30 HPC Temp</th>
                    <th>T50 LPT Temp</th>
                    <th>P30 HPC Press</th>
                    <th>Nf Fan Speed</th>
                    <th>Ps30 Press</th>
                    <th>BPR Ratio</th>
                    <th>Bleed Enth.</th>
                  </tr>
                </thead>
                <tbody>
                  {rawDataset.map((row, idx) => (
                    <tr key={idx}>
                      <td className="font-mono">Engine #{row.unit_number}</td>
                      <td className="font-mono">{row.time_in_cycles}</td>
                      <td className="font-mono">{row.op_setting_1}</td>
                      <td className="font-mono">{row.op_setting_2}</td>
                      <td className="font-mono">{row.sensor_2}</td>
                      <td className="font-mono">{row.sensor_3}</td>
                      <td className="font-mono">{row.sensor_4}</td>
                      <td className="font-mono">{row.sensor_7}</td>
                      <td className="font-mono">{row.sensor_8}</td>
                      <td className="font-mono">{row.sensor_11}</td>
                      <td className="font-mono">{row.sensor_15}</td>
                      <td className="font-mono">{row.sensor_17}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Table pagination navigation */}
              <div className="pagination-bar">
                <button 
                  className="btn-secondary btn-sm" 
                  onClick={() => setDatasetPage(p => Math.max(1, p - 1))}
                  disabled={datasetPage === 1}
                >
                  Previous
                </button>
                <span className="font-mono" style={{ fontSize: '0.8rem' }}>Page {datasetPage} of {datasetTotalPages}</span>
                <button 
                  className="btn-secondary btn-sm" 
                  onClick={() => setDatasetPage(p => Math.min(datasetTotalPages, p + 1))}
                  disabled={datasetPage === datasetTotalPages}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="dashboard-container">
      {/* 1. TOP HEADER BANNER */}
      <header className="dashboard-header glass-panel">
        <div className="logo-section">
          <div className="logo-badge">AEROGUARD</div>
          <h1>FLEET MISSION CONTROL</h1>
        </div>
        <div className="sim-controls">
          <button className={`btn-primary ${simPlaying ? 'playing' : ''}`} onClick={() => setSimPlaying(!simPlaying)}>
            {simPlaying ? (
              <>
                <Pause size={16} />
                <span>Pause Telemetry</span>
              </>
            ) : (
              <>
                <Play size={16} fill="white" />
                <span>Stream Live Telemetry</span>
              </>
            )}
          </button>
          <button className="btn-secondary" onClick={resetSimulation}>
            <RefreshCw size={16} />
            <span>Reset Simulation</span>
          </button>
        </div>
      </header>

      {/* 2. BODY LAYOUT WITH LEFT NAV SIDEBAR */}
      <div className="main-content-area">
        {/* Left Nav Menu */}
        <nav className="sidebar-nav-panel glass-panel">
          <div className="nav-group">
            <span className="nav-group-label">FLEET COMMAND</span>
            <button 
              className={`nav-item ${activeTab === 'fleet' ? 'active' : ''}`}
              onClick={() => setActiveTab('fleet')}
            >
              <Cpu size={16} />
              <span>Fleet Queue</span>
            </button>
            <button 
              className={`nav-item ${activeTab === 'twin' ? 'active' : ''}`}
              onClick={() => setActiveTab('twin')}
            >
              <BarChart2 size={16} />
              <span>Digital Twin Analyst</span>
            </button>
          </div>

          <div className="nav-group">
            <span className="nav-group-label">SCENARIOS</span>
            <button 
              className={`nav-item ${activeTab === 'whatif' ? 'active' : ''}`}
              onClick={() => setActiveTab('whatif')}
            >
              <Wrench size={16} />
              <span>What-If Sandbox</span>
            </button>
          </div>

          <div className="nav-group">
            <span className="nav-group-label">COGNITIVE</span>
            <button 
              className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={16} />
              <span>AI Copilot Chat</span>
            </button>
            <button 
              className={`nav-item ${activeTab === 'dataset' ? 'active' : ''}`}
              onClick={() => setActiveTab('dataset')}
            >
              <Database size={16} />
              <span>Dataset Explorer</span>
            </button>
          </div>

          {/* Quick diagnostic highlight */}
          <div className="active-engine-badge font-mono">
            <div className="label">ACTIVE TARGET</div>
            <div className="val">Engine #{selectedEngineId}</div>
          </div>
        </nav>

        {/* Right Content Space */}
        <section className="content-view-viewport">
          {activeTab === 'fleet' && renderFleetOverview()}
          {activeTab === 'twin' && renderDigitalTwin()}
          {activeTab === 'whatif' && renderWhatIfSandbox()}
          {activeTab === 'chat' && renderAICopilot()}
          {activeTab === 'dataset' && renderDatasetExplorer()}
        </section>
      </div>
    </div>
  );
}
