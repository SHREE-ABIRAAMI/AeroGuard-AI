import os
import pickle
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE = os.path.join(MODELS_DIR, "engine_model.pkl")

# NASA CMAPSS details
COLUMN_NAMES = [
    "unit_number", "time_in_cycles", "op_setting_1", "op_setting_2", "op_setting_3",
    "sensor_1", "sensor_2", "sensor_3", "sensor_4", "sensor_5", "sensor_6", "sensor_7",
    "sensor_8", "sensor_9", "sensor_10", "sensor_11", "sensor_12", "sensor_13", "sensor_14",
    "sensor_15", "sensor_16", "sensor_17", "sensor_18", "sensor_19", "sensor_20", "sensor_21"
]

ACTIVE_SENSORS = [
    "sensor_2", "sensor_3", "sensor_4", "sensor_7", "sensor_8", "sensor_11",
    "sensor_12", "sensor_13", "sensor_14", "sensor_15", "sensor_17", "sensor_20", "sensor_21"
]

SENSOR_LABELS = {
    "sensor_2": "T24 LPC Temp (R)",
    "sensor_3": "T30 HPC Temp (R)",
    "sensor_4": "T50 LPT Temp (R)",
    "sensor_7": "P30 HPC Pressure (psia)",
    "sensor_8": "Nf Physical Fan Speed (rpm)",
    "sensor_11": "Ps30 HPC Outlet Static Press (psia)",
    "sensor_12": "phi Fuel ratio to Ps30 (pps/psi)",
    "sensor_13": "NRf Corrected Fan Speed (rpm)",
    "sensor_14": "NRc Corrected Core Speed (rpm)",
    "sensor_15": "BPR Bypass Ratio",
    "sensor_17": "htBleed Bleed Enthalpy",
    "sensor_20": "W31 HPT Coolant Bleed (lbm/s)",
    "sensor_21": "W32 LPT Coolant Bleed (lbm/s)"
}

# Baseline nominal values at Cycle 1 for FD001
SENSOR_BASELINES = {
    "sensor_2": 641.8,   "sensor_3": 1589.0,  "sensor_4": 1400.0,
    "sensor_7": 554.0,   "sensor_8": 2388.0,  "sensor_11": 47.4,
    "sensor_12": 521.6,  "sensor_13": 2388.0, "sensor_14": 8138.0,
    "sensor_15": 8.4,    "sensor_17": 392.0,  "sensor_20": 39.0,
    "sensor_21": 23.4
}

# Directions where drift signifies degradation
# True if increasing indicates wear, False if decreasing indicates wear
DEGRADATION_DIRECTIONS = {
    "sensor_2": True,   "sensor_3": True,   "sensor_4": True,
    "sensor_7": False,  "sensor_8": True,   "sensor_11": True,
    "sensor_12": False, "sensor_13": True,  "sensor_14": True,
    "sensor_15": True,  "sensor_17": True,  "sensor_20": False,
    "sensor_21": False
}

def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

def copy_or_load_dataset():
    ensure_directories()
    
    train_path = os.path.join(DATA_DIR, "train_FD001.txt")
    test_path = os.path.join(DATA_DIR, "test_FD001.txt")
    rul_path = os.path.join(DATA_DIR, "RUL_FD001.txt")
    
    # Check if files already exist in our workspace data folder
    if not (os.path.exists(train_path) and os.path.exists(test_path) and os.path.exists(rul_path)):
        # Try copying from existing backend/data/ folder if available
        backend_data_dir = os.path.join(BASE_DIR, "backend", "data")
        if os.path.exists(backend_data_dir):
            import shutil
            for f in ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt"]:
                src = os.path.join(backend_data_dir, f)
                dst = os.path.join(DATA_DIR, f)
                if os.path.exists(src):
                    shutil.copy(src, dst)
                    print(f"Copied {f} to {DATA_DIR}")
    
    # Read files
    if os.path.exists(train_path) and os.path.exists(test_path) and os.path.exists(rul_path):
        train_df = pd.read_csv(train_path, sep=r"\s+", header=None, names=COLUMN_NAMES)
        test_df = pd.read_csv(test_path, sep=r"\s+", header=None, names=COLUMN_NAMES)
        rul_df = pd.read_csv(rul_path, sep=r"\s+", header=None, names=["RUL"])
        return train_df, test_df, rul_df
    else:
        raise FileNotFoundError("NASA CMAPSS Dataset files not found. Run dataset downloader or make sure they exist in the root data folder.")

def engineer_features(df, window_size=20):
    """
    Computes rolling mean, rolling standard deviation, drift, rolling max, rolling min,
    exponential moving average (EMA), and rolling median for active sensors.
    """
    df = df.sort_values(by=["unit_number", "time_in_cycles"])
    features_df = df.copy()
    
    for col in ACTIVE_SENSORS:
        # Rolling Mean
        features_df[f"{col}_roll_mean"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).mean()
        )
        # Rolling Std
        features_df[f"{col}_roll_std"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).std().fillna(0)
        )
        # Drift from first cycle
        features_df[f"{col}_drift"] = df.groupby("unit_number")[col].transform(
            lambda x: x - x.iloc[0]
        )
        # Rolling Max
        features_df[f"{col}_roll_max"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).max()
        )
        # Rolling Min
        features_df[f"{col}_roll_min"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).min()
        )
        # Exponential Moving Average (EMA)
        features_df[f"{col}_ema"] = df.groupby("unit_number")[col].transform(
            lambda x: x.ewm(span=window_size, adjust=False).mean()
        )
        # Rolling Median
        features_df[f"{col}_median"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).median()
        )
        
    return features_df

def train_model():
    print("Training XGBoost Regressor model...")
    train_df, test_df, rul_df = copy_or_load_dataset()
    
    # Piecewise-linear target RUL capping at 125 (for optimal convergence & physical accuracy)
    max_cycles = train_df.groupby("unit_number")["time_in_cycles"].transform("max")
    train_df["true_rul"] = max_cycles - train_df["time_in_cycles"]
    train_df["target_rul"] = train_df["true_rul"].clip(upper=125)
    
    feat_df = engineer_features(train_df)
    
    exclude_cols = ["unit_number", "time_in_cycles", "true_rul", "target_rul"]
    feature_cols = [col for col in feat_df.columns if col not in exclude_cols]
    
    X_train = feat_df[feature_cols]
    y_train = feat_df["target_rul"]
    
    # Prepare test data (only last cycle of each unit)
    test_feat_df = engineer_features(test_df)
    test_last_df = test_feat_df.groupby("unit_number").last().reset_index()
    
    X_test = test_last_df[feature_cols]
    y_test = np.clip(rul_df["RUL"].values, 0, 125)
    
    model = XGBRegressor(
        n_estimators=220,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        random_state=42,
        objective="reg:squarederror"
    )
    model.fit(X_train, y_train)
    
    y_pred = np.clip(model.predict(X_test), 0, None)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"XGBoost Model training completed. Test RUL RMSE: {rmse:.3f} cycles")
    
    importances = dict(zip(feature_cols, model.feature_importances_.astype(float)))
    sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    
    metadata = {
        "model": model,
        "feature_cols": feature_cols,
        "active_sensors": ACTIVE_SENSORS,
        "feature_importances": sorted_importances,
        "rmse": rmse
    }
    
    ensure_directories()
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(metadata, f)
        
    print(f"Model saved to {MODEL_FILE}")
    return metadata

def load_model():
    if not os.path.exists(MODEL_FILE):
        return train_model()
        
    with open(MODEL_FILE, "rb") as f:
        return pickle.load(f)

# Global model cache
MODEL_CACHE = None

def get_model():
    global MODEL_CACHE
    if MODEL_CACHE is None:
        MODEL_CACHE = load_model()
    return MODEL_CACHE

def predict_rul(features_df, feature_cols):
    """
    Predicts Remaining Useful Life for a given engineered features row.
    """
    model_meta = get_model()
    model = model_meta["model"]
    X = features_df[feature_cols]
    pred = model.predict(X)[0]
    return float(np.clip(pred, 0, None))

def calculate_confidence(predicted_rul):
    """
    Confidence score calculation based on predicted RUL.
    Close to failure results in high prediction confidence (as telemetry signals grow stronger),
    whereas stable early operation has higher uncertainty but is capped at normal operational confidence.
    """
    if predicted_rul <= 20:
        return 98.0  # High confidence near failure due to stark degradation signature
    elif predicted_rul <= 40:
        return 92.0
    elif predicted_rul <= 80:
        return 85.0
    else:
        return 78.0  # Slightly lower confidence when the engine is running completely normally

def calculate_health_score(predicted_rul):
    """
    Health Score from 0 to 100 based on predicted RUL relative to typical degradation window.
    """
    # Max RUL is capped at 125 in model training, so 125 represents 100% health
    score = (predicted_rul / 125.0) * 100.0
    return float(np.clip(score, 0.0, 100.0))

def classify_risk(predicted_rul):
    """
    Classify risk level according to prediction thresholds.
    """
    if predicted_rul > 80:
        return "Low Risk", "green"
    elif predicted_rul > 40:
        return "Medium Risk", "yellow"
    elif predicted_rul > 20:
        return "High Risk", "orange"
    else:
        return "Critical", "red"

def parse_sensor_anomalies(sensor_values, baseline_values):
    """
    Analyzes which sensors show significant drift compared to baseline.
    """
    anomalies = []
    for s in ACTIVE_SENSORS:
        val = sensor_values.get(s)
        base = baseline_values.get(s, SENSOR_BASELINES[s])
        if val is None:
            continue
            
        diff_pct = (val - base) / base if base != 0 else 0
        is_increasing = DEGRADATION_DIRECTIONS[s]
        
        # Flag anomalies where they drift in the wear direction by > 1.5%
        is_anomalous = False
        if is_increasing and diff_pct > 0.015:
            is_anomalous = True
        elif not is_increasing and diff_pct < -0.015:
            is_anomalous = True
            
        if is_anomalous:
            anomalies.append({
                "sensor": s,
                "label": SENSOR_LABELS[s],
                "baseline": round(base, 2),
                "current": round(val, 2),
                "deviation_pct": round(diff_pct * 100, 1),
                "direction": "UP" if diff_pct > 0 else "DOWN"
            })
    return anomalies
