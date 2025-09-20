# 📡 Smart Network Monitor

A lightweight real-time **network monitoring system** with:
- 🌍 GeoIP + ASN/Organization enrichment
- 📊 Interactive Streamlit dashboard
- 🚨 Anomaly detection (Isolation Forest)
- 🏠 LAN ↔ Public & Public ↔ Public traffic visualization
- 🔍 Filters (protocol, country, IP, ASN/org)
- 📄 SQLite backend for captured packets

---

## 🚀 Features
- **Live packet capture** via `pyshark` + `tshark`
- **GeoIP Enrichment** using MaxMind GeoLite2 (City + ASN)
- **Dashboard** built with Streamlit
- **Alerts** for suspicious traffic spikes
- **Custom LAN Mapping** (choose how private IPs appear on map)

---

## 🛠️ Installation

### 1. Clone the repo
```bash
git clone https://github.com/<YOUR_USERNAME>/smart-network-monitor.git
cd smart-network-monitor

```
### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### Structure
``` bash
smart-network-monitor/
│── snm_capture.py       # Packet capture + enrichment
│── snm_dashboard.py     # Streamlit dashboard
│── requirements.txt     # Dependencies
│── packets.db           # SQLite DB (auto-generated)
│── README.md            # Project documentation
│── .gitignore           # Ignore db, venv, cache

```

Install Wireshark/Tshark
```bash
tshark -v
