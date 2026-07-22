import os
import time
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai

import data_handler
import ml_pipeline

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global variables for model and data
MODEL_METADATA = None
TRAIN_DF = None
TEST_DF = None
RUL_DF = None

# Fleet Simulator State: Keep track of current cycle for simulated active engines
SIMULATED_ENGINES = {}

def init_simulator_state():
    """
    Initializes simulation states for a subset of engines (e.g., units 1 to 20 from test set).
    This allows the UI to show a scrolling, real-time updated mission control dashboard.
    """
    global SIMULATED_ENGINES, TEST_DF, RUL_DF
    SIMULATED_ENGINES = {}
    
    # We take engines 1 to 15
    for unit in range(1, 16):
        unit_data = TEST_DF[TEST_DF["unit_number"] == unit].sort_values(by="time_in_cycles")
        max_cycle = int(unit_data["time_in_cycles"].max())
        
        # We start the simulation at a random cycle in the middle of their operational life
        # to show varying levels of risk
        start_cycle = np.random.randint(15, max(20, max_cycle - 10))
        
        # Ground truth total life for this simulated engine
        # In test set, true RUL is RUL_DF[unit-1]. So total lifespan = max_cycle + true_RUL
        true_rul_val = int(RUL_DF.iloc[unit - 1]["RUL"])
        total_lifespan = max_cycle + true_rul_val
        
        SIMULATED_ENGINES[unit] = {
            "unit_number": unit,
            "current_cycle": start_cycle,
            "max_cycle_in_dataset": max_cycle,
            "total_lifespan": total_lifespan,
            "original_lifespan": total_lifespan,
            "sensor_multipliers": {s: 1.0 for s in ml_pipeline.ACTIVE_SENSORS}, # used for what-if scenarios
            "maintenance_history": []
        }
    print(f"Initialized live simulation state for {len(SIMULATED_ENGINES)} engines.")

# Startup datasets and models are loaded globally below

# We will load data and model immediately upon execution
try:
    print("Loading datasets...")
    TRAIN_DF, TEST_DF, RUL_DF = data_handler.load_dataset()
    print("Loading ML model...")
    MODEL_METADATA = ml_pipeline.load_trained_model()
    init_simulator_state()
except Exception as e:
    print(f"Error during startup loading: {e}")

def get_engine_features_at_cycle(unit_number, cycle, simulated_state=None):
    """
    Constructs the feature row for a specific engine at a specific cycle,
    incorporating any simulated maintenance offsets.
    """
    # Fetch all data for this unit up to the current cycle
    unit_data = TEST_DF[(TEST_DF["unit_number"] == unit_number) & (TEST_DF["time_in_cycles"] <= cycle)].copy()
    
    if len(unit_data) == 0:
        # Fallback to generating synthetic engine slice if not in dataset
        unit_data = data_handler.generate_synthetic_engine_data(unit_number, max_cycles=cycle)
    
    # Apply simulated modifications (like what-if repair overrides)
    if simulated_state and "sensor_multipliers" in simulated_state:
        for sensor, mult in simulated_state["sensor_multipliers"].items():
            unit_data[sensor] = unit_data[sensor] * mult
            
    # Run the feature engineering pipeline
    feat_df = ml_pipeline.engineer_features(unit_data)
    
    # Get the last row (which represents the state at the current cycle)
    last_row = feat_df.iloc[[-1]]
    
    X = last_row[MODEL_METADATA["feature_cols"]]
    return X, last_row

def compute_engine_metrics(unit):
    state = SIMULATED_ENGINES[unit]
    cycle = state["current_cycle"]
    
    # Predict RUL using our XGBoost model
    X, last_row = get_engine_features_at_cycle(unit, cycle, state)
    predicted_rul = float(MODEL_METADATA["model"].predict(X)[0])
    predicted_rul = max(0.0, predicted_rul)
    
    # Calculate health score (0-100) based on RUL
    # Capped at 100
    health_score = min(100.0, (predicted_rul / 125.0) * 100.0)
    
    # Failure probability (high if RUL is low)
    failure_prob = 1.0 - (health_score / 100.0)
    # Give a sharper curve to failure probability near the end
    failure_prob = float(np.power(failure_prob, 2))
    
    # Risk Level & Priority
    if predicted_rul <= 25:
        risk_level = "CRITICAL"
        priority = "URGENT"
    elif predicted_rul <= 65:
        risk_level = "WARNING"
        priority = "MEDIUM"
    else:
        risk_level = "HEALTHY"
        priority = "LOW"
        
    return {
        "unit_number": unit,
        "current_cycle": cycle,
        "predicted_rul": round(predicted_rul, 1),
        "health_score": round(health_score, 1),
        "failure_prob": round(failure_prob * 100, 1),
        "risk_level": risk_level,
        "priority": priority,
        "maintenance_history": state["maintenance_history"]
    }

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "AeroGuard AI - Predictive Maintenance API Gateway",
        "status": "online",
        "model_loaded": MODEL_METADATA is not None,
        "endpoints": {
            "/api/health": "Check gateway and ML model health status",
            "/api/fleet": "Aggregate status of all active simulated assets",
            "/api/fleet/tick": "Tick simulation cycles forward (POST)",
            "/api/fleet/reset": "Reset simulation states (POST)",
            "/api/engine/<id>": "Retrieve historical telemetry curves for a specific engine",
            "/api/copilot": "Query Explainable AI Copilot for asset diagnostics (POST)",
            "/api/simulate": "Run What-If maintenance scenarios (POST)"
        }
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "model_loaded": MODEL_METADATA is not None,
        "rmse": round(MODEL_METADATA["rmse"], 3) if MODEL_METADATA else None
    })

@app.route("/api/fleet", methods=["GET"])
def get_fleet():
    fleet_data = []
    for unit in SIMULATED_ENGINES:
        try:
            metrics = compute_engine_metrics(unit)
            fleet_data.append(metrics)
        except Exception as e:
            print(f"Error computing metrics for engine {unit}: {e}")
            
    # Calculate global metrics
    avg_rul = np.mean([e["predicted_rul"] for e in fleet_data])
    avg_health = np.mean([e["health_score"] for e in fleet_data])
    critical_count = sum(1 for e in fleet_data if e["risk_level"] == "CRITICAL")
    warning_count = sum(1 for e in fleet_data if e["risk_level"] == "WARNING")
    healthy_count = sum(1 for e in fleet_data if e["risk_level"] == "HEALTHY")
    
    return jsonify({
        "engines": fleet_data,
        "stats": {
            "total_engines": len(fleet_data),
            "average_rul": round(avg_rul, 1),
            "average_health": round(avg_health, 1),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "healthy_count": healthy_count
        }
    })

@app.route("/api/fleet/tick", methods=["POST"])
def tick_fleet():
    """
    Advances the operational cycles of all simulated engines by 1.
    If an engine reaches its failure point, it remains at RUL 0.
    """
    for unit in SIMULATED_ENGINES:
        state = SIMULATED_ENGINES[unit]
        # Allow the engine to continue running up to its total lifespan
        if state["current_cycle"] < state["total_lifespan"]:
            state["current_cycle"] += 1
            
    return jsonify({"status": "success", "message": "Simulated fleet time ticked by 1 cycle."})

@app.route("/api/fleet/reset", methods=["POST"])
def reset_fleet():
    init_simulator_state()
    return jsonify({"status": "success", "message": "Simulation states reset to baselines."})

@app.route("/api/engine/<int:unit_id>", methods=["GET"])
def get_engine(unit_id):
    if unit_id not in SIMULATED_ENGINES:
        return jsonify({"error": f"Engine {unit_id} not found."}), 404
        
    state = SIMULATED_ENGINES[unit_id]
    current_cycle = state["current_cycle"]
    
    # Retrieve telemetry up to current cycle
    unit_data = TEST_DF[(TEST_DF["unit_number"] == unit_id) & (TEST_DF["time_in_cycles"] <= current_cycle)].copy()
    if len(unit_data) == 0:
        unit_data = data_handler.generate_synthetic_engine_data(unit_id, max_cycles=current_cycle)
        
    # Scale/modify sensors based on simulation state
    for sensor, mult in state["sensor_multipliers"].items():
        unit_data[sensor] = unit_data[sensor] * mult
        
    # Get current predicted metrics
    metrics = compute_engine_metrics(unit_id)
    
    # Subsample data for chart plotting (send last 50 cycles to avoid huge payloads)
    plot_df = unit_data.tail(50)
    
    telemetry_history = []
    for _, row in plot_df.iterrows():
        entry = {
            "cycle": int(row["time_in_cycles"]),
            "op_setting_1": float(row["op_setting_1"]),
            "op_setting_2": float(row["op_setting_2"]),
        }
        for s in ml_pipeline.ACTIVE_SENSORS:
            entry[s] = float(row[s])
        telemetry_history.append(entry)
        
    # Detect anomalous sensors based on current value vs baseline
    anomalies = []
    first_row = unit_data.iloc[0]
    last_row = unit_data.iloc[-1]
    
    for s in ml_pipeline.ACTIVE_SENSORS:
        base = first_row[s]
        current = last_row[s]
        diff_pct = (current - base) / base if base != 0 else 0
        
        # Standard anomaly directions
        # E.g. T24, T30, T50 drifting UP; P30, phi drifting DOWN
        is_anomalous = False
        if s in ["sensor_2", "sensor_3", "sensor_4", "sensor_11", "sensor_17"] and diff_pct > 0.015:
            is_anomalous = True
        elif s in ["sensor_7", "sensor_12", "sensor_20", "sensor_21"] and diff_pct < -0.015:
            is_anomalous = True
            
        if is_anomalous:
            anomalies.append({
                "sensor": s,
                "label": get_sensor_label(s),
                "baseline": round(base, 2),
                "current": round(current, 2),
                "deviation_pct": round(diff_pct * 100, 1)
            })
            
    return jsonify({
        "metadata": metrics,
        "telemetry_history": telemetry_history,
        "anomalies": anomalies,
        "max_cycles_completed": current_cycle
    })

@app.route("/api/simulate", methods=["POST"])
def simulate_maintenance():
    """
    What-If Simulator Endpoint.
    Applies corrective actions that temporarily reduce temperature/pressure
    or restore RUL life cycles.
    """
    data = request.json or {}
    unit_id = data.get("unit_number")
    maintenance_type = data.get("type") # compressor_wash, bearing_replace, core_overhaul
    
    if not unit_id or unit_id not in SIMULATED_ENGINES:
        return jsonify({"error": "Invalid engine ID."}), 400
        
    state = SIMULATED_ENGINES[unit_id]
    
    # Calculate original stats
    before_metrics = compute_engine_metrics(unit_id)
    
    description = ""
    extended_cycles = 0
    
    # Apply modifications
    if maintenance_type == "compressor_wash":
        # Reduces LPC/HPC temperatures (Sensor 2, 3, 4) back to baseline
        state["sensor_multipliers"]["sensor_2"] = 0.992
        state["sensor_multipliers"]["sensor_3"] = 0.990
        state["sensor_multipliers"]["sensor_4"] = 0.992
        # Restores P30 pressure slightly
        state["sensor_multipliers"]["sensor_7"] = 1.005
        
        state["total_lifespan"] += 35
        extended_cycles = 35
        description = "Water wash performed on core compressor blades. Reduced thermal exhaust signature and restored pressure ratios."
        
    elif maintenance_type == "bearing_replace":
        # Restores fan speed stability and static pressure
        state["sensor_multipliers"]["sensor_8"] = 0.995
        state["sensor_multipliers"]["sensor_11"] = 0.993
        state["sensor_multipliers"]["sensor_13"] = 0.995
        
        state["total_lifespan"] += 60
        extended_cycles = 60
        description = "Replaced degraded main shaft bearings. Vibration index minimized and rotational friction reduced."
        
    elif maintenance_type == "core_overhaul":
        # Reset all sensors back to pristine multipliers
        state["sensor_multipliers"] = {s: 1.0 for s in ml_pipeline.ACTIVE_SENSORS}
        # Substantially extends lifespan or resets cycle
        # Reset cycle back to a healthy state (e.g. cycle 10)
        state["current_cycle"] = 10
        state["total_lifespan"] = state["original_lifespan"]
        extended_cycles = 150
        description = "Complete core teardown and hot-section rebuild. Engine restored to zero-hour equivalent."
        
    else:
        return jsonify({"error": "Unsupported maintenance type."}), 400
        
    # Log maintenance action
    state["maintenance_history"].append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": maintenance_type,
        "description": description,
        "cycle": before_metrics["current_cycle"]
    })
    
    # Calculate new predicted stats
    after_metrics = compute_engine_metrics(unit_id)
    
    return jsonify({
        "success": True,
        "engine_id": unit_id,
        "maintenance_applied": maintenance_type,
        "description": description,
        "extended_cycles": extended_cycles,
        "before": before_metrics,
        "after": after_metrics
    })

@app.route("/api/copilot", methods=["POST"])
def copilot_explain():
    data = request.json or {}
    unit_id = data.get("unit_number")
    
    if not unit_id or unit_id not in SIMULATED_ENGINES:
        return jsonify({"error": "Invalid engine ID."}), 400
        
    # Retrieve current stats
    metrics = compute_engine_metrics(unit_id)
    engine_details = get_engine(unit_id).json
    
    anomalies = engine_details.get("anomalies", [])
    anomaly_text = ", ".join([f"{a['label']} ({a['deviation_pct']}% drift)" for a in anomalies])
    if not anomaly_text:
        anomaly_text = "No severe sensor drift detected (stable operation)."
        
    prompt = f"""
You are the AeroGuard AI Copilot, a certified turbine aeronautical engineer.
Analyze the following telemetry diagnostics:
- Engine ID: Unit {unit_id}
- Current Operational Cycle: {metrics['current_cycle']}
- Predicted Remaining Useful Life (RUL): {metrics['predicted_rul']} cycles
- Health Status: {metrics['risk_level']} (Urgency: {metrics['priority']})
- Active Telemetry Anomalies: {anomaly_text}

Provide a structured, professional diagnostic summary (3-4 sentences maximum). Include:
1. An explanation of *why* the engine has this risk level.
2. The specific sensor telemetry responsible.
3. Recommended corrective action (e.g. Compressor wash, core inspect, fuel flow adjustment) with a specific servicing window.
Output in concise Markdown bullet points.
"""

    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            explanation = response.text
        except Exception as e:
            print(f"Gemini API execution error: {e}. Using offline fallback.")
            explanation = get_offline_explanation(metrics, anomalies)
    else:
        explanation = get_offline_explanation(metrics, anomalies)
        
    return jsonify({
        "engine_id": unit_id,
        "copilot_analysis": explanation
    })

def get_sensor_label(sensor_name):
    labels = {
        "sensor_2": "T24 Total Temp (LPC)",
        "sensor_3": "T30 Total Temp (HPC)",
        "sensor_4": "T50 Total Temp (LPT)",
        "sensor_7": "P30 Total Pressure (HPC)",
        "sensor_8": "Nf Physical Fan Speed",
        "sensor_11": "Ps30 Static Pressure",
        "sensor_12": "phi Fuel ratio to Ps30",
        "sensor_13": "NRf Corrected Fan Speed",
        "sensor_14": "NRc Corrected Core Speed",
        "sensor_15": "BPR Bypass Ratio",
        "sensor_17": "htBleed Bleed Enthalpy",
        "sensor_20": "W31 HPT Coolant Bleed",
        "sensor_21": "W32 LPT Coolant Bleed"
    }
    return labels.get(sensor_name, sensor_name)

def get_offline_explanation(metrics, anomalies):
    unit_id = metrics["unit_number"]
    rul = metrics["predicted_rul"]
    
    if metrics["risk_level"] == "CRITICAL":
        trigger_sensors = ", ".join([a["label"] for a in anomalies[:2]]) if anomalies else "T30 High Exhaust Temperatures"
        return f"""* **Critical Degradation Alert**: Engine {unit_id} has an estimated Remaining Useful Life of **{rul} cycles**. Immediate maintenance scheduling is required.
* **Telemetry Drivers**: High core thermal profiles detected on `{trigger_sensors}` combined with significant pressure drop across the High Pressure Compressor (HPC).
* **Recommended Actions**: Schedule a **Core Overhaul** or **Bearing Replacement** within the next **5 operational cycles** to mitigate risk of catastrophic blade shear."""
    elif metrics["risk_level"] == "WARNING":
        trigger_sensors = ", ".join([a["label"] for a in anomalies[:2]]) if anomalies else "Sensor T24 upward thermal drift"
        return f"""* **Warning Health Index**: Engine {unit_id} is displaying mild sensor degradation with an estimated RUL of **{rul} cycles**.
* **Telemetry Drivers**: Initial thermal warnings on `{trigger_sensors}` and minor fuel-to-pressure ratio fluctuations.
* **Recommended Actions**: Schedule a **Compressor Wash** and a routine borescope blade check within the next **15-20 cycles** to restore thermal margins and extend operational lifespan."""
    else:
        return f"""* **Healthy Status**: Engine {unit_id} is operating within nominal parameters with a healthy estimated RUL of **{rul} cycles**.
* **Telemetry Drivers**: Telemetry signals show stable pressure ratios, normal vibration indices, and nominal bleed enthalpy coefficients.
* **Recommended Actions**: Continue scheduled flight ops. No preventive maintenance required at this interval. Re-evaluate at cycle {metrics['current_cycle'] + 20}."""

@app.route("/api/dataset", methods=["GET"])
def get_dataset():
    """
    Paginated viewer for the raw NASA CMAPSS training dataset.
    Helps users inspect the actual data points.
    """
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 15, type=int)
    unit_id = request.args.get("unit_number", None, type=int)
    
    df = TRAIN_DF
    if df is None:
        return jsonify({"error": "Dataset not loaded."}), 500
        
    if unit_id is not None:
        df = df[df["unit_number"] == unit_id]
        
    total_rows = len(df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    slice_df = df.iloc[start_idx:end_idx]
    
    rows = []
    for _, row in slice_df.iterrows():
        row_dict = {}
        for col in df.columns:
            val = row[col]
            if isinstance(val, (np.integer, int)):
                row_dict[col] = int(val)
            elif isinstance(val, (np.floating, float)):
                row_dict[col] = round(float(val), 4)
            else:
                row_dict[col] = str(val)
        rows.append(row_dict)
        
    return jsonify({
        "data": rows,
        "total_rows": total_rows,
        "page": page,
        "page_size": page_size,
        "pages": int(np.ceil(total_rows / page_size))
    })

@app.route("/api/copilot/chat", methods=["POST"])
def copilot_chat():
    """
    Interactive Chatbot Gateway. Handles conversational diagnostics.
    If GEMINI_API_KEY is available, queries Google Gemini 1.5.
    Otherwise, handles queries with a rule-based aerospace expert responder.
    """
    data = request.json or {}
    unit_id = data.get("unit_number")
    messages = data.get("messages", [])
    
    if not unit_id or unit_id not in SIMULATED_ENGINES:
        return jsonify({"error": "Invalid engine ID."}), 400
        
    if not messages:
        return jsonify({"error": "No messages provided."}), 400
        
    # Get the latest message from user
    latest_msg = messages[-1]["text"].lower()
    
    # Collect active engine context
    metrics = compute_engine_metrics(unit_id)
    engine_details = get_engine(unit_id).json
    anomalies = engine_details.get("anomalies", [])
    anomaly_names = [a["label"] for a in anomalies]
    
    # Formulate contextual system prompt
    context_prompt = f"""
    You are the AeroGuard AI Copilot, a certified aeronautical turbine engineer.
    The user is asking you questions about Engine #{unit_id}.
    Current Engine State:
    - Running Cycle: {metrics['current_cycle']}
    - Predicted Remaining Useful Life (RUL): {metrics['predicted_rul']} cycles
    - Health Condition: {metrics['risk_level']} (Servicing Urgency: {metrics['priority']})
    - Active Sensor Anomaly Flags: {', '.join(anomaly_names) if anomaly_names else 'None (Nominal)'}
    
    Please answer the user's question concisely in 2-3 sentences.
    User Question: "{messages[-1]['text']}"
    """
    
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(context_prompt)
            reply = response.text.strip()
            return jsonify({"reply": reply})
        except Exception as e:
            print(f"Gemini Chat execution error: {e}. Falling back to offline responder.")
            
    # Offline rule-based smart responder
    reply = get_offline_chat_response(latest_msg, metrics, anomalies)
    return jsonify({"reply": reply})

def get_offline_chat_response(msg, metrics, anomalies):
    unit_id = metrics["unit_number"]
    rul = metrics["predicted_rul"]
    risk = metrics["risk_level"]
    
    # Keyword routing
    if "hello" in msg or "hi " in msg or "hey" in msg:
        return f"Greetings! I am the AeroGuard AI Copilot. I can assist you with diagnostic telemetry and maintenance tasks for Engine #{unit_id}. What would you like to analyze?"
        
    elif "sensor 11" in msg or "ps30" in msg or "static pressure" in msg:
        return "Sensor 11 measures Ps30 (Static Pressure at High Pressure Compressor Outlet). As turbine blades degrade or clog, the backpressure increases, causing Ps30 to drift upwards. For Engine #{}, it is currently reading {}.".format(unit_id, "anomalous" if any(a["sensor"] == "sensor_11" for a in anomalies) else "nominal values")
        
    elif "sensor 3" in msg or "t30" in msg or "exhaust" in msg or "temperature" in msg:
        return "Sensor 3 monitors T30 (Total Temperature at High Pressure Compressor Outlet). Increased thermal readings indicate core friction, turbine wear, or fuel combustion imbalances. Keeping T30 clean is key to fuel efficiency."
        
    elif "sensor 7" in msg or "p30" in msg or "pressure" in msg:
        return "Sensor 7 tracks P30 (Total Pressure at the HPC Outlet). A drop in P30 pressure points to air compression leakage, blade warping, or seals wearing down."
        
    elif "wash" in msg or "compressor wash" in msg or "clean" in msg:
        return "A Compressor Core Wash removes salt, dirt, and carbon scale from the compressor blades. This reduces operating temperatures (like T30), restores airflow pressure, and adds +35 cycles of predicted Remaining Useful Life (RUL)."
        
    elif "bearing" in msg or "vibration" in msg or "shaft" in msg:
        return "Replacing the main shaft bearings minimizes mechanical friction and rotational drag. This stabilizes core fan speeds (Nf/Nc) and extends the engine's predicted RUL by +60 cycles."
        
    elif "overhaul" in msg or "rebuild" in msg or "fix" in msg:
        return "A Complete Engine Overhaul performs a hot-section rebuild and restores the entire turbine to zero-hour conditions, resetting sensor wear levels and returning the asset to peak operating efficiency."
        
    elif "rul" in msg or "useful life" in msg or "runs" in msg or "flights" in msg:
        if risk == "CRITICAL":
            return f"Engine #{unit_id} is in a CRITICAL state. It is predicted to fail in just {rul} cycles. Immediate scheduling of a bearing swap or overhaul is required."
        elif risk == "WARNING":
            return f"Engine #{unit_id} is showing early signs of degradation. Remaining life is estimated at {rul} cycles. A compressor wash should be scheduled within 15 runs."
        else:
            return f"Engine #{unit_id} is operating optimally. Predicted remaining useful life is a healthy {rul} cycles. Continue routine operations."
            
    else:
        # Generic helpful turbine engineering reply
        anomaly_text = ", ".join([a["label"] for a in anomalies]) if anomalies else "no active alarms"
        return f"Regarding Engine #{unit_id}: It is currently on cycle {metrics['current_cycle']} with a Remaining Useful Life of {rul} cycles. The system registers {anomaly_text}. For troubleshooting, I recommend checking compressor thermal profiles or running a simulator scenario."

if __name__ == "__main__":
    # In Windows environment, run Flask on localhost:5000
    app.run(host="127.0.0.1", port=5000, debug=True)
