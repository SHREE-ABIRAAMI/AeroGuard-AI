def generate_maintenance_recommendation(predicted_rul, health_score, anomalies):
    """
    Automated decision engine that maps RUL, health score, and specific sensor anomalies
    to concrete operational recommendations and urgency priority codes.
    """
    rec_data = {
        "priority_code": "P4",
        "priority_label": "Low",
        "action": "Continue Normal Operation",
        "estimated_window": "Nominal (> 80 cycles)",
        "details": []
    }
    
    # 1. Classify Urgency and Estimated Failure Windows
    if predicted_rul <= 20:
        rec_data["priority_code"] = "P1"
        rec_data["priority_label"] = "Critical"
        rec_data["action"] = "Immediate Maintenance Required (Ground Engine)"
        rec_data["estimated_window"] = f"CRITICAL - Failure projected within {int(predicted_rul)} cycles"
        rec_data["details"] = [
            "Severe sensor degradation signature indicating high risk of imminent breakdown.",
            "Ground aircraft/asset immediately and issue an AOG (Aircraft on Ground) maintenance ticket.",
            "Initiate hot-section rebuild and non-destructive blade shear testing."
        ]
    elif predicted_rul <= 40:
        rec_data["priority_code"] = "P2"
        rec_data["priority_label"] = "High"
        rec_data["action"] = "Schedule Core Inspection & Component Repair"
        rec_data["estimated_window"] = f"High Urgency - Window: {int(predicted_rul)} cycles"
        rec_data["details"] = [
            "Significant telemetry deviations indicating accelerated mechanical wear.",
            "Schedule borescope blade inspection and verify sealing ring tolerances.",
            "Stage main shaft bearing replacement parts in the hangar."
        ]
    elif predicted_rul <= 80:
        rec_data["priority_code"] = "P3"
        rec_data["priority_label"] = "Medium"
        rec_data["action"] = "Schedule Preventive Maintenance"
        rec_data["estimated_window"] = f"Preventive - Window: {int(predicted_rul)} cycles"
        rec_data["details"] = [
            "Sensors show early-stage degradation drift from baseline.",
            "Schedule routine engine checkout and filter replacement within next service schedule."
        ]
    else: # RUL > 80
        rec_data["priority_code"] = "P4"
        rec_data["priority_label"] = "Low"
        rec_data["action"] = "Continue Normal Operation"
        rec_data["estimated_window"] = f"Nominal - {int(predicted_rul)} cycles remaining"
        rec_data["details"] = [
            "Telemetry signals are within stable baseline parameters.",
            "No immediate servicing required.",
            "Re-evaluate at next operational cycle checkpoint."
        ]
        
    # 2. Add Sensor-Specific Recommendations for Medium & High Urgencies
    if predicted_rul <= 80:
        # Check for thermal issues (T24, T30, T50 sensors: sensor_2, sensor_3, sensor_4)
        thermal_anoms = [a for a in anomalies if a["sensor"] in ["sensor_2", "sensor_3", "sensor_4"]]
        # Check for pressure issues (P30, Ps30: sensor_7, sensor_11)
        pressure_anoms = [a for a in anomalies if a["sensor"] in ["sensor_7", "sensor_11"]]
        # Check for speed / mechanical issues (Nf, NRf, NRc: sensor_8, sensor_13, sensor_14)
        speed_anoms = [a for a in anomalies if a["sensor"] in ["sensor_8", "sensor_13", "sensor_14"]]
        
        if thermal_anoms:
            rec_data["details"].append(
                "Thermal Exhaust Profile: Core temperatures are elevated. Perform a Compressor Core Wash to clean blades and restore efficiency."
            )
            # Override recommended action if RUL is medium but thermal drift is high
            if rec_data["priority_code"] == "P3":
                rec_data["action"] = "Perform Compressor Core Wash"
                
        if pressure_anoms:
            rec_data["details"].append(
                "Pressure Deviation: Compressor outlet pressure ratios are unstable. Inspect turbine seals and bleed-air valves."
            )
            
        if speed_anoms:
            rec_data["details"].append(
                "Mechanical Friction: Rotor speeds (Nf/NRc) are displaying friction anomalies. Schedule shaft bearing replacement and lubrication check."
            )
            if rec_data["priority_code"] == "P2":
                rec_data["action"] = "Replace Main Shaft Bearings"
                
    return rec_data
