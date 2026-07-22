def calculate_business_impact(predicted_rul, health_score, anomalies, risk_level):
    """
    Translates predictive telemetry (RUL and Risk Level) into key business value outcomes:
    financial savings, downtime hours prevented, operational safety, and fleet utilization.
    """
    # Baseline Constants for Aerospace Fleet Management
    COST_UNPLANNED_FAILURE = 185000.0  # Cost of emergency engine core failure in USD
    COST_PLANNED_SERVICE = 15000.0     # Cost of planned preventive repair in USD
    DOWNTIME_UNPLANNED_HOURS = 28.0    # Average aircraft grounding for unplanned engine repair
    DOWNTIME_PLANNED_HOURS = 4.0       # Average grounding for planned service
    COST_DOWNTIME_PER_HOUR = 8500.0    # Commercial downtime cost per hour in USD
    
    # 1. Initialize Default Nominal Metrics (Low Risk / Healthy)
    downtime_prevented = 0.0
    direct_savings = 0.0
    downtime_cost_saved = 0.0
    total_savings = 0.0
    safety_index = 99.8
    operational_efficiency = 98.5
    
    # 2. Compute Metrics Based on Degradation Level
    if risk_level == "Critical":
        # Unplanned failure is imminent. Acting now prevents the worst-case scenario.
        downtime_prevented = DOWNTIME_UNPLANNED_HOURS - DOWNTIME_PLANNED_HOURS # 24 hours saved
        direct_savings = COST_UNPLANNED_FAILURE - COST_PLANNED_SERVICE  # $170,000 saved on parts
        downtime_cost_saved = downtime_prevented * COST_DOWNTIME_PER_HOUR # 24 * $8500 = $204,000
        total_savings = direct_savings + downtime_cost_saved # $374,000 total saved
        
        # High risk of flight delays, safety compromises
        safety_index = max(10.0, health_score * 0.8)
        operational_efficiency = max(15.0, health_score * 0.9)
        
    elif risk_level == "High Risk":
        # Significant wear. Repair is necessary soon to avoid component damage.
        downtime_prevented = 18.0 # 18 hours of unplanned downtime avoided
        direct_savings = 90000.0   # $90,000 saved by preventing damage to surrounding rotor stages
        downtime_cost_saved = downtime_prevented * COST_DOWNTIME_PER_HOUR
        total_savings = direct_savings + downtime_cost_saved
        
        safety_index = 65.0
        operational_efficiency = 70.0
        
    elif risk_level == "Medium Risk":
        # Early-stage wear. Low chance of failure but scheduling prevents future degradation.
        downtime_prevented = 8.0 # 8 hours avoided by consolidation with routine checkups
        direct_savings = 30000.0  # Restoring thermal efficiency early saves fuel and carbon tax
        downtime_cost_saved = downtime_prevented * COST_DOWNTIME_PER_HOUR
        total_savings = direct_savings + downtime_cost_saved
        
        safety_index = 88.0
        operational_efficiency = 90.0
        
    else: # Low Risk / Healthy
        # Normal operations. Business impact is maintaining peak standard fleet parameters.
        downtime_prevented = 0.0
        direct_savings = 0.0
        total_savings = 0.0
        safety_index = 99.8
        operational_efficiency = 99.2
        
    # Check anomalies to add operational impacts
    anomalies_count = len(anomalies)
    if anomalies_count > 0:
        # Each anomaly slightly degrades fleet operational efficiency indices
        operational_efficiency -= (anomalies_count * 1.5)
        safety_index -= (anomalies_count * 0.5)
        
    return {
        "downtime_prevented_hours": round(downtime_prevented, 1),
        "maintenance_cost_savings": round(direct_savings, 2),
        "downtime_cost_savings": round(downtime_cost_saved, 2),
        "total_financial_savings": round(total_savings, 2),
        "safety_index_pct": round(max(5.0, min(100.0, safety_index)), 1),
        "operational_efficiency_pct": round(max(10.0, min(100.0, operational_efficiency)), 1),
        "fleet_availability_contribution_pct": round(health_score, 1)
    }
