import os
import urllib.request
import pandas as pd
import numpy as np

# Column names matching the NASA CMAPSS format
COLUMN_NAMES = [
    "unit_number", "time_in_cycles", "op_setting_1", "op_setting_2", "op_setting_3",
    "sensor_1", "sensor_2", "sensor_3", "sensor_4", "sensor_5", "sensor_6", "sensor_7",
    "sensor_8", "sensor_9", "sensor_10", "sensor_11", "sensor_12", "sensor_13", "sensor_14",
    "sensor_15", "sensor_16", "sensor_17", "sensor_18", "sensor_19", "sensor_20", "sensor_21"
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TRAIN_PATH = os.path.join(DATA_DIR, "train_FD001.txt")
TEST_PATH = os.path.join(DATA_DIR, "test_FD001.txt")
RUL_PATH = os.path.join(DATA_DIR, "RUL_FD001.txt")

# CMAPSS download links (using a reliable raw GitHub repository archive)
CMAPSS_URLS = {
    "train_FD001.txt": "https://raw.githubusercontent.com/MSD-Group/CMAPSS/master/CMAPSS/train_FD001.txt",
    "test_FD001.txt": "https://raw.githubusercontent.com/MSD-Group/CMAPSS/master/CMAPSS/test_FD001.txt",
    "RUL_FD001.txt": "https://raw.githubusercontent.com/MSD-Group/CMAPSS/master/CMAPSS/RUL_FD001.txt"
}

def ensure_data_directory():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def download_cmapss_data():
    ensure_data_directory()
    print("Attempting to download NASA CMAPSS dataset...")
    for filename, url in CMAPSS_URLS.items():
        dest_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(dest_path):
            try:
                print(f"Downloading {filename} from {url}...")
                urllib.request.urlretrieve(url, dest_path)
                print(f"Successfully downloaded {filename}.")
            except Exception as e:
                print(f"Failed to download {filename} due to: {e}. Falling back to synthetic generation.")
                return False
    return True

def generate_synthetic_engine_data(unit_number, max_cycles=None):
    """
    Generates realistic, physically motivated CMAPSS-like telemetry data for a single engine.
    Degradation is simulated using exponential and linear trends with random noise.
    """
    if max_cycles is None:
        max_cycles = np.random.randint(130, 362)
    
    # Initialize basic settings
    op_setting_1 = np.random.normal(0.002, 0.001, max_cycles)
    op_setting_2 = np.random.normal(0.0002, 0.0001, max_cycles)
    op_setting_3 = np.ones(max_cycles) * 100.0
    
    # Create cycles list
    cycles = np.arange(1, max_cycles + 1)
    
    # Standard baseline values for 21 sensors
    baselines = {
        1: 518.67,  2: 641.8,   3: 1589.0,  4: 1400.0,  5: 14.62,
        6: 21.61,   7: 554.0,   8: 2388.0,  9: 9046.0,  10: 1.3,
        11: 47.4,   12: 521.6,  13: 2388.0, 14: 8138.0, 15: 8.4,
        16: 0.03,   17: 392.0,  18: 2388.0, 19: 100.0,  20: 39.0,
        21: 23.4
    }
    
    # Define how each sensor degrades as failure approaches (exponent/rate)
    # Drift coefficient and direction
    drifts = {
        2: (0.8, 0.002),    # T24 drifts upwards
        3: (1.5, 0.003),    # T30 drifts upwards
        4: (1.2, 0.004),    # T50 drifts upwards
        7: (-0.9, -0.003),  # P30 drifts downwards
        8: (0.7, 0.0015),   # Nf drifts upwards
        11: (1.1, 0.0018),  # Ps30 drifts upwards
        12: (-0.8, -0.0012),# phi drifts downwards
        13: (0.6, 0.001),   # NRf drifts upwards
        14: (1.0, 0.0025),  # NRc drifts upwards
        15: (0.9, 0.0015),  # BPR drifts upwards
        17: (1.2, 0.003),   # htBleed drifts upwards
        20: (-0.7, -0.002), # W31 drifts downwards
        21: (-0.8, -0.002)  # W32 drifts downwards
    }
    
    data = {
        "unit_number": np.ones(max_cycles, dtype=int) * unit_number,
        "time_in_cycles": cycles,
        "op_setting_1": op_setting_1,
        "op_setting_2": op_setting_2,
        "op_setting_3": op_setting_3
    }
    
    for s_idx in range(1, 22):
        base = baselines[s_idx]
        col_name = f"sensor_{s_idx}"
        
        # Check if sensor is active or constant
        if s_idx in drifts:
            power, rate = drifts[s_idx]
            # Exponential degradation curve: base + rate * (cycle^power) + noise
            # Noise also increases as degradation worsens
            t = cycles / max_cycles
            drift_val = rate * (cycles ** power)
            noise_std = abs(base * 0.001) * (1 + 2 * t)
            noise = np.random.normal(0, noise_std, max_cycles)
            data[col_name] = base + drift_val + noise
        else:
            # Constant sensor with minor noise
            noise = np.random.normal(0, base * 0.0005, max_cycles)
            data[col_name] = base + noise
            
    return pd.DataFrame(data)

def generate_synthetic_dataset(num_train=100, num_test=100):
    ensure_data_directory()
    print(f"Generating synthetic NASA CMAPSS dataset ({num_train} train, {num_test} test)...")
    
    # Generate training data
    train_dfs = []
    for i in range(1, num_train + 1):
        train_dfs.append(generate_synthetic_engine_data(i))
    train_df = pd.concat(train_dfs, ignore_index=True)
    
    # Save training file
    train_df.to_csv(TRAIN_PATH, sep=" ", header=False, index=False)
    
    # Generate test data (engines cut off before failure) and their actual RUL
    test_dfs = []
    ruls = []
    for i in range(1, num_test + 1):
        total_lifespan = np.random.randint(130, 362)
        cutoff = np.random.randint(30, total_lifespan - 10)
        
        # Generate full lifespan data, then select up to cutoff cycle
        full_data = generate_synthetic_engine_data(i, max_cycles=total_lifespan)
        cutoff_data = full_data[full_data["time_in_cycles"] <= cutoff]
        test_dfs.append(cutoff_data)
        
        # The remaining cycles is the true RUL
        rul = total_lifespan - cutoff
        ruls.append(rul)
        
    test_df = pd.concat(test_dfs, ignore_index=True)
    test_df.to_csv(TEST_PATH, sep=" ", header=False, index=False)
    
    # Save RUL ground truth
    pd.DataFrame(ruls).to_csv(RUL_PATH, sep=" ", header=False, index=False)
    
    print("Synthetic dataset generation complete.")

def load_dataset():
    """
    Ensures data exists (downloads or synthesizes) and loads the training and testing files.
    """
    ensure_data_directory()
    
    # Try downloading. If fails, check if files exist, if not generate them.
    download_success = download_cmapss_data()
    
    files_exist = (
        os.path.exists(TRAIN_PATH) and
        os.path.exists(TEST_PATH) and
        os.path.exists(RUL_PATH)
    )
    
    if not download_success and not files_exist:
        generate_synthetic_dataset()
        
    # Read the text files into pandas dataframes
    train_df = pd.read_csv(TRAIN_PATH, sep=r"\s+", header=None, names=COLUMN_NAMES)
    test_df = pd.read_csv(TEST_PATH, sep=r"\s+", header=None, names=COLUMN_NAMES)
    rul_df = pd.read_csv(RUL_PATH, sep=r"\s+", header=None, names=["RUL"])
    
    return train_df, test_df, rul_df

if __name__ == "__main__":
    train, test, rul = load_dataset()
    print(f"Train Shape: {train.shape}")
    print(f"Test Shape: {test.shape}")
    print(f"RUL Shape: {rul.shape}")
    print(f"Loaded {len(train['unit_number'].unique())} training units.")
    print(f"Loaded {len(test['unit_number'].unique())} testing units.")
