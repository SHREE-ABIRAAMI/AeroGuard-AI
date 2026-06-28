import os
import pickle
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error
import data_handler

# File paths for model artifacts
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(MODEL_DIR, "engine_model.pkl")

# Critical sensors showing degradation variance
ACTIVE_SENSORS = [
    "sensor_2", "sensor_3", "sensor_4", "sensor_7", "sensor_8", "sensor_11",
    "sensor_12", "sensor_13", "sensor_14", "sensor_15", "sensor_17", "sensor_20", "sensor_21"
]

def engineer_features(df, window_size=10):
    """
    Computes rolling averages and rolling standard deviations for active sensors.
    Features are grouped by engine (unit_number).
    """
    # Sort to ensure sequential computation
    df = df.sort_values(by=["unit_number", "time_in_cycles"])
    
    # Base columns
    features_df = df.copy()
    
    # Compute rolling values
    for col in ACTIVE_SENSORS:
        # Rolling Mean
        features_df[f"{col}_roll_mean"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).mean()
        )
        # Rolling Std
        features_df[f"{col}_roll_std"] = df.groupby("unit_number")[col].transform(
            lambda x: x.rolling(window_size, min_periods=1).std().fillna(0)
        )
        # Cumulative trend slope (difference from initial cycle value)
        features_df[f"{col}_drift"] = df.groupby("unit_number")[col].transform(
            lambda x: x - x.iloc[0]
        )
        
    return features_df

def prepare_training_data(train_df, window_size=10, max_rul=125):
    """
    Constructs the targets using a piecewise-linear RUL strategy. Capping RUL
    at max_rul (e.g. 125 cycles) represents the stable operational phase and
    substantially improves model learning rate and testing accuracy.
    """
    # Calculate true RUL for each row in train
    max_cycles = train_df.groupby("unit_number")["time_in_cycles"].transform("max")
    train_df["true_rul"] = max_cycles - train_df["time_in_cycles"]
    
    # Apply Piecewise-Linear RUL capping
    train_df["target_rul"] = train_df["true_rul"].clip(upper=max_rul)
    
    # Engineer features
    feat_df = engineer_features(train_df, window_size)
    
    # Columns to exclude from feature matrix
    exclude_cols = ["unit_number", "time_in_cycles", "true_rul", "target_rul"]
    feature_cols = [col for col in feat_df.columns if col not in exclude_cols]
    
    X = feat_df[feature_cols]
    y = feat_df["target_rul"]
    
    return X, y, feature_cols

def prepare_test_data(test_df, rul_df, feature_cols, window_size=10):
    """
    Prepares test engine data. For the test set, we only predict RUL at the 
    last cycle of each unit number.
    """
    feat_df = engineer_features(test_df, window_size)
    
    # Extract only the last cycle for each engine
    test_last_df = feat_df.groupby("unit_number").last().reset_index()
    
    X_test = test_last_df[feature_cols]
    y_test = np.clip(rul_df["RUL"].values, 0, 125)
    
    return X_test, y_test

def train_and_evaluate():
    # 1. Load Data
    train_df, test_df, rul_df = data_handler.load_dataset()
    
    # 2. Prepare Train
    X_train, y_train, feature_cols = prepare_training_data(train_df)
    
    # 3. Prepare Test
    X_test, y_test = prepare_test_data(test_df, rul_df, feature_cols)
    
    print(f"Training features dimensions: {X_train.shape}")
    print("Training XGBoost Regressor...")
    
    # 4. Train Model
    model = XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        objective="reg:squarederror"
    )
    model.fit(X_train, y_train)
    
    # 5. Evaluate
    y_pred = model.predict(X_test)
    # Clip predictions to prevent negative RULs
    y_pred = np.clip(y_pred, 0, None)
    
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"Model Training Complete. Test RUL RMSE: {rmse:.3f} cycles")
    
    # Calculate feature importances
    importances = dict(zip(feature_cols, model.feature_importances_.astype(float)))
    # Sort features
    sorted_importances = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    
    # 6. Save model and metadata
    metadata = {
        "model": model,
        "feature_cols": feature_cols,
        "active_sensors": ACTIVE_SENSORS,
        "feature_importances": sorted_importances,
        "rmse": rmse
    }
    
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(metadata, f)
        
    print(f"Saved trained model and metadata to {MODEL_FILE}")
    return rmse

def load_trained_model():
    if not os.path.exists(MODEL_FILE):
        print("Model file not found. Running training first...")
        train_and_evaluate()
        
    with open(MODEL_FILE, "rb") as f:
        return pickle.load(f)

if __name__ == "__main__":
    train_and_evaluate()
