// AeroGuard AI - SPA Frontend Logic

// Global API base mapping
const API_BASE = window.location.origin;

// State management
let currentActiveTab = 'landing';
let selectedSimEngineId = 1;
let simIntervalId = null;
let isSimStreaming = false;

// Pre-defined real NASA CMAPSS sample rows for quick demos
const SAMPLE_ENGINES = {
  healthy: {
    unit_number: 12,
    time_in_cycles: 10,
    sensor_2: 641.85,
    sensor_3: 1589.20,
    sensor_4: 1400.15,
    sensor_7: 554.10,
    sensor_8: 2388.02,
    sensor_11: 47.41,
    sensor_12: 521.62,
    sensor_13: 2388.01,
    sensor_14: 8138.20,
    sensor_15: 8.39,
    sensor_17: 392,
    sensor_20: 39.02,
    sensor_21: 23.41
  },
  warning: {
    unit_number: 45,
    time_in_cycles: 120,
    sensor_2: 642.50,
    sensor_3: 1591.45,
    sensor_4: 1406.80,
    sensor_7: 553.15,
    sensor_8: 2388.11,
    sensor_11: 47.88,
    sensor_12: 520.45,
    sensor_13: 2388.10,
    sensor_14: 8142.50,
    sensor_15: 8.46,
    sensor_17: 393,
    sensor_20: 38.65,
    sensor_21: 23.22
  },
  critical: {
    unit_number: 27,
    time_in_cycles: 195,
    sensor_2: 643.82,
    sensor_3: 1598.60,
    sensor_4: 1422.40,
    sensor_7: 551.40,
    sensor_8: 2388.24,
    sensor_11: 48.28,
    sensor_12: 518.15,
    sensor_13: 2388.22,
    sensor_14: 8150.30,
    sensor_15: 8.59,
    sensor_17: 396,
    sensor_20: 38.25,
    sensor_21: 22.92
  }
};

// Initial setup
document.addEventListener("DOMContentLoaded", () => {
  // Navigation Router Setup
  const navItems = document.querySelectorAll("[data-target]");
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const target = item.getAttribute("data-target");
      switchTab(target);
    });
  });

  // Load sample data trigger
  document.getElementById("btn-load-healthy")?.addEventListener("click", () => populateSensorForm('healthy'));
  document.getElementById("btn-load-warning")?.addEventListener("click", () => populateSensorForm('warning'));
  document.getElementById("btn-load-critical")?.addEventListener("click", () => populateSensorForm('critical'));

  // Form submission
  document.getElementById("sensor-prediction-form")?.addEventListener("submit", handlePredictionSubmit);

  // CSV upload handler
  document.getElementById("csv-file-input")?.addEventListener("change", handleCSVUpload);

  // Simulation controls
  document.getElementById("btn-stream-sim")?.addEventListener("click", toggleSimulationStream);
  document.getElementById("btn-reset-sim")?.addEventListener("click", resetSimulation);
  document.getElementById("sim-engine-selector")?.addEventListener("change", (e) => {
    selectedSimEngineId = parseInt(e.target.value);
    loadSimEngineDetails();
  });

  // Sim Maintenance triggers
  document.getElementById("btn-wash-compressor")?.addEventListener("click", () => triggerWhatIfMaintenance("compressor_wash"));
  document.getElementById("btn-replace-bearings")?.addEventListener("click", () => triggerWhatIfMaintenance("bearing_replace"));
  document.getElementById("btn-overhaul-core")?.addEventListener("click", () => triggerWhatIfMaintenance("core_overhaul"));

  // Chat copilot actions
  document.getElementById("btn-chat-send")?.addEventListener("click", sendCopilotChat);
  document.getElementById("chat-input-text")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendCopilotChat();
  });

  // Chips click templates
  document.querySelectorAll(".chat-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const text = chip.getAttribute("data-query");
      document.getElementById("chat-input-text").value = text;
      sendCopilotChat();
    });
  });

  // System logs polling scheduler (every 2.5 seconds)
  loadSystemLogs();
  setInterval(loadSystemLogs, 2500);

  // Default start tab
  switchTab('landing');

  // Pre-load dashboard statistics and selector state to initialize the header active asset focus badge
  loadDashboardStats();
  loadAnalyticsCharts();

  // Pre-populate prediction form silently with critical template to show non-zero business savings on load
  populateSensorForm('critical', false);
  runDefaultPrediction('critical');
});

// SPA Tab Switcher
function switchTab(tabId) {
  currentActiveTab = tabId;

  // Show/Hide page views
  document.querySelectorAll(".app-view").forEach(view => {
    view.classList.remove("active");
  });
  const activeView = document.getElementById(`view-${tabId}`);
  if (activeView) activeView.classList.add("active");

  // Show/Hide sidebar depending on Landing page tab
  const sidebar = document.getElementById("app-sidebar");
  if (sidebar) {
    if (tabId === 'landing') {
      sidebar.classList.add("hidden");
    } else {
      sidebar.classList.remove("hidden");
    }
  }

  // Highlight navbar active markers
  document.querySelectorAll("[data-target]").forEach(nav => {
    if (nav.getAttribute("data-target") === tabId) {
      nav.classList.add("active-nav");
    } else {
      nav.classList.remove("active-nav");
    }
  });

  // Stop ticker if navigating away from Dashboard
  if (tabId !== 'dashboard' && isSimStreaming) {
    toggleSimulationStream();
  }

  // Load contextual page data
  if (tabId === 'dashboard') {
    switchDashboardSubTab('overview');
    loadDashboardStats();
    loadAnalyticsCharts();
  } else if (tabId === 'fleet') {
    loadFleetMonitor();
  } else if (tabId === 'explain') {
    loadModelInfo();
    renderExplainShapChart();
  }
}

// Run a default prediction on startup to populate placeholders
async function runDefaultPrediction(type = 'critical') {
  const data = SAMPLE_ENGINES[type];
  if (!data) return;
  
  const payload = {
    unit_number: data.unit_number,
    time_in_cycles: data.time_in_cycles,
  };
  Object.keys(data).forEach(key => {
    if (key !== 'unit_number' && key !== 'time_in_cycles') {
      payload[key] = data[key];
    }
  });

  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const result = await res.json();
      renderPredictionResults(result);
      // Pre-set active copilot context
      window.lastPredictionContext = {
        unit_number: payload.unit_number,
        cycle: payload.time_in_cycles,
        predicted_rul: result.predicted_rul,
        health_score: result.health_score,
        risk_level: result.risk_level,
        priority: result.maintenance_priority,
        anomalies: result.anomalies,
        explainability: result.explainability
      };
      if (!window.activeCopilotContext) {
        window.activeCopilotContext = window.lastPredictionContext;
      }
    }
  } catch (err) {
    console.error("Default prediction failed:", err);
  }
}

// Populate prediction form with sample NASA data
function populateSensorForm(type, showToastNotification = true) {
  const data = SAMPLE_ENGINES[type];
  if (!data) return;

  document.getElementById("input-unit-number").value = data.unit_number;
  document.getElementById("input-cycles").value = data.time_in_cycles;

  Object.keys(data).forEach(key => {
    const input = document.getElementById(`input-${key.replace('_', '-')}`);
    if (input) input.value = data[key];
  });

  if (showToastNotification) {
    showToast(`Loaded CMAPSS ${type.toUpperCase()} engine template (Unit #${data.unit_number})`);
  }
}

// Submit manual sensor entries for prediction
async function handlePredictionSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);
  
  const payload = {
    unit_number: parseInt(formData.get("unit_number")),
    time_in_cycles: parseInt(formData.get("time_in_cycles")),
  };

  // Extract sensors
  Object.keys(SAMPLE_ENGINES.healthy).forEach(key => {
    if (key !== 'unit_number' && key !== 'time_in_cycles') {
      payload[key] = parseFloat(formData.get(key));
    }
  });

  // Show loader on predict button
  const btn = document.getElementById("btn-submit-predict");
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<i class="fa-solid fa-gear fa-spin mr-2"></i> Calculating...`;
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (!res.ok) throw new Error("Prediction API failed");
    const result = await res.json();
    
    renderPredictionResults(result);
    showToast("Remaining Useful Life prediction complete!");
    loadSystemLogs();
    
    // Auto scroll to results panel
    document.getElementById("prediction-results-panel")?.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    console.error(err);
    showToast("Error making RUL prediction. Verify backend values.", "error");
  } finally {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
  }
}

// Render prediction output onto the UI results panels
function renderPredictionResults(res) {
  // Populate metrics
  document.getElementById("res-rul").innerText = `${res.predicted_rul} cycles`;
  document.getElementById("res-health").innerText = `${res.health_score}%`;
  document.getElementById("res-risk").innerText = res.risk_level;
  document.getElementById("res-priority").innerText = `Priority ${res.maintenance_priority}`;
  document.getElementById("res-confidence").innerText = `${res.confidence_score}%`;
  document.getElementById("res-failure-window").innerText = res.recommendation_details[0] || "";
  document.getElementById("res-recommendation").innerText = res.recommendation;

  // Set colors dynamically
  const riskBadge = document.getElementById("res-risk");
  riskBadge.className = "text-2xl font-bold font-mono uppercase";
  if (res.risk_level === 'Critical') riskBadge.classList.add("text-red-500", "text-glow-red");
  else if (res.risk_level === 'High Risk') riskBadge.classList.add("text-orange-500");
  else if (res.risk_level === 'Medium Risk') riskBadge.classList.add("text-yellow-500");
  else riskBadge.classList.add("text-green-500", "text-glow-green");

  // Populate Business Impact cards
  const bus = res.business_impact;
  const inrSavings = Math.round(bus.total_financial_savings * 83.5);
  document.getElementById("res-savings").innerText = `₹${inrSavings.toLocaleString('en-IN')}`;
  document.getElementById("res-downtime-saved").innerText = `${bus.downtime_prevented_hours} hrs`;
  document.getElementById("res-safety-index").innerText = `${bus.safety_index_pct}%`;
  document.getElementById("res-fleet-avail").innerText = `${bus.fleet_availability_contribution_pct}%`;

  // Populate Explainability Details
  const explain = res.explainability;
  document.getElementById("res-explain-method").innerText = `Model: XGBoost • Attribution Method: ${explain.method}`;
  document.getElementById("res-explain-natural").innerText = explain.natural_language;

  // Render SHAP waterfall/bar chart
  const sensors = explain.sensor_impacts;
  const trace = {
    x: sensors.map(s => s.impact),
    y: sensors.map(s => s.label),
    type: 'bar',
    orientation: 'h',
    marker: {
      color: sensors.map(s => s.impact < 0 ? '#ef4444' : '#10b981'),
      width: 0.6
    }
  };

  const layout = {
    title: { text: 'Telemetry Feature Attributions (SHAP)', font: { color: '#c084fc', size: 14 } },
    plot_bgcolor: 'rgba(0,0,0,0)',
    paper_bgcolor: 'rgba(0,0,0,0)',
    xaxis: { gridcolor: 'rgba(168, 85, 247, 0.05)', tickfont: { color: '#c084fc' }, title: 'RUL Impact (Cycles)' },
    yaxis: { tickfont: { color: '#c084fc' }, automargin: true },
    margin: { l: 150, r: 20, t: 40, b: 40 }
  };

  Plotly.newPlot('shap-bar-chart', [trace], layout, { responsive: true, displayModeBar: false });

  // Store variables in prompt history for Copilot Focus
  window.lastPredictionContext = {
    unit_number: parseInt(document.getElementById("input-unit-number").value),
    cycle: parseInt(document.getElementById("input-cycles").value),
    predicted_rul: res.predicted_rul,
    health_score: res.health_score,
    risk_level: res.risk_level,
    priority: res.maintenance_priority,
    anomalies: res.anomalies,
    explainability: res.explainability
  };

  // Set the globally active chatbot/XAI context
  window.activeCopilotContext = window.lastPredictionContext;
  
  // Update copilot focus badge
  const focusText = `Engine #${window.lastPredictionContext.unit_number} (Active)`;
  const badge = document.getElementById("copilot-focus-badge");
  const badgeHeader = document.getElementById("copilot-focus-badge-header");
  if (badge) badge.innerText = focusText;
  if (badgeHeader) badgeHeader.innerText = focusText;

  // Render to explain page if it exists
  renderExplainShapChart();
}

// Handle CSV File upload and summary
async function handleCSVUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const container = document.getElementById("csv-results-summary");
  container.innerHTML = `<div class="flex items-center text-secondary gap-3 p-4"><i class="fa-solid fa-compact-disc fa-spin"></i> Parsing logs, training matrices...</div>`;
  container.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) throw new Error("CSV Upload response error");
    const data = await res.json();

    let rowsHtml = '';
    data.predictions.forEach(p => {
      rowsHtml += `
        <tr class="border-b border-white/5 hover:bg-white/5 font-mono">
          <td class="p-3 text-cyan">Engine #${p.unit_number}</td>
          <td class="p-3 text-secondary">${p.cycle}</td>
          <td class="p-3">${p.predicted_rul} cycles</td>
          <td class="p-3">${p.health_score}%</td>
          <td class="p-3"><span class="text-${p.risk_color}-500 font-bold">${p.risk_level}</span></td>
          <td class="p-3"><span class="badge-priority ${p.priority.toLowerCase()}">${p.priority}</span></td>
          <td class="p-3 text-green-500 font-bold">₹${Math.round(p.savings * 83.5).toLocaleString('en-IN')}</td>
        </tr>
      `;
    });

    container.innerHTML = `
      <div class="border-b border-indigo-500/20 p-4 bg-indigo-500/5 rounded-t-xl">
        <div class="flex justify-between items-center flex-wrap gap-4">
          <div class="flex items-center gap-2 text-glow-green text-green-400 font-bold">
            <i class="fa-solid fa-circle-check"></i>
            <span>Log Evaluation Successful</span>
          </div>
          <div class="text-sm font-mono text-secondary">
            Analyzed: <strong class="text-white">${data.engines_analyzed_count}</strong> | 
            Critical Assets: <strong class="text-red-400">${data.critical_assets_found}</strong>
          </div>
        </div>
      </div>
      <div class="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="p-3 border border-white/5 rounded-lg bg-black/20">
          <div class="text-xs text-secondary">PROJECTED DOWNTIME PREVENTED</div>
          <div class="text-2xl font-bold font-mono text-cyan">${data.engines_analyzed_count * 20} Hours</div>
        </div>
        <div class="p-3 border border-white/5 rounded-lg bg-black/20">
          <div class="text-xs text-secondary">ESTIMATED MAINTENANCE COST SAVINGS</div>
          <div class="text-2xl font-bold font-mono text-green-400">₹${Math.round(data.projected_cost_savings * 83.5).toLocaleString('en-IN')}</div>
        </div>
      </div>
      <div class="overflow-x-auto max-h-72 overflow-y-auto px-4 pb-4">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="border-b border-white/10 text-secondary font-bold">
              <th class="p-3">Engine ID</th>
              <th class="p-3">Cycle</th>
              <th class="p-3">Predicted RUL</th>
              <th class="p-3">Health Score</th>
              <th class="p-3">Risk Level</th>
              <th class="p-3">Priority</th>
              <th class="p-3">Part Savings</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;

    showToast(`CSV Parsed. Evaluated RUL for ${data.predictions.length} turbines!`);
    loadSystemLogs();
  } catch (err) {
    console.error(err);
    container.innerHTML = `<div class="text-red-500 p-4 font-mono text-xs"><i class="fa-solid fa-triangle-exclamation mr-2"></i> CSV validation error: columns must include unit_number, time_in_cycles, and active sensors.</div>`;
  }
}

// Fetch Global operations stats
async function loadDashboardStats() {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard`);
    const data = await res.json();

    document.getElementById("stat-fleet-health").innerText = `${data.fleet_health_score}%`;
    document.getElementById("stat-avg-rul").innerText = `${data.average_rul} cycles`;
    document.getElementById("stat-critical-engines").innerText = data.critical_engines;
    document.getElementById("stat-maint-due").innerText = data.maintenance_due;
    document.getElementById("stat-accuracy").innerText = `${data.prediction_accuracy_pct}%`;
    
    // Active simulation selectors
    const selector = document.getElementById("sim-engine-selector");
    if (selector && selector.children.length === 0) {
      for (let i = 1; i <= data.total_active_assets; i++) {
        const opt = document.createElement("option");
        opt.value = i;
        opt.innerText = `Engine Unit #${i}`;
        selector.appendChild(opt);
      }
      loadSimEngineDetails();
    }
  } catch (err) {
    console.error("Dashboard stats failed:", err);
  }
}

// Render dynamic dashboard analytics charts (Plotly)
async function loadAnalyticsCharts() {
  try {
    const res = await fetch(`${API_BASE}/api/analytics`);
    const data = await res.json();

    // Chart 1: Risk Distribution (Pie chart) - Filter out 0-value categories to prevent label overlapping
    const rawKeys = Object.keys(data.risk_distribution);
    const rawVals = Object.values(data.risk_distribution);
    const filteredRiskKeys = [];
    const filteredRiskValues = [];
    const colorMap = {
      'Low Risk': '#10b981',
      'Medium Risk': '#f59e0b',
      'High Risk': '#f97316',
      'Critical': '#ef4444'
    };
    const filteredColors = [];

    rawKeys.forEach((key, idx) => {
      const val = rawVals[idx];
      if (val > 0) {
        filteredRiskKeys.push(key);
        filteredRiskValues.push(val);
        filteredColors.push(colorMap[key] || '#a855f7');
      }
    });

    const riskData = [
      {
        values: filteredRiskValues,
        labels: filteredRiskKeys,
        type: 'pie',
        hole: 0.5,
        marker: {
          colors: filteredColors
        },
        textinfo: 'percent',
        textposition: 'inside'
      }
    ];

    const riskLayout = {
      title: { text: 'Risk Distribution Profile', font: { color: '#c084fc', size: 14 } },
      plot_bgcolor: 'rgba(0,0,0,0)',
      paper_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#c084fc' },
      margin: { l: 10, r: 10, t: 40, b: 10 },
      showlegend: true,
      legend: {
        font: { color: '#c084fc', size: 9 },
        orientation: 'h',
        x: 0,
        y: -0.15
      },
      height: 220
    };

    Plotly.newPlot('chart-risk-dist', riskData, riskLayout, { responsive: true, displayModeBar: false });

    // Chart 2: RUL Histogram
    const rulTrace = {
      x: data.rul_values,
      type: 'histogram',
      xbins: { size: 15 },
      marker: { color: '#a855f7' }
    };

    const rulLayout = {
      title: { text: 'Remaining Useful Life Histogram', font: { color: '#c084fc', size: 14 } },
      plot_bgcolor: 'rgba(0,0,0,0)',
      paper_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#c084fc' },
      xaxis: { title: 'Predicted Cycles', gridcolor: 'rgba(168, 85, 247, 0.05)' },
      yaxis: { title: 'Engine Count', gridcolor: 'rgba(168, 85, 247, 0.05)' },
      margin: { l: 40, r: 20, t: 40, b: 40 },
      height: 220
    };

    Plotly.newPlot('chart-rul-hist', [rulTrace], rulLayout, { responsive: true, displayModeBar: false });

    // Chart 3: Prediction Timeline curve
    const timelineTrace = {
      x: data.timeline.map(t => t.unit),
      y: data.timeline.map(t => t.rul),
      mode: 'lines+markers',
      type: 'scatter',
      name: 'RUL Prediction',
      line: { color: '#a855f7' },
      marker: {
        size: 8,
        color: data.timeline.map(t => {
          if (t.risk === 'Critical') return '#ef4444';
          if (t.risk === 'High Risk') return '#f97316';
          if (t.risk === 'Medium Risk') return '#f59e0b';
          return '#10b981';
        })
      }
    };

    const timelineLayout = {
      title: { text: 'Fleet-wide Timeline Prediction Index', font: { color: '#c084fc', size: 14 } },
      plot_bgcolor: 'rgba(0,0,0,0)',
      paper_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#c084fc' },
      xaxis: { title: 'Engine Unit ID', gridcolor: 'rgba(168, 85, 247, 0.05)' },
      yaxis: { title: 'Remaining Useful Life (Cycles)', gridcolor: 'rgba(168, 85, 247, 0.05)' },
      margin: { l: 50, r: 20, t: 40, b: 40 },
      height: 220
    };

    Plotly.newPlot('chart-timeline', [timelineTrace], timelineLayout, { responsive: true, displayModeBar: false });

  } catch (err) {
    console.error("Charts loading failed:", err);
  }
}

// Load and populate the Fleet table Monitor
let lastFleetData = [];
async function loadFleetMonitor() {
  try {
    const res = await fetch(`${API_BASE}/api/fleet`);
    const data = await res.json();
    lastFleetData = data.engines;

    renderFleetTable(lastFleetData);

  } catch (err) {
    console.error("Fleet loading error:", err);
  }
}

function renderFleetTable(engines) {
  const tbody = document.getElementById("fleet-table-body");
  if (!tbody) return;

  let rows = '';
  engines.forEach(e => {
    rows += `
      <tr class="border-b border-white/5 hover:bg-white/5 cursor-pointer font-mono" onclick="setSimEngineFocus(${e.unit_number})">
        <td class="p-4 text-cyan font-bold">Engine #${e.unit_number}</td>
        <td class="p-4 text-secondary">${e.current_cycle}</td>
        <td class="p-4">${e.predicted_rul} cycles</td>
        <td class="p-4">
          <div class="flex items-center gap-2">
            <div class="w-16 bg-white/10 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-${e.risk_color}-500" style="width: ${e.health_score}%"></div>
            </div>
            <span>${e.health_score}%</span>
          </div>
        </td>
        <td class="p-4">
          <span class="text-${e.risk_color}-500 font-bold uppercase text-xs">${e.risk_level}</span>
        </td>
        <td class="p-4">
          <span class="badge-priority ${e.maintenance_priority.toLowerCase()}">${e.maintenance_priority}</span>
        </td>
        <td class="p-4 text-xs font-sans text-secondary truncate max-w-xs" title="${e.recommendation}">
          ${e.recommendation}
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = rows;
}

// Enable filtering / sorting on the fleet monitor
function filterFleetTable() {
  const query = document.getElementById("fleet-search-input").value.toLowerCase();
  const riskFilter = document.getElementById("fleet-risk-filter").value;

  const filtered = lastFleetData.filter(e => {
    const matchesSearch = e.unit_number.toString().includes(query) || e.recommendation.toLowerCase().includes(query);
    const matchesRisk = riskFilter === 'all' || e.risk_level === riskFilter;
    return matchesSearch && matchesRisk;
  });

  renderFleetTable(filtered);
}

// Focus selector bridge
function setSimEngineFocus(id) {
  selectedSimEngineId = id;
  const selector = document.getElementById("sim-engine-selector");
  if (selector) selector.value = id;
  
  switchTab('dashboard');
  switchDashboardSubTab('twin');
  loadSimEngineDetails();
  
  showToast(`Focused diagnostics console on Engine #${id}`);
}

// Load Model validation info for Explain AI page
async function loadModelInfo() {
  try {
    const res = await fetch(`${API_BASE}/api/model-info`);
    const data = await res.json();

    document.getElementById("info-rmse").innerText = `${data.rmse} cycles`;
    document.getElementById("info-features-count").innerText = `${data.feature_count} features`;

    // Render global feature importances bar chart
    const importances = data.feature_importances;
    const trace = {
      x: importances.map(i => i[1]).reverse(),
      y: importances.map(i => {
        // Humanize labels
        const label = i[0];
        if (label.endsWith("_roll_mean")) return label.replace("_roll_mean", " Roll Mean");
        if (label.endsWith("_roll_std")) return label.replace("_roll_std", " Roll Std");
        if (label.endsWith("_drift")) return label.replace("_drift", " Drift");
        return label;
      }).reverse(),
      type: 'bar',
      orientation: 'h',
      marker: { color: '#a855f7' }
    };

    const layout = {
      title: { text: 'Global Feature Importances (XGBoost)', font: { color: '#c084fc', size: 14 } },
      plot_bgcolor: 'rgba(0,0,0,0)',
      paper_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#c084fc' },
      xaxis: { gridcolor: 'rgba(168, 85, 247, 0.05)', title: 'Gain Contribution Ratio' },
      yaxis: { automargin: true },
      margin: { l: 150, r: 20, t: 40, b: 40 },
      height: 380
    };

    Plotly.newPlot('global-importance-chart', [trace], layout, { responsive: true, displayModeBar: false });

  } catch (err) {
    console.error(err);
  }
}

// Render local SHAP bar chart inside the Explainable AI Copilot view
function renderExplainShapChart() {
  const context = window.lastPredictionContext || window.lastSimContext;
  const explainShapContainer = document.getElementById('explain-shap-bar-chart');
  if (!explainShapContainer) return;

  if (!context || !context.explainability) {
    explainShapContainer.innerHTML = '';
    const explainDesc = document.getElementById('explain-shap-desc');
    if (explainDesc) {
      explainDesc.innerText = "Please run a prediction in the Prediction Center to view local SHAP attributions.";
    }
    return;
  }

  const explain = context.explainability;
  const sensors = explain.sensor_impacts;
  
  // Calculate sum of absolute impacts to check if all features are at baseline
  const totalImpact = sensors.reduce((sum, s) => sum + Math.abs(s.impact), 0);
  if (totalImpact < 0.05) {
    explainShapContainer.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 36px 20px; text-align: center; background: rgba(16, 185, 129, 0.03); border: 1px dashed rgba(16, 185, 129, 0.15); border-radius: 12px; margin-top: 12px;">
        <i class="fa-solid fa-circle-check" style="color: var(--color-green); font-size: 2rem; margin-bottom: 10px; filter: drop-shadow(0 0 10px rgba(16,185,129,0.35));"></i>
        <strong style="color: white; font-size: 0.8rem; display: block; margin-bottom: 4px;">100% Nominal Baseline Performance</strong>
        <span style="color: var(--text-dim); font-size: 0.68rem; max-width: 320px; line-height: 1.45;">
          All physical telemetry channels are operating at default factory baselines. No wear anomalies or sensor deviations detected.
        </span>
      </div>
    `;
    return;
  }

  const trace = {
    x: sensors.map(s => s.impact),
    y: sensors.map(s => s.label),
    type: 'bar',
    orientation: 'h',
    marker: {
      color: sensors.map(s => s.impact < 0 ? '#ef4444' : '#10b981'),
      width: 0.6
    }
  };

  const layout = {
    title: { text: `SHAP Attributions (Engine #${context.unit_number})`, font: { color: '#c084fc', size: 13 } },
    plot_bgcolor: 'rgba(0,0,0,0)',
    paper_bgcolor: 'rgba(0,0,0,0)',
    xaxis: { gridcolor: 'rgba(168, 85, 247, 0.05)', tickfont: { color: '#c084fc' }, title: 'RUL Impact (Cycles)' },
    yaxis: { tickfont: { color: '#c084fc' }, automargin: true },
    margin: { l: 150, r: 20, t: 40, b: 40 },
    height: 300
  };

  Plotly.newPlot('explain-shap-bar-chart', [trace], layout, { responsive: true, displayModeBar: false });
  const explainDesc = document.getElementById('explain-shap-desc');
  if (explainDesc) {
    explainDesc.innerText = `Showing local telemetry SHAP attributions for Engine #${context.unit_number} (Active Focus).`;
  }
}

// Simulation Streaming time controller
function toggleSimulationStream() {
  const btn = document.getElementById("btn-stream-sim");
  
  if (isSimStreaming) {
    clearInterval(simIntervalId);
    isSimStreaming = false;
    btn.innerHTML = `<i class="fa-solid fa-play"></i> Stream Live Telemetry`;
    btn.className = "btn-secondary paused";
    showToast("Live telemetry stream paused.");
  } else {
    isSimStreaming = true;
    btn.innerHTML = `<i class="fa-solid fa-pause spinner"></i> Pause Stream`;
    btn.className = "btn-secondary streaming";
    showToast("Streaming live aircraft telemetry feeds...");

    // Tick simulation every 4 seconds
    simIntervalId = setInterval(async () => {
      try {
        await fetch(`${API_BASE}/api/tick`, { method: 'POST' });
        loadDashboardStats();
        loadAnalyticsCharts();
        loadSimEngineDetails();
        loadFleetMonitor();
        loadSystemLogs();
      } catch (err) {
        console.error("Simulation tick failed:", err);
      }
    }, 4000);
  }
}

async function resetSimulation() {
  try {
    // Stop the running stream first so it doesn't immediately advance cycles
    if (isSimStreaming) {
      toggleSimulationStream();
    }

    const res = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
    const data = await res.json();
    
    showToast("Asset simulator states reset to baseline cycles.");
    loadDashboardStats();
    loadAnalyticsCharts();
    loadSimEngineDetails();
    loadFleetMonitor();
    loadSystemLogs();

  } catch (err) {
    console.error(err);
  }
}

// Load focused simulated engine detailed schematic & history
async function loadSimEngineDetails() {
  try {
    const res = await fetch(`${API_BASE}/api/fleet/${selectedSimEngineId}`);
    if (!res.ok) throw new Error("Focused engine metrics loading failed.");
    const engine = await res.json();

    // Update schematic indicators
    document.getElementById("sim-engine-id-badge").innerText = `ENGINE UNIT #${engine.unit_number}`;
    document.getElementById("sim-engine-cycles").innerText = `CYCLE ${engine.current_cycle}`;
    document.getElementById("sim-engine-rul").innerText = `${engine.predicted_rul} cycles`;
    document.getElementById("sim-engine-health").innerText = `${engine.health_score}%`;
    document.getElementById("sim-engine-priority").innerText = `Priority ${engine.maintenance_priority}`;

    const priorityBadge = document.getElementById("sim-engine-priority");
    priorityBadge.className = "badge-priority p4 text-xs mt-1";
    if (engine.maintenance_priority === 'P1') priorityBadge.className = "badge-priority p1 text-xs mt-1";
    else if (engine.maintenance_priority === 'P2') priorityBadge.className = "badge-priority p2 text-xs mt-1";
    else if (engine.maintenance_priority === 'P3') priorityBadge.className = "badge-priority p3 text-xs mt-1";

    // Rotate rotor animation speed
    const rotor = document.getElementById("turbine-schematic-rotor");
    if (rotor) {
      rotor.className = "turbine-rotor";
      if (engine.risk_level === 'Critical') rotor.classList.add("critical");
      else if (engine.risk_level === 'High Risk') rotor.classList.add("warning");
    }

    // Set risk overlays colors
    const lpcRing = document.getElementById("lpc-ring");
    const hpcRing = document.getElementById("hpc-ring");
    const lptRing = document.getElementById("lpt-ring");
    
    // Clear colors
    lpcRing.className = "ring-overlay green w-16 h-16 left-12 top-10";
    hpcRing.className = "ring-overlay green w-14 h-14 left-44 top-12";
    lptRing.className = "ring-overlay green w-16 h-16 right-12 top-10";

    const color = engine.risk_color; // green, yellow, orange, red
    if (color !== 'green') {
      lpcRing.className = `ring-overlay ${color} w-16 h-16 left-12 top-10`;
      hpcRing.className = `ring-overlay ${color} w-14 h-14 left-44 top-12`;
      lptRing.className = `ring-overlay ${color} w-16 h-16 right-12 top-10`;
    }

    // Populate maintenance history list
    const historyList = document.getElementById("sim-maint-history");
    if (historyList) {
      let items = '';
      
      // If the engine has abnormal wear risk, prepend a highly visible active alert card!
      if (engine.risk_level !== "Low Risk") {
        items += `
          <div class="p-3 border border-red-500/20 bg-red-500/10 rounded-lg flex flex-col gap-1 text-xs">
            <div class="flex justify-between font-mono text-red-500 font-bold">
              <span><i class="fa-solid fa-triangle-exclamation"></i> ACTIVE TELEMETRY WARNING</span>
              <span style="text-shadow: 0 0 8px rgba(239,68,68,0.5);">${engine.risk_level.toUpperCase()}</span>
            </div>
            <div class="text-primary font-semibold">Priority ${engine.maintenance_priority}: Health index dropped to ${engine.health_score}%!</div>
            <div class="text-[10px] text-muted font-mono">${engine.recommendation}</div>
          </div>
        `;
      }
      
      if (engine.maintenance_history.length === 0) {
        if (items === '') {
          historyList.innerHTML = `<div class="text-xs text-muted italic p-3 text-center">No maintenance logs registered in current cycle sequence.</div>`;
        } else {
          historyList.innerHTML = `<div class="flex flex-col gap-2">${items}</div>`;
        }
      } else {
        engine.maintenance_history.forEach(log => {
          items += `
            <div class="p-3 border border-white/5 bg-black/20 rounded-lg flex flex-col gap-1 text-xs">
              <div class="flex justify-between font-mono">
                <span class="text-cyan font-bold">${log.type.replace('_', ' ').toUpperCase()}</span>
                <span class="text-secondary">${log.timestamp}</span>
              </div>
              <div class="text-secondary">${log.description}</div>
              <div class="text-[10px] text-muted font-mono">Triggered at Cycle ${log.cycle}</div>
            </div>
          `;
        });
        historyList.innerHTML = `<div class="flex flex-col gap-2">${items}</div>`;
      }
    }

    // Contextualize AI Maintenance Copilot Focus
    window.lastSimContext = {
      unit_number: engine.unit_number,
      cycle: engine.current_cycle,
      predicted_rul: engine.predicted_rul,
      health_score: engine.health_score,
      risk_level: engine.risk_level,
      priority: engine.maintenance_priority,
      anomalies: engine.anomalies,
      explainability: engine.explainability
    };

    // Set the globally active chatbot/XAI context
    window.activeCopilotContext = window.lastSimContext;

    // Render explain SHAP chart if focused
    renderExplainShapChart();

    // Update copilot focus badge
    const focusText = `Engine #${engine.unit_number} (Active)`;
    const badge = document.getElementById("copilot-focus-badge");
    const badgeHeader = document.getElementById("copilot-focus-badge-header");
    if (badge) badge.innerText = focusText;
    if (badgeHeader) badgeHeader.innerText = focusText;

  } catch (err) {
    console.error(err);
  }
}

// Trigger What-If repairs
async function triggerWhatIfMaintenance(type) {
  const container = document.getElementById("whatif-results-box");
  container.innerHTML = `<div class="flex items-center justify-center p-8 text-secondary"><i class="lucide-activity spinner mr-2"></i> Computing thermodynamic lifetime shifts...</div>`;
  container.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_number: selectedSimEngineId, type: type })
    });

    if (!res.ok) throw new Error("Simulation failure");
    const data = await res.json();

    container.innerHTML = `
      <div class="flex items-center gap-2 text-green-400 font-bold mb-3">
        <i class="fa-solid fa-circle-check"></i>
        <span>THERMODYNAMIC SIMULATION COMPLETED</span>
      </div>
      <p class="text-sm text-secondary mb-4">${data.description}</p>
      <div class="grid grid-cols-2 gap-4">
        <div class="p-3 border border-white/5 bg-red-500/5 rounded-lg text-center">
          <span class="text-[10px] text-secondary font-mono block">PRE-SERVICE RUL</span>
          <span class="text-2xl font-bold font-mono text-red-400">${data.before.predicted_rul}c</span>
          <span class="text-[10px] text-muted block mt-1">Health: ${data.before.health_score}%</span>
        </div>
        <div class="p-3 border border-green-500/20 bg-green-500/5 rounded-lg text-center">
          <span class="text-[10px] text-secondary font-mono block">POST-SERVICE RUL</span>
          <span class="text-2xl font-bold font-mono text-green-400">${data.after.predicted_rul}c</span>
          <span class="text-[10px] text-green-400 block mt-1">Health: ${data.after.health_score}%</span>
        </div>
      </div>
      <div class="mt-4 p-3 bg-green-500/10 border border-green-500/20 text-center rounded-lg text-green-400 text-sm font-bold">
        Lifespan Extended by +${data.extended_cycles} Cycles!
      </div>
    `;

    showToast(`Simulation Applied! Engine #${selectedSimEngineId} lifespan extended.`);
    loadDashboardStats();
    loadAnalyticsCharts();
    loadSimEngineDetails();
    loadFleetMonitor();
    loadSystemLogs();

  } catch (err) {
    console.error(err);
    container.innerHTML = `<div class="text-red-400 p-4 font-mono text-xs"><i class="fa-solid fa-triangle-exclamation mr-2"></i> Simulation failed. Ensure backend server is reachable.</div>`;
  }
}

// AI Maintenance Copilot conversational interface
async function sendCopilotChat() {
  const input = document.getElementById("chat-input-text");
  const query = input.value.trim();
  if (!query) return;

  // Clear input
  input.value = "";

  // Append user bubble
  appendChatBubble('user', query);

  // Load context from globally active focus or fallback
  const context = window.activeCopilotContext || window.lastPredictionContext || window.lastSimContext;
  if (!context) {
    appendChatBubble('assistant', "Please run a prediction in the Prediction Center or select an engine on the Dashboard so I have active telemetry context to analyze.");
    return;
  }

  // Show typing loader
  const chatLog = document.getElementById("chat-log-container");
  const loader = document.createElement("div");
  loader.id = "chat-typing-loader";
  loader.className = "flex items-center text-xs text-secondary gap-2 p-3 font-mono";
  loader.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-cyan-400"></i> AeroGuard Copilot reasoning...`;
  chatLog.appendChild(loader);
  chatLog.scrollTop = chatLog.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/api/copilot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        unit_number: context.unit_number,
        cycle: context.cycle,
        predicted_rul: context.predicted_rul,
        health_score: context.health_score,
        risk_level: context.risk_level,
        priority: context.priority,
        anomalies: context.anomalies,
        question: query
      })
    });

    if (!res.ok) throw new Error("Copilot response issue");
    const data = await res.json();

    // Remove loader
    loader.remove();

    // Append assistant bubble
    appendChatBubble('assistant', data.reply);
    
    // Dynamically pivot visualization and sandbox context if chatbot redirected focus
    if (data.context_shift) {
      const shift = data.context_shift;
      window.lastSimContext = shift;
      window.activeCopilotContext = shift;
      selectedSimEngineId = shift.unit_number;
      
      const selector = document.getElementById("sim-engine-selector");
      if (selector) selector.value = shift.unit_number;
      
      loadSimEngineDetails();
      renderExplainShapChart();
      
      const focusText = `Engine #${shift.unit_number} (Active)`;
      const badge = document.getElementById("copilot-focus-badge");
      const badgeHeader = document.getElementById("copilot-focus-badge-header");
      if (badge) badge.innerText = focusText;
      if (badgeHeader) badgeHeader.innerText = focusText;
      
      showToast(`Pivoted active diagnostic focus to Engine #${shift.unit_number}`);
    }
    
    loadSystemLogs();

  } catch (err) {
    console.error(err);
    loader.remove();
    appendChatBubble('assistant', "Diagnostic communication loss. Verify your Google Gemini API key or network status. (Offline fallback failed to return reply)");
  }
}

function appendChatBubble(sender, text) {
  const chatLog = document.getElementById("chat-log-container");
  if (!chatLog) return;

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${sender}`;

  // Format text (simple parser for markdown headings/bullet points)
  let formatted = text.split('\n').map(line => {
    let clean = line.trim();
    if (clean.startsWith('**') && clean.endsWith('**')) {
      return `<strong class="text-white block mt-2 text-sm">${clean.replace(/\*\*/g, '')}</strong>`;
    }
    if (clean.startsWith('*') || clean.startsWith('-')) {
      return `<div class="flex gap-2 text-xs py-0.5"><span class="text-cyan-400">•</span><span>${clean.substring(1).trim().replace(/\*\*/g, '<strong>').replace(/\*\*/g, '</strong>')}</span></div>`;
    }
    // Replace **bold** anywhere in string
    let parsedLine = clean;
    while (parsedLine.includes('**')) {
      parsedLine = parsedLine.replace('**', '<strong>').replace('**', '</strong>');
    }
    return `<p class="mt-1">${parsedLine}</p>`;
  }).join('');

  bubble.innerHTML = formatted;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

// Toast notification controller
function showToast(message, type = 'success') {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  if (type === 'error') {
    toast.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> <span>${message}</span>`;
  } else {
    toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>${message}</span>`;
  }

  container.appendChild(toast);
  
  // Animate in
  setTimeout(() => {
    toast.classList.add("show");
  }, 10);

  // Remove toast
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}

// Sub-Tab prediction view router
function switchPredictionMode(mode) {
  const manualBtn = document.getElementById("sub-tab-manual-btn");
  const batchBtn = document.getElementById("sub-tab-batch-btn");
  const manualDiv = document.getElementById("predict-mode-manual");
  const batchDiv = document.getElementById("predict-mode-batch");

  if (mode === 'manual') {
    manualBtn.classList.add("active");
    batchBtn.classList.remove("active");
    manualDiv.classList.remove("hidden");
    batchDiv.classList.add("hidden");
  } else {
    batchBtn.classList.add("active");
    manualBtn.classList.remove("active");
    batchDiv.classList.remove("hidden");
    manualDiv.classList.add("hidden");
  }
}

// Sub-Tab dashboard view router (Fleet Analytics vs Digital Twin Sandbox)
function switchDashboardSubTab(subTabId) {
  const overviewBtn = document.getElementById("db-tab-overview-btn");
  const twinBtn = document.getElementById("db-tab-twin-btn");
  const overviewContent = document.getElementById("dashboard-overview-content");
  const twinContent = document.getElementById("dashboard-twin-content");

  if (!overviewBtn || !twinBtn || !overviewContent || !twinContent) return;

  if (subTabId === 'overview') {
    overviewBtn.classList.add("active");
    twinBtn.classList.remove("active");
    overviewContent.classList.remove("hidden");
    twinContent.classList.add("hidden");
    // Dispatch window resize event to force Plotly charts to adapt to visible size
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 100);
  } else {
    twinBtn.classList.add("active");
    overviewBtn.classList.remove("active");
    twinContent.classList.remove("hidden");
    overviewContent.classList.add("hidden");
  }
}

// Sensor Group tab router in Manual Telemetry form
function switchSensorGroup(groupId) {
  const groups = ['thermal', 'speed', 'fluid'];
  groups.forEach(g => {
    const btn = document.getElementById(`sensor-tab-${g}-btn`);
    const div = document.getElementById(`sensor-group-${g}`);
    if (g === groupId) {
      btn?.classList.add("active");
      div?.classList.remove("hidden");
    } else {
      btn?.classList.remove("active");
      div?.classList.add("hidden");
    }
  });
}

// Fetch and render system logs from FastAPI backend
async function loadSystemLogs() {
  const terminal = document.getElementById("system-terminal-logs");
  if (!terminal) return;
  
  try {
    const res = await fetch(`${API_BASE}/api/system-logs`);
    if (!res.ok) throw new Error("Logger API error");
    const data = await res.json();
    
    const logsHtml = data.logs.join("\n");
    
    // Detect if user scrolled up, if not, auto-scroll to bottom
    const isScrolledToBottom = terminal.scrollHeight - terminal.clientHeight <= terminal.scrollTop + 20;
    
    terminal.innerText = logsHtml;
    
    if (isScrolledToBottom || terminal.scrollTop === 0) {
      terminal.scrollTop = terminal.scrollHeight;
    }
  } catch (err) {
    console.error("Failed to load system logs:", err);
  }
}
