# 🚚 DeliveryPulse – Delivery SLA Analytics Dashboard

> **An intelligent analytics platform that helps food delivery companies identify, analyze, and predict SLA (Service Level Agreement) violations using data analytics and machine learning.**

---

## 📌 Overview

DeliveryPulse is a data analytics dashboard designed to help food delivery companies monitor operational performance and reduce delivery delays.

Food delivery companies collect data from multiple systems such as delivery logs, rider assignments, customer complaints, refund records, and order details. Since this information exists in disconnected systems, operations teams struggle to identify why deliveries are delayed and which factors contribute to SLA violations.

DeliveryPulse consolidates these datasets into a single interactive dashboard, enabling users to monitor delivery performance, identify bottlenecks, perform root cause analysis, and predict future SLA violations.

---

## 🚨 Problem Statement

A fast-growing food delivery company stores delivery logs, rider assignment history, customer complaints, refund records, and order details across disconnected systems, but operations teams still cannot identify which delivery patterns consistently lead to SLA violations during peak hours.

As a result:

- Operations teams cannot identify recurring SLA violations.
- Rider performance is difficult to evaluate.
- Peak-hour bottlenecks remain hidden.
- Customer complaints and refunds cannot be linked to operational issues.
- Manual reporting consumes significant time.

DeliveryPulse solves this problem by providing a centralized analytics platform for operational monitoring and predictive insights.

---

## 🤝 Team Workflow

This repository follows a simple GitHub Flow process so the team can work in parallel without breaking the shared codebase.

- Main stays releasable and only receives reviewed merges.
- Each task starts on a feature branch named with the issue number, such as `feature/12-delay-analysis`.
- Every change is tracked in a GitHub issue before code is written.
- Pull requests must reference the issue and include a short summary, testing notes, and review approval.
- Commit messages use the conventional format, such as `feat: add delay hotspot chart` or `fix: handle missing delivery times`.

See [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for the full working agreement.

---

# 🎯 Objectives

- Improve SLA compliance
- Reduce delayed deliveries
- Analyze rider performance
- Identify peak-hour bottlenecks
- Detect operational root causes
- Predict future SLA violations
- Support data-driven decision making

---

# ✨ Features

## 📊 Dashboard Overview

- Total Orders
- SLA Compliance %
- Late Deliveries
- Average Delivery Time
- Refund Amount
- Delivery Trends
- Delay Hotspots
- Critical Alerts

---

## ⚠️ SLA Violation Analysis

- SLA Violation Rate
- Delay Trends
- Violation Reasons
- Zone-wise Analysis
- Rider-wise Analysis
- Delayed Orders Table

---

## 🔍 Root Cause Analysis

- Traffic Delays
- Restaurant Delays
- Rider Assignment Delays
- Peak Hour Congestion
- Distance vs Delay
- Delay Frequency by Zone
- Root Cause Summary

---

## 🤖 Predictive Analytics

- SLA Risk Prediction
- High-Risk Orders
- Demand Forecasting
- Risk Heatmap
- AI Recommendations
- Rider Allocation Suggestions

---

## 📄 Reports

- Export CSV
- Weekly Reports
- Monthly Reports
- Operational Insights

---

# 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Core Programming Language |
| Pandas | Data Cleaning & Analysis |
| NumPy | Numerical Computation |
| SQL | Data Storage & Queries |
| Scikit-learn | Machine Learning Models |
| Streamlit | Interactive Dashboard |
| GitHub Actions | CI/CD Automation |

---

# 📂 Project Structure

```text
DeliveryPulse/
│
├── data/
│   ├── delivery_logs.csv
│   ├── rider_assignments.csv
│   ├── complaints.csv
│   ├── refunds.csv
│   └── orders.csv
│
├── notebooks/
│
├── models/
│   ├── prediction_model.pkl
│   └── preprocessing.pkl
│
├── dashboard/
│   ├── app.py
│   ├── pages/
│   ├── components/
│   └── assets/
│
├── src/
│   ├── preprocessing.py
│   ├── analytics.py
│   ├── prediction.py
│   └── visualization.py
│
├── tests/
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# 📊 Dataset

The project integrates multiple datasets.

| Dataset | Description |
|----------|-------------|
| Delivery Logs | Delivery time, SLA status, delivery duration |
| Rider Assignments | Rider allocation details |
| Customer Complaints | Complaint information |
| Refund Records | Refund reasons and amount |
| Order Details | Restaurant, distance, zone |

---

# 🔄 Workflow

```text
Raw Delivery Data
        │
        ▼
Data Cleaning
(Pandas)
        │
        ▼
Data Integration
(SQL)
        │
        ▼
Feature Engineering
        │
        ▼
Analytics Engine
        │
        ▼
Machine Learning
        │
        ▼
Streamlit Dashboard
        │
        ▼
Operational Insights
```

---

# 📈 Dashboard Modules

### Dashboard Overview

- Delivery KPIs
- Delivery Trends
- Delay Hotspots
- Rider Performance
- Alerts

---

### SLA Analysis

- Violation Trends
- Zone Analysis
- Delay Reasons
- Refund Impact

---

### Root Cause Analysis

- Traffic Delays
- Rider Delays
- Restaurant Delays
- Peak Hour Analysis
- Distance Analysis

---

### Predictions

- Future SLA Risk
- High Risk Zones
- Rider Recommendations
- AI Insights

---

### Reports

- Export Analytics
- Weekly Reports
- Monthly Reports

---

# 🤖 Machine Learning

The prediction module analyzes historical delivery data to estimate:

- Future SLA violations
- High-risk delivery zones
- Peak-hour congestion
- Delay probability
- Operational recommendations

---

# 📊 KPIs

- Total Orders
- SLA Compliance
- Late Deliveries
- Average Delivery Time
- Refund Amount
- Rider Performance
- Delay Frequency
- Complaint Rate

---

# 🚀 Future Scope

- Live GPS Tracking
- Real-Time Analytics
- Kafka Streaming
- Dynamic Rider Allocation
- AI Chat Assistant
- Route Optimization
- Role-Based Access Control
- Cloud Deployment

---

# 👥 Team

| Name | Role |
|------|------|
| Ananya | Backend Developer |
| Deepak | Data Analyst |
| Kishore | Operations & Analytics |

---

# 🏆 Expected Outcomes

- Faster SLA monitoring
- Reduced delivery delays
- Improved rider performance
- Lower refund costs
- Better operational visibility
- Data-driven decision making

---

# 📸 UI Preview

The dashboard consists of:

- Dashboard Overview
- SLA Violation Analysis
- Root Cause Analysis
- Prediction Dashboard
- Reports

---

## ⭐ DeliveryPulse

**"Monitor. Analyze. Predict. Improve."**
