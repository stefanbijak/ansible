# 📦 Ansible Host Inventory Collector

This project provides a simple Ansible playbook that collects basic host information (IP addresses, uptime, and group membership) and stores it locally in structured JSON files.

---

## 🚀 Features

- Collects IPv4 addresses from each host  
- Retrieves system uptime  
- Captures Ansible inventory group membership  
- Saves data as formatted JSON per host  
- Runs without requiring Python on remote hosts (`raw` module)  
- Uses **dynamic inventory from a database via Python** (external script)

---

## 📁 Project Structure

```
.
├── playbook.yml
└── output/
    ├── host1.json
    ├── host2.json
    └── ...
```

> Dynamic inventory script (`inventory.py`) is maintained separately.

---

## ⚙️ Requirements

- Ansible installed on control node  
- Python environment for dynamic inventory script  
- Database (MySQL/PostgreSQL/SQLite)  
- SSH access to target hosts  

---

## 🧠 Inventory Source (Database)

This project does **not use static `hosts.ini`**.

Inventory is dynamically generated using a custom Python script that:

- Connects to a database  
- Reads host data (hostname, IP, credentials, groups)  
- Outputs Ansible-compatible JSON  

---

## ▶️ Usage

Run the playbook with your external dynamic inventory script:

```bash
ansible-playbook -i /path/to/inventory.py playbook.yml
```

---

## 📊 Example Output

```json
{
  "hostname": "server1",
  "groups": ["web", "production"],
  "ips": ["192.168.1.10", "10.0.0.5"],
  "uptime": "10:23"
}
```

---

## 🧠 How It Works

### 1. Create Output Directory
Ensures a local folder (`./output`) exists

### 2. Collect IP Addresses
```bash
ip -o -4 addr show up | awk '{print $4}' | cut -d/ -f1 | grep -v "127.0.0.1"
```

### 3. Get Uptime
```bash
uptime | awk {'print $3'}
```

### 4. Save Data
Creates:
```
output/<hostname>.json
```

---

## ⚠️ Notes

- Uses `raw` module → no Python required on remote hosts  
- Dynamic inventory requires Python only on control node  
- Uptime parsing may vary depending on OS  
- Inventory structure depends on external script implementation  

---

## 🔧 Possible Improvements

- Store collected data back into database  
- Add CPU, RAM, disk metrics  
- Build API layer (FastAPI)  
- Dashboard visualization (Grafana / Streamlit)  
- Scheduling via cron or CI/CD  

---

## 📌 Use Cases

- Database-driven infrastructure inventory  
- Automation pipelines  
- IPTV/server fleet visibility  
- Source-of-truth synchronization  

---

## 🧑‍💻 Author

Automation workflow using **Ansible + dynamic inventory + database integration**
