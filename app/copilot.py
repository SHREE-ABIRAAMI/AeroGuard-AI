import os
import google.generativeai as genai
import predictor

def ask_copilot(unit_number, cycle, predicted_rul, health_score, risk_level, priority, anomalies, question, chat_history=None, fleet_summary=None):
    """
    Cognitive chatbot gateway for maintenance engineering support.
    Connects to Google Gemini API if GEMINI_API_KEY is defined in environment variables,
    otherwise routes the question through an expert-level offline rule-based responder.
    """
    
    # 1. Structure contextual summary for the LLM prompt
    anomaly_text = ", ".join([f"{a['label']} ({a['deviation_pct']}% drift)" for a in anomalies])
    if not anomaly_text:
        anomaly_text = "No severe sensor drift detected (all channels stable)."
        
    context_prompt = f"""You are the AeroGuard AI Maintenance Copilot, a certified senior turbine aerospace engineer.
You are troubleshooting Engine #{unit_number} which is currently at cycle {cycle}.
Here are the current telemetry and ML diagnostics:
- Estimated Remaining Useful Life (RUL): {predicted_rul} cycles
- Current Health Index: {health_score}%
- Risk Classification: {risk_level} (Servicing Priority: {priority})
- Active Sensor Deviations: {anomaly_text}

Answer the user's question with precise, technical engineering advice. Keep it concise (2-4 sentences max), structured with markdown bold headers, and maintain a highly professional aerospace operator tone.

User Question: "{question}"
"""

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            # Use gemini-1.5-flash for rapid, lightweight response
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(context_prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API chat call failed: {e}. Falling back to offline expert system.")
            
    # 2. Offline Fallback Chat Responder
    return get_offline_response(question, unit_number, cycle, predicted_rul, health_score, risk_level, anomalies, fleet_summary)

def get_offline_response(question, unit_number, cycle, predicted_rul, health_score, risk_level, anomalies, fleet_summary=None):
    q = question.lower().strip()
    
    # 1. Fleet-wide Risk Listing checking
    if any(kw in q for kw in ["list risky", "risky conditions", "risky engines", "critical engines", "active warnings", "list critical", "list warning", "which engines are critical", "which engines are risky", "which engines have risk"]):
        if fleet_summary:
            risky = [f for f in fleet_summary if f["risk_level"] in ["Critical", "High Risk", "Medium Risk"]]
            if risky:
                lines = ["**Active Fleet-wide Risk Report:**"]
                for eng in sorted(risky, key=lambda x: x["rul"]):
                    lines.append(f"- **Engine #{eng['unit_number']}**: {eng['risk_level']} (RUL: {int(eng['rul'])} cycles, Priority {eng['priority']})")
                lines.append("I recommend selecting these turbines in the sandbox to simulate repair wash/bearing solutions.")
                return "\n".join(lines)
            else:
                return "**Active Fleet-wide Risk Report:** All 30 active turbofan engines are currently running normally (Low Risk) under baseline wear tolerances."
        else:
            return "**Active Fleet-wide Risk Report:** Telemetry server offline. Unable to scan simulated fleet wear matrices."
            
    # 2. Simple keyword checking
    elif any(greet in q for greet in ["hello", "hi ", "hey", "greetings"]):
        return f"**AeroGuard Copilot Online.** Greetings, engineer. I am ready to assist with diagnostics for Engine #{unit_number} at cycle {cycle}. What system anomalies are we troubleshooting today?"
        
    elif any(kw in q for kw in ["sensor 11", "ps30", "static pressure"]):
        return "**Ps30 Static Pressure (Sensor 11) Analysis:** The static pressure at the High Pressure Compressor (HPC) outlet is a critical indicator of aerodynamic loading. Upward drift indicates backpressure build-up, typically caused by compressor blade fouling or nozzle guide vane erosion. Cleaning or borescope inspection is recommended."
        
    elif any(kw in q for kw in ["sensor 3", "t30", "hpc temp"]):
        return "**T30 HPC Outlet Temp (Sensor 3) Analysis:** Elevated T30 temperatures indicate excessive friction or combustion backflow in the High Pressure Compressor. This results in reduced thermal margins and accelerated blade degradation. Consider scheduling a Compressor Core Wash to restore nominal heat rejection."
        
    elif any(kw in q for kw in ["sensor 7", "p30", "hpc pressure"]):
        return "**P30 Core Pressure (Sensor 7) Analysis:** A downward drift in P30 total pressure points to pressure leakage, stator seal degradation, or blade profile warping in the HPC stages. It leads to a drop in thrust efficiency and requires close inspection during the next borescope check."
        
    elif any(kw in q for kw in ["compressor wash", "core wash", "wash"]):
        return "**Compressor Wash Impact:** A water wash flushes out accumulated salt, dust, and carbon scale from the LPC/HPC blades. In our simulation pipeline, executing this wash reduces core temperatures, restores air ratios, and extends the predicted RUL by **+35 cycles**."
        
    elif any(kw in q for kw in ["bearing", "shaft", "vibration", "lubrication"]):
        return "**Bearing Replacement Impact:** High shaft friction leads to speed anomalies (Nf/NRc) and mechanical vibration. Replacing the main shaft bearings reduces rotational drag, stabilizes rotor speeds, and extends the predicted RUL by **+60 cycles**."
        
    elif any(kw in q for kw in ["overhaul", "rebuild", "teardown"]):
        return "**Engine Core Overhaul:** A full overhaul involves complete engine teardown, replacement of life-limited parts (LLPs), and hot-section restoration. This resets the operational cycle count to zero-hour equivalent and returns all sensor channels to pristine baseline values."
        
    elif any(kw in q for kw in ["nasa", "cmapss", "dataset", "simulat"]):
        return "**NASA CMAPSS Dataset Context:** The Commercial Modular Aero-Propulsion System Simulation dataset was generated by NASA using a thermodynamic simulator. It models typical degradation across 21 sensors under standard flight conditions. Remaining Useful Life (RUL) represents cycles remaining before failure."
        
    elif any(kw in q for kw in ["rul", "useful life", "fail", "ground", "risk", "status", "health", "condition", "warning", "critical", "alert", "priority"]):
        if risk_level == "Critical":
            return f"**Critical Risk Alert:** Engine #{unit_number} has reached its wear limit with only **{int(predicted_rul)} cycles** predicted before failure (Health: {health_score}%). Immediate grounding (Priority P1) and hot-section turbine overhaul is required."
        elif risk_level == "High Risk":
            return f"**High Risk Advisory:** Engine #{unit_number} has **{int(predicted_rul)} cycles** of remaining useful life. Telemetry indicators show severe wear. Schedule maintenance (Priority P2) immediately."
        elif risk_level == "Medium Risk":
            return f"**Medium Risk Warning:** Engine #{unit_number} has **{int(predicted_rul)} cycles** remaining. Minor sensor drifts detected. Recommend scheduling maintenance (Priority P3) at next routine checkup."
        else:
            return f"**System Health Nominal:** Engine #{unit_number} is operating normally with a stable RUL of **{int(predicted_rul)} cycles** (Health: {health_score}%). No active maintenance priorities are registered at this interval."
            
    else:
        # Smart generic response based on active anomalies
        if risk_level != "Low Risk" or predicted_rul < 60:
            if anomalies:
                anoms_labels = [a["label"] for a in anomalies]
                return f"**Active Wear Warning:** Engine #{unit_number} is currently classified as **{risk_level}** with **{int(predicted_rul)} cycles** remaining. Active sensor drifts detected on: `{', '.join(anoms_labels)}`. Immediate maintenance action is recommended in the What-If Sandbox."
            else:
                return f"**Active Wear Warning:** Engine #{unit_number} is currently classified as **{risk_level}** with **{int(predicted_rul)} cycles** remaining. Borescope inspection is recommended to check for internal seals leakages."
        else:
            if anomalies:
                anoms_labels = [a["label"] for a in anomalies]
                return f"**Telemetry Advisory:** Engine #{unit_number} is at cycle {cycle} ({risk_level}). Sensor drift detected on: `{', '.join(anoms_labels)}`. RUL is stable at {int(predicted_rul)} cycles."
            else:
                return f"**System Normal:** Engine #{unit_number} is operating normally on cycle {cycle} with a stable predicted Remaining Useful Life of {int(predicted_rul)} cycles. No active anomalies detected."
