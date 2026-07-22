import os
import time
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

import predictor
import recommendation
import business
import explainability
import copilot

# Initialize FastAPI and CORS
app = FastAPI(
    title="AeroGuard AI - Predictive Maintenance Platform",
    description="Enterprise API Gateway for Industrial Asset Health and RUL predictions."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories and mount templates/static
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# Mount Static Files and Templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

from collections import deque
SYSTEM_LOGS = deque(maxlen=100)

def log_event(message: str):
    timestamp = time.strftime("%H:%M:%S")
    SYSTEM_LOGS.append(f"[{timestamp}] {message}")

# Global dataset caches
TRAIN_DF = None
TEST_DF = None
RUL_DF = None
TEST_FEATURES_DF = None

# Global state for simulated fleet (mission control)
SIMULATED_FLEET = {}

def initialize_fleet_simulation():
    """
    Initializes a dynamic mission control simulator state for 30 active turbofan engines
    pulled from the test set, giving them varied cycle durations and wear multipliers.
    """
    global SIMULATED_FLEET, TEST_DF, RUL_DF
    SIMULATED_FLEET = {}
    
    np.random.seed(42)  # For reproducible simulation starters
    
    # We load engines 1 to 30 from the NASA test set
    for unit in range(1, 31):
        unit_data = TEST_DF[TEST_DF["unit_number"] == unit].sort_values(by="time_in_cycles")
        max_cycle = int(unit_data["time_in_cycles"].max())
        
        # True RUL and total lifespan calculation
        true_rul_val = int(RUL_DF.iloc[unit - 1]["RUL"])
        total_lifespan = max_cycle + true_rul_val
        
        # Introduce critical and warning assets on load to make metrics realistic on startup
        if unit in [3, 8, 14, 22]:
            # Close to failure (RUL between 4 and 14 cycles remaining)
            start_cycle = max(10, total_lifespan - np.random.randint(4, 15))
        else:
            # Standard random middle cycle
            start_cycle = int(np.random.randint(15, max(20, max_cycle - 5)))
        
        SIMULATED_FLEET[unit] = {
            "unit_number": unit,
            "current_cycle": start_cycle,
            "max_cycle_in_dataset": max_cycle,
            "total_lifespan": total_lifespan,
            "original_lifespan": total_lifespan,
            "sensor_multipliers": {s: 1.0 for s in predictor.ACTIVE_SENSORS}, # what-if parameters
            "maintenance_history": []
        }
    print(f"Loaded simulated fleet state for {len(SIMULATED_FLEET)} engines.")

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup hook to load dataset, train/load the XGBoost model,
    pre-calculate telemetry features, and spin up the simulation.
    """
    global TRAIN_DF, TEST_DF, RUL_DF, TEST_FEATURES_DF
    log_event("AeroGuard AI backend gateway starting...")
    try:
        log_event("Loading NASA CMAPSS telemetry dataset...")
        TRAIN_DF, TEST_DF, RUL_DF = predictor.copy_or_load_dataset()
        log_event(f"Dataset loaded. Train rows: {len(TRAIN_DF)}, Test rows: {len(TEST_DF)}")
        
        log_event("Initializing XGBoost prediction model...")
        predictor.get_model()
        log_event("Model loaded and ready for predictions.")
        
        log_event("Pre-calculating rolling features for the entire test set...")
        TEST_FEATURES_DF = predictor.engineer_features(TEST_DF)
        log_event("Pre-calculation complete. Telemetry feature cache populated.")
        
        log_event("Initializing fleet simulation states...")
        initialize_fleet_simulation()
        log_event("Fleet monitoring simulation online.")
    except Exception as e:
        log_event(f"Startup error: {e}")
        print(f"Startup warning (dataset might not be ready yet): {e}")

def get_engine_data_at_cycle(unit_number: int, cycle: int, sim_state=None):
    """
    Reconstructs history of the engine up to the current cycle, using the pre-calculated
    telemetry feature cache for instantaneous retrieval (~0.1ms), falling back to on-the-fly
    calculations only if what-if multipliers are active in the simulator.
    """
    global TEST_FEATURES_DF, TEST_DF
    
    # Check if there are active multipliers in the simulation state
    has_multipliers = False
    if sim_state and "sensor_multipliers" in sim_state:
        for s, mult in sim_state["sensor_multipliers"].items():
            if mult != 1.0:
                has_multipliers = True
                break
                
    if has_multipliers:
        # What-If is active: Reconstruct history and calculate features on-the-fly
        unit_data = TEST_DF[(TEST_DF["unit_number"] == unit_number) & (TEST_DF["time_in_cycles"] <= cycle)].copy()
        if len(unit_data) == 0:
            rows = []
            for c in range(1, cycle + 1):
                row = {"unit_number": unit_number, "time_in_cycles": c, "op_setting_1": 0.002, "op_setting_2": 0.0002, "op_setting_3": 100.0}
                for s, base in predictor.SENSOR_BASELINES.items():
                    row[s] = base
                rows.append(row)
            unit_data = pd.DataFrame(rows)
            
        for s, mult in sim_state["sensor_multipliers"].items():
            unit_data[s] = unit_data[s] * mult
            
        features_df = predictor.engineer_features(unit_data)
        last_row = features_df.iloc[[-1]]
        unit_history = unit_data
    else:
        # No What-If: retrieve instantly from the pre-calculated features!
        last_row = TEST_FEATURES_DF[(TEST_FEATURES_DF["unit_number"] == unit_number) & (TEST_FEATURES_DF["time_in_cycles"] == cycle)].copy()
        if len(last_row) == 0:
            # Fallback to the latest cycle available in cache for this unit
            last_row = TEST_FEATURES_DF[TEST_FEATURES_DF["unit_number"] == unit_number].iloc[[-1]].copy()
        
        # Pull history slice silently if needed for baseline comparisons
        unit_history = TEST_DF[(TEST_DF["unit_number"] == unit_number) & (TEST_DF["time_in_cycles"] <= cycle)]
        
    return last_row, unit_history

def compute_engine_metrics(unit_number: int, include_explainability: bool = False):
    """
    Runs model inference, risk scoring, recommendations, and business impact for a simulated engine.
    """
    state = SIMULATED_FLEET[unit_number]
    cycle = state["current_cycle"]
    
    last_row, history = get_engine_data_at_cycle(unit_number, cycle, state)
    model_meta = predictor.get_model()
    
    predicted_rul = predictor.predict_rul(last_row, model_meta["feature_cols"])
    health_score = predictor.calculate_health_score(predicted_rul)
    risk_level, color = predictor.classify_risk(predicted_rul)
    confidence = predictor.calculate_confidence(predicted_rul)
    
    # Parse active anomalies on the current cycle
    baseline_row = history.iloc[0]
    current_row = history.iloc[-1]
    anomalies = predictor.parse_sensor_anomalies(current_row, baseline_row)
    
    # Generate decision-support recommendation and business impact
    rec = recommendation.generate_maintenance_recommendation(predicted_rul, health_score, anomalies)
    bus = business.calculate_business_impact(predicted_rul, health_score, anomalies, risk_level)
    
    # SHAP Explainability (Computed on-demand only to keep fleet calculations extremely fast)
    if include_explainability:
        explain_data = explainability.explain_prediction_shap(last_row, predicted_rul, model_meta["feature_cols"])
    else:
        explain_data = {"method": "Skipped", "sensor_impacts": [], "natural_language": "Explainability details skipped."}
    
    return {
        "unit_number": unit_number,
        "current_cycle": cycle,
        "predicted_rul": round(predicted_rul, 1),
        "health_score": round(health_score, 1),
        "risk_level": risk_level,
        "risk_color": color,
        "confidence_score": round(confidence, 1),
        "maintenance_priority": rec["priority_code"],
        "recommendation": rec["action"],
        "recommendation_details": rec["details"],
        "business_impact": bus,
        "anomalies": anomalies,
        "maintenance_history": state["maintenance_history"],
        "explainability": explain_data
    }

# Pydantic schemas for request bodies
class PredictRequest(BaseModel):
    unit_number: int
    time_in_cycles: int
    sensor_2: float
    sensor_3: float
    sensor_4: float
    sensor_7: float
    sensor_8: float
    sensor_11: float
    sensor_12: float
    sensor_13: float
    sensor_14: float
    sensor_15: float
    sensor_17: float
    sensor_20: float
    sensor_21: float

class CopilotRequest(BaseModel):
    unit_number: int
    cycle: int
    predicted_rul: float
    health_score: float
    risk_level: str
    priority: str
    anomalies: List[dict]
    question: str

class SimulateRequest(BaseModel):
    unit_number: int
    type: str # compressor_wash, bearing_replace, core_overhaul

# API ENDPOINTS

@app.get("/")
async def root(request: Request):
    """
    Serves the primary UI dashboard and SaaS Landing page.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/model-info")
async def get_model_info():
    """
    Exposes RMSE, trained features, and global importances.
    """
    try:
        meta = predictor.get_model()
        return {
            "status": "trained",
            "rmse": round(meta["rmse"], 3),
            "feature_count": len(meta["feature_cols"]),
            "feature_importances": meta["feature_importances"][:15] # Top 15 features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model loading failed: {e}")

@app.get("/api/dashboard")
async def get_dashboard_summary():
    """
    Calculates aggregate metrics for the active fleet.
    """
    if not SIMULATED_FLEET:
        raise HTTPException(status_code=503, detail="Simulated fleet not initialized.")
        
    engines = []
    for unit in SIMULATED_FLEET:
        engines.append(compute_engine_metrics(unit, include_explainability=False))
        
    # Global aggregates
    avg_rul = np.mean([e["predicted_rul"] for e in engines])
    avg_health = np.mean([e["health_score"] for e in engines])
    critical_count = sum(1 for e in engines if e["risk_level"] == "Critical")
    warning_count = sum(1 for e in engines if e["risk_level"] == "High Risk")
    due_count = sum(1 for e in engines if e["maintenance_priority"] in ["P1", "P2"])
    
    # Model info for accuracy widget
    meta = predictor.get_model()
    accuracy_pct = max(75.0, 100.0 - (meta["rmse"] / 125.0 * 100.0))
    
    return {
        "fleet_health_score": round(avg_health, 1),
        "average_rul": round(avg_rul, 1),
        "critical_engines": critical_count,
        "warning_engines": warning_count,
        "maintenance_due": due_count,
        "prediction_accuracy_pct": round(accuracy_pct, 1),
        "total_active_assets": len(engines)
    }

@app.get("/api/analytics")
async def get_analytics_charts():
    """
    Provides risk distribution, RUL histogram, and timeline data for Plotly.js charts (explainability is skipped to run fast).
    """
    engines = [compute_engine_metrics(unit, include_explainability=False) for unit in SIMULATED_FLEET]
    
    # Risk distribution
    risks = [e["risk_level"] for e in engines]
    risk_counts = {
        "Low Risk": risks.count("Low Risk"),
        "Medium Risk": risks.count("Medium Risk"),
        "High Risk": risks.count("High Risk"),
        "Critical": risks.count("Critical")
    }
    
    # Histogram of RULs
    ruls = [e["predicted_rul"] for e in engines]
    
    # Timeline plot: Predicted RULs over Unit numbers
    timeline = [{"unit": e["unit_number"], "rul": e["predicted_rul"], "risk": e["risk_level"]} for e in engines]
    
    # Health score distributions
    healths = [e["health_score"] for e in engines]
    
    return {
        "risk_distribution": risk_counts,
        "rul_values": ruls,
        "health_values": healths,
        "timeline": timeline
    }

@app.get("/api/fleet")
async def get_fleet_table():
    """
    Returns full data rows for the Fleet Monitor grid (explainability is skipped to run fast).
    """
    engines = [compute_engine_metrics(unit, include_explainability=False) for unit in SIMULATED_FLEET]
    return {"engines": engines}

@app.get("/api/fleet/{unit_number}")
async def get_fleet_engine(unit_number: int):
    """
    Returns full data details for a focused engine including local SHAP explainability.
    """
    if unit_number not in SIMULATED_FLEET:
        raise HTTPException(status_code=404, detail=f"Engine #{unit_number} not active in fleet.")
    return compute_engine_metrics(unit_number, include_explainability=True)

@app.post("/api/predict")
async def manual_predict(req: PredictRequest):
    """
    Processes manual sensor inputs. Reconstructs previous rolling data
    from the test set for consistency before making a prediction.
    """
    t0 = time.time()
    log_event(f"Manual Predict request received for Engine #{req.unit_number}, Cycle {req.time_in_cycles}")
    try:
        # 1. Fetch test set history up to time_in_cycles - 1
        unit = req.unit_number
        cycle = req.time_in_cycles
        
        unit_history = TEST_DF[(TEST_DF["unit_number"] == unit) & (TEST_DF["time_in_cycles"] < cycle)].copy()
        
        # 2. Append the new manual row as the latest cycle
        manual_row = {
            "unit_number": unit,
            "time_in_cycles": cycle,
            "op_setting_1": 0.002, "op_setting_2": 0.0002, "op_setting_3": 100.0
        }
        for s in predictor.ACTIVE_SENSORS:
            manual_row[s] = getattr(req, s)
            
        new_row_df = pd.DataFrame([manual_row])
        combined_df = pd.concat([unit_history, new_row_df], ignore_index=True)
        
        # 3. Calculate rolling/drift metrics
        log_event(f"Calculating rolling features and drift indicators (Row count: {len(combined_df)})...")
        feat_df = predictor.engineer_features(combined_df)
        last_row = feat_df.iloc[[-1]]
        
        # 4. Predict
        model_meta = predictor.get_model()
        predicted_rul = predictor.predict_rul(last_row, model_meta["feature_cols"])
        health_score = predictor.calculate_health_score(predicted_rul)
        risk_level, color = predictor.classify_risk(predicted_rul)
        confidence = predictor.calculate_confidence(predicted_rul)
        
        # Parse anomalies vs initial baseline cycle
        baseline_val = combined_df.iloc[0] if len(combined_df) > 1 else new_row_df.iloc[0]
        anomalies = predictor.parse_sensor_anomalies(manual_row, baseline_val)
        
        # Rec & Business Engine
        rec = recommendation.generate_maintenance_recommendation(predicted_rul, health_score, anomalies)
        bus = business.calculate_business_impact(predicted_rul, health_score, anomalies, risk_level)
        
        # SHAP Explainability
        explain_data = explainability.explain_prediction_shap(last_row, predicted_rul, model_meta["feature_cols"])
        
        t1 = time.time()
        elapsed_ms = int((t1 - t0) * 1000)
        log_event(f"Prediction successful (RUL: {round(predicted_rul, 1)} cycles, Health: {round(health_score, 1)}%) in {elapsed_ms}ms")
        log_event(f"SHAP attribution complete ({explain_data['method']} mode)")
        log_event(f"Business calculations complete: Projected financial savings = ${int(bus['total_financial_savings'])}")
        
        return {
            "predicted_rul": round(predicted_rul, 1),
            "health_score": round(health_score, 1),
            "risk_level": risk_level,
            "risk_color": color,
            "confidence_score": round(confidence, 1),
            "maintenance_priority": rec["priority_code"],
            "recommendation": rec["action"],
            "recommendation_details": rec["details"],
            "business_impact": bus,
            "anomalies": anomalies,
            "explainability": explain_data
        }
    except Exception as e:
        log_event(f"Manual prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Manual prediction failed: {e}")

@app.post("/api/upload")
async def csv_upload(file: UploadFile = File(...)):
    """
    Accepts CSV upload of sensor data. Evaluates RUL for each row in the CSV
    and returns a summarized flight logs analysis response.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    t0 = time.time()
    log_event(f"CSV Upload request received: filename='{file.filename}'")
    try:
        # Load uploaded CSV
        uploaded_df = pd.read_csv(file.file)
        
        # Basic validation
        required_cols = ["unit_number", "time_in_cycles"] + predictor.ACTIVE_SENSORS
        missing = [c for c in required_cols if c not in uploaded_df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"CSV missing columns: {', '.join(missing)}")
            
        # Run rolling averages (this works row-by-row grouping by unit in the CSV)
        log_event(f"Parsing CSV... Calculating rolling features on {len(uploaded_df)} total records...")
        feat_df = predictor.engineer_features(uploaded_df)
        model_meta = predictor.get_model()
        
        predictions = []
        # Calculate RUL for each engine group's latest cycle
        latest_rows = feat_df.groupby("unit_number").last().reset_index()
        
        for _, row in latest_rows.iterrows():
            row_df = pd.DataFrame([row])
            unit_id = int(row["unit_number"])
            cycle = int(row["time_in_cycles"])
            
            pred = predictor.predict_rul(row_df, model_meta["feature_cols"])
            health = predictor.calculate_health_score(pred)
            risk, color = predictor.classify_risk(pred)
            
            # Simple anomaly check (last vs first of this unit in upload)
            unit_history = uploaded_df[uploaded_df["unit_number"] == unit_id]
            base = unit_history.iloc[0]
            current = unit_history.iloc[-1]
            anomalies = predictor.parse_sensor_anomalies(current, base)
            
            rec = recommendation.generate_maintenance_recommendation(pred, health, anomalies)
            bus = business.calculate_business_impact(pred, health, anomalies, risk)
            
            predictions.append({
                "unit_number": unit_id,
                "cycle": cycle,
                "predicted_rul": round(pred, 1),
                "health_score": round(health, 1),
                "risk_level": risk,
                "risk_color": color,
                "priority": rec["priority_code"],
                "recommendation": rec["action"],
                "savings": bus["total_financial_savings"]
            })
            
        total_savings = sum(p["savings"] for p in predictions)
        critical_count = sum(1 for p in predictions if p["risk_level"] == "Critical")
        
        t1 = time.time()
        elapsed_ms = int((t1 - t0) * 1000)
        log_event(f"CSV processed in {elapsed_ms}ms. Analyzed {len(predictions)} engines. Critical found: {critical_count}")
        log_event(f"Total projected parts cost savings: ${int(total_savings)}")
        
        return {
            "status": "success",
            "engines_analyzed_count": len(predictions),
            "critical_assets_found": critical_count,
            "projected_cost_savings": round(total_savings, 2),
            "predictions": predictions
        }
    except Exception as e:
        log_event(f"CSV Parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"CSV Parsing failure: {e}")

@app.get("/api/download-dataset")
async def download_dataset():
    """
    Exports a clean CSV representation of the NASA CMAPSS test template dataset (FD001) for local review.
    """
    import io
    from fastapi.responses import StreamingResponse
    try:
        csv_buffer = io.StringIO()
        TEST_DF.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nasa_cmapss_test_dataset.csv"}
        )
    except Exception as e:
        log_event(f"Dataset download failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate dataset download: {e}")

@app.post("/api/copilot")
async def copilot_chat(req: CopilotRequest):
    """
    Main chat gateway connecting frontend messages to the Copilot.
    Parses dynamic engine focus shifts from the user question to override context parameters,
    and constructs a fleet summary list to enable offline fleet-wide queries.
    """
    import re
    unit_number = req.unit_number
    cycle = req.cycle
    predicted_rul = req.predicted_rul
    health_score = req.health_score
    risk_level = req.risk_level
    priority = req.priority
    anomalies = req.anomalies
    context_shifted = False
    explain_data = None

    # Construct fleet summary for conversational listing queries (extremely fast due to cached TEST_FEATURES_DF)
    fleet_summary = []
    for u in SIMULATED_FLEET:
        m = compute_engine_metrics(u, include_explainability=False)
        fleet_summary.append({
            "unit_number": u,
            "risk_level": m["risk_level"],
            "rul": m["predicted_rul"],
            "priority": m["maintenance_priority"]
        })

    # Regex detect explicit engine focus requests e.g. "engine 2" or "unit 2"
    match = re.search(r'(?:engine|unit|#)\s*(\d+)', req.question.lower())
    if match:
        target_unit = int(match.group(1))
        if target_unit in SIMULATED_FLEET:
            metrics = compute_engine_metrics(target_unit, include_explainability=True)
            unit_number = target_unit
            cycle = metrics["current_cycle"]
            predicted_rul = metrics["predicted_rul"]
            health_score = metrics["health_score"]
            risk_level = metrics["risk_level"]
            priority = metrics["maintenance_priority"]
            anomalies = metrics["anomalies"]
            explain_data = metrics["explainability"]
            context_shifted = True
            log_event(f"Copilot query redirected to requested Engine #{unit_number} context")

    log_event(f"Copilot query received for Engine #{unit_number}: '{req.question[:30]}...'")
    t0 = time.time()
    reply = copilot.ask_copilot(
        unit_number=unit_number,
        cycle=cycle,
        predicted_rul=predicted_rul,
        health_score=health_score,
        risk_level=risk_level,
        priority=priority,
        anomalies=anomalies,
        question=req.question,
        fleet_summary=fleet_summary
    )
    t1 = time.time()
    elapsed_ms = int((t1 - t0) * 1000)
    log_event(f"Copilot response generated in {elapsed_ms}ms")
    
    response_payload = {"reply": reply}
    if context_shifted:
        response_payload["context_shift"] = {
            "unit_number": unit_number,
            "cycle": cycle,
            "predicted_rul": round(predicted_rul, 1),
            "health_score": round(health_score, 1),
            "risk_level": risk_level,
            "maintenance_priority": priority,
            "anomalies": anomalies,
            "explainability": explain_data
        }
    return response_payload

@app.post("/api/simulate")
async def simulate_maintenance(req: SimulateRequest):
    """
    Applies repairs to simulated engines in mission control, updating wear multipliers
    and extending simulated total lifespan cycles.
    """
    unit_id = req.unit_number
    m_type = req.type
    
    log_event(f"Triggered What-If simulation: type='{m_type}' on Engine #{unit_id}")
    if unit_id not in SIMULATED_FLEET:
        log_event(f"What-If simulation failed: Engine #{unit_id} not found.")
        raise HTTPException(status_code=404, detail=f"Engine {unit_id} not active in fleet.")
        
    state = SIMULATED_FLEET[unit_id]
    before = compute_engine_metrics(unit_id)
    
    extended = 0
    desc = ""
    
    if m_type == "compressor_wash":
        # Compressor wash: restores temperature and pressure multipliers
        state["sensor_multipliers"]["sensor_2"] = 0.993 # lower LPC temp
        state["sensor_multipliers"]["sensor_3"] = 0.990 # lower HPC temp
        state["sensor_multipliers"]["sensor_4"] = 0.992 # lower LPT temp
        state["sensor_multipliers"]["sensor_7"] = 1.004 # restore pressure
        state["total_lifespan"] += 35
        extended = 35
        desc = "Performed high-pressure compressor core wash. Flushed salt and carbon blade deposits, restoring airflow ratio."
        
    elif m_type == "bearing_replace":
        # Bearing replacement: reduces shaft speeds vibrations
        state["sensor_multipliers"]["sensor_8"] = 0.994 # Nf speed
        state["sensor_multipliers"]["sensor_11"] = 0.993 # Ps30 static pressure
        state["sensor_multipliers"]["sensor_13"] = 0.995 # NRf fan speed
        state["total_lifespan"] += 60
        extended = 60
        desc = "Swapped degraded rotor shaft bearings. Reduced high-frequency friction and shaft oscillation coefficients."
        
    elif m_type == "core_overhaul":
        # Reset all wear parameters back to baseline
        state["sensor_multipliers"] = {s: 1.0 for s in predictor.ACTIVE_SENSORS}
        state["current_cycle"] = 10  # Reset cycle to healthy starting zone
        state["total_lifespan"] = state["original_lifespan"]
        extended = 140
        desc = "Complete hot-section teardown and core blade replacement. Engine parameters re-calibrated to zero-hour equivalent."
        
    else:
        raise HTTPException(status_code=400, detail="Invalid maintenance type.")
        
    # Log repair details
    state["maintenance_history"].append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "type": m_type,
        "description": desc,
        "cycle": before["current_cycle"]
    })
    
    after = compute_engine_metrics(unit_id)
    log_event(f"What-If complete: extended cycles = +{extended}, post-service RUL = {round(after['predicted_rul'], 1)} cycles")
    
    return {
        "success": True,
        "maintenance_applied": m_type,
        "description": desc,
        "extended_cycles": extended,
        "before": before,
        "after": after
    }

@app.post("/api/reset")
async def reset_simulation():
    """
    Resets simulated engines back to their default cycles and parameters.
    """
    log_event("Simulated fleet state reset to baseline cycles.")
    initialize_fleet_simulation()
    return {"status": "success", "message": "Simulation reset successfully."}

@app.post("/api/tick")
async def tick_simulation():
    """
    Ticks all active simulated engines forward by 1 operating cycle.
    If an engine reaches its lifespan limit, it stops accumulating cycles.
    """
    log_event("Simulation time advanced: Ticked active simulated engines by 1 cycle.")
    for unit in SIMULATED_FLEET:
        state = SIMULATED_FLEET[unit]
        if state["current_cycle"] < state["total_lifespan"]:
            state["current_cycle"] += 1
    return {"status": "success", "message": "Simulated time advanced by 1 cycle."}

@app.get("/api/system-logs")
async def get_system_logs():
    """
    Returns the accumulated in-memory console log strings.
    """
    return {"logs": list(SYSTEM_LOGS)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
