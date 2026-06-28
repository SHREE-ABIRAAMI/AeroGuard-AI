<<<<<<< HEAD
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
=======
# AeroGuard AI - Predictive Maintenance Intelligence Platform

> Predict Failures Before They Happen. Optimize Maintenance Before It Costs Millions.

AeroGuard AI is an AI-powered Predictive Maintenance Intelligence Platform designed to forecast equipment failures before they occur using machine sensor data. The system leverages machine learning, explainable AI, and intelligent maintenance recommendations to help organizations reduce downtime, optimize maintenance schedules, and improve operational efficiency.

This project is built using the NASA Turbofan Jet Engine Dataset and focuses on predicting the Remaining Useful Life (RUL) of machinery to enable proactive maintenance decisions.

---

## Problem Statement

Industrial equipment failures often lead to:

* Unplanned downtime
* Increased maintenance costs
* Production losses
* Reduced operational efficiency
* Safety and reliability concerns

Traditional maintenance approaches are either:

### Reactive Maintenance

Maintenance is performed only after a failure occurs.

### Preventive Maintenance

Maintenance is performed at fixed intervals regardless of the machine's actual condition.

Both approaches can result in unnecessary costs and inefficient resource utilization.

The objective of this project is to use machinery sensor data to predict when maintenance is required before failures occur, thereby optimizing industrial operations and reducing operational risks.

---

## Project Objective

The primary goal of AeroGuard AI is to transform raw sensor readings into actionable maintenance intelligence.

Instead of simply predicting whether a machine will fail, the system estimates:

* Remaining Useful Life (RUL)
* Machine Health Status
* Failure Risk Level
* Maintenance Priority
* Recommended Maintenance Actions

This enables maintenance teams to make informed, data-driven decisions before critical failures happen.

---

## Proposed Solution

AeroGuard AI follows a predictive maintenance pipeline that converts sensor data into maintenance recommendations.

### Workflow

Sensor Data

↓

Data Cleaning & Preprocessing

↓

Feature Engineering

↓

XGBoost Prediction Model

↓

Remaining Useful Life (RUL) Prediction

↓

Risk Assessment Engine

↓

Maintenance Recommendation Engine

↓

Explainable AI Insights

↓

Interactive Monitoring Dashboard

---

## Key Features

### Remaining Useful Life (RUL) Prediction

Predicts the estimated number of operational cycles remaining before equipment failure.

### Health Score Generation

Converts technical predictions into an intuitive health score for easy monitoring.

Example:

* Healthy
* Warning
* High Risk
* Critical

### Risk Assessment Engine

Classifies equipment based on predicted failure risk.

### Maintenance Recommendation Engine

Provides actionable maintenance suggestions based on machine condition and risk level.

### Fleet Monitoring Dashboard

Allows monitoring of multiple machines through a centralized interface.

### Explainable AI

Uses SHAP (SHapley Additive Explanations) to explain model predictions and identify the most influential sensor readings.

### AI Maintenance Copilot

Generates human-readable explanations for maintenance decisions using Large Language Models (LLMs).

### Business Impact Analysis

Provides insights into:

* Potential downtime reduction
* Maintenance optimization opportunities
* Fleet availability improvements
* Operational efficiency gains

---

## Why AeroGuard AI?

Most predictive maintenance solutions focus only on model predictions.

AeroGuard AI goes beyond prediction by converting machine learning outputs into practical maintenance decisions that engineers and operations teams can directly act upon.

The platform emphasizes:

* Predictive Intelligence
* Explainability
* Operational Decision Support
* Business Impact
* Industrial Applicability

---

## Dataset

### NASA Turbofan Jet Engine Dataset (CMAPSS)

The project utilizes the NASA Commercial Modular Aero-Propulsion System Simulation (CMAPSS) dataset.

The dataset contains:

* Engine operational cycles
* Operational settings
* Multiple sensor measurements
* Engine degradation behavior over time

This dataset is widely used for Remaining Useful Life (RUL) prediction and predictive maintenance research.

---

## Technology Stack

### Programming Language

* Python

### Data Processing

* Pandas
* NumPy

### Machine Learning

* Scikit-Learn
* XGBoost

### Explainable AI

* SHAP

### Backend Development

* FastAPI

### Frontend Development

* HTML
* Tailwind CSS
* JavaScript

### Data Visualization

* Plotly

### AI Assistant

* Groq API
* Llama Models

### Version Control

* Git
* GitHub

### Deployment

* Render

---

## System Architecture

NASA Turbofan Dataset

↓

Data Preprocessing

↓

Feature Engineering

↓

XGBoost RUL Prediction Model

↓

Health & Risk Assessment

↓

Maintenance Recommendation Engine

↓

SHAP Explainability Layer

↓

AI Maintenance Copilot

↓

AeroGuard AI Dashboard

---

## Expected Outputs

For each machine, AeroGuard AI will generate:

### Remaining Useful Life

Example:

RUL = 42 Cycles

### Health Score

Example:

Health Score = 87 / 100

### Risk Category

* Low Risk
* Warning
* High Risk
* Critical

### Maintenance Priority

* P1 – Immediate Attention
* P2 – Schedule Soon
* P3 – Monitor Regularly

### Maintenance Recommendation

Example:

"Inspect critical engine components within the next 10 operational cycles to prevent potential failure."

---

## Business Impact

AeroGuard AI aims to help organizations:

* Reduce unexpected equipment failures
* Minimize operational downtime
* Improve maintenance planning
* Increase asset utilization
* Optimize maintenance costs
* Support proactive decision-making

---

## Project Roadmap

### Phase 1

* Dataset Collection
* Repository Setup
* Project Planning

### Phase 2

* Data Analysis
* Data Cleaning
* Feature Engineering

### Phase 3

* XGBoost Model Development
* Remaining Useful Life Prediction

### Phase 4

* Explainable AI Integration
* SHAP Analysis

### Phase 5

* Dashboard Development
* Risk Monitoring System

### Phase 6

* AI Maintenance Copilot
* Business Impact Analysis

### Phase 7

* Deployment
* Documentation
* Final Presentation

---

## Future Enhancements

* Real-Time Sensor Monitoring
* IoT Device Integration
* Multi-Factory Fleet Monitoring
* Automated Maintenance Scheduling
* Advanced Failure Simulation
* Mobile Monitoring Application

---

## Repository Structure

```text
AeroGuard-AI/
│
├── data/
├── notebooks/
├── models/
├── app/
├── static/
├── templates/
├── screenshots/
├── docs/
│
├── README.md
├── requirements.txt
├── architecture.png
├── .gitignore
└── LICENSE
>>>>>>> d0a566ecb61f57c6aab35af6df875ecca1a031df
```

---

<<<<<<< HEAD
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
=======
## Project Status

Current Status:

🚧 Project Initialization & Development Phase

Upcoming Milestone:

✅ Data Exploration and Predictive Modeling

---

## Author

### SHREE ABIRAAMI M

**AI/ML Engineer**

Passionate about Artificial Intelligence, Machine Learning, Predictive Analytics, and building intelligent systems that solve real-world industrial challenges.

---

## License

This project is intended for educational, research, and demonstration purposes.
>>>>>>> d0a566ecb61f57c6aab35af6df875ecca1a031df
