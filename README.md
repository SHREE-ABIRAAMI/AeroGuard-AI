# AeroGuard AI – Predictive Maintenance Intelligence Platform

> Transforming Industrial Sensor Data into Intelligent Maintenance Decisions.

AeroGuard AI is an enterprise-grade decision-support platform designed for aerospace operations, industrial asset management, and airline maintenance engineering teams. Using the **NASA CMAPSS Turbofan Engine Degradation Dataset**, the platform monitors real-time telemetry, forecasts Remaining Useful Life (RUL), runs What-If servicing simulations, explains ML predictions via SHAP, and computes operational/financial business impact.

---

## 🚀 Key Features

* **SaaS Landing Page**: Sleek, dark-mode aerospace landing page featuring a product overview, value proposition, tech stack, and a "Launch Platform" call-to-action.
* **Operations Dashboard (Mission Control)**: Displays real-time aggregates (Average Health, Avg RUL, Critical Assets, Active Services due) with active line plotting and live telemetry streaming simulation.
* **SCHEMATIC Digital Twin**: SVG-based turbofan schematic illustrating low-pressure compressor (LPC), high-pressure compressor (HPC), and low-pressure turbine (LPT) stages with active risk overlays that animate (spin) in proportion to degradation.
* **Prediction Center**: Allows manual intake parameters, "Load Sample Data" presets representing real CMAPSS stages (Healthy, Warning, Critical), and CSV log file uploads.
* **Explainable AI (XAI)**: Predictions are backed by local feature attributions (SHAP) mapped to a waterfall plot, complemented by a natural language summary.
* **AI Maintenance Copilot**: Conversational diagnostic chatbot powered by Google Gemini (with an offline rule-based turbine engineering fallback) to answer queries (e.g., "Why does sensor 11 drift?").
* **Fleet Monitor Grid**: Tabular asset display with real-time searching, risk filtering, and priority code tagging (P1-P4).

---

## 🛠️ Technology Stack

* **Frontend**: HTML5, CSS3 (Tailwind CSS v3 + Custom glassmorphism, animations), Vanilla JavaScript, Plotly.js charts.
* **Backend**: FastAPI, Python 3.12, Jinja2 Templates.
* **Machine Learning & Analytics**: XGBoost (Piecewise-linear regression model), Scikit-learn, Pandas, NumPy.
* **Explainability**: SHAP (SHAP TreeExplainer with local perturbation fallback).
* **Cognitive Agent**: Gemini LLM via `google-generativeai` (with offline keyword routing).

---

## 📐 Project Structure

```
AeroGuard-AI/
├── app/
│   ├── main.py                 # FastAPI Application Server and API Routes
│   ├── predictor.py            # XGBoost Model Loading, Feature Engineering, and RUL Inference
│   ├── recommendation.py       # Rule-based Maintenance Recommendation Engine
│   ├── business.py             # Business Impact Calculator (Downtime, Savings, Efficiency)
│   ├── explainability.py       # SHAP and Feature Attribution Generator
│   ├── copilot.py              # LLM Maintenance Copilot (Gemini API and fallback)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       # Custom Glassmorphic Styles, Keyframes, and Fonts
│   │   └── js/
│   │       └── app.js          # SPA Controller, Interactivity, Charting, and API Integrations
│   └── templates/
│       └── index.html          # Main HTML Dashboard Layout and SaaS Landing Page
├── data/                       # Contains train_FD001.txt, test_FD001.txt, RUL_FD001.txt
├── models/                     # Holds the serialized engine_model.pkl file
├── requirements.txt            # Python dependencies (fastapi, uvicorn, jinja2, xgboost, shap, etc.)
└── README.md                   # Enterprise System Documentation
```

---

## 🔌 API Gateway Endpoints

* **`GET /`**: Serves the Single Page Application dashboard.
* **`GET /api/dashboard`**: Aggregate status statistics for the simulated fleet.
* **`GET /api/analytics`**: Plotly distribution vectors (RUL histogram, risks, timeline indices).
* **`GET /api/fleet`**: Active fleet table data.
* **`GET /api/model-info`**: ML model parameters, test RMSE, and global feature importances.
* **`POST /api/predict`**: Manual RUL inference from JSON sensor body.
* **`POST /api/upload`**: Upload CSV file for batch log evaluation.
* **`POST /api/copilot`**: Cognitive chatbot diagnostics queries.
* **`POST /api/simulate`**: What-If maintenance applicator (compressor wash, bearing swap, core overhaul).
* **`POST /api/tick`**: Advances active simulated time by 1 operating cycle.
* **`POST /api/reset`**: Resets simulated cycles and wear factors to default baselines.

---

## ⚙️ Setup & Installation

### 1. Pre-requisites
* Python 3.10+ (tested on Python 3.12.3)
* Google Gemini API Key (Optional, for conversational AI chat): Set the environment variable `GEMINI_API_KEY`.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Training the Model
Upon first launch, the server will automatically download the NASA CMAPSS dataset text files (if missing), copy them into `data/`, run rolling feature engineering, and train the XGBoost regressor, saving the model metadata to `models/engine_model.pkl`. 

To train it manually ahead of time:
```bash
python -c "import sys; sys.path.append('app'); import predictor; predictor.train_model()"
```

### 4. Running the Application
```bash
python app/main.py
```
Open your browser and navigate to `http://127.0.0.1:8000`.

---

## 📈 Verification Suite
To run the automated endpoint validation tests:
```bash
python -m unittest scratch/verify_app.py
```
*(Tests verify dashboard loading, simulated fleet states, manual prediction models, and Copilot fallback responses)*.
