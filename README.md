# FaceTrack AI — 100% Pure Python Face Recognition & Employee Attendance System

FaceTrack AI is a production-ready, pure Python biometric employee management and attendance system built with **FastAPI**, **SQLAlchemy**, **OpenCV (YuNet + SFace)**, and **Jinja2 + Tailwind CSS (via CDN)**.

Designed specifically for clean, lightweight deployment on **Hostinger VPS** or any standard Linux/Windows server without requiring Node.js, npm, or frontend build steps.

---

## Key Features

- **100% Pure Python Monolith**: No Node.js, React, or Next.js dependencies. Fast startup and minimal RAM usage.
- **Employees-Only Focus**: Streamlined employee directory with department assignment, job positions, and biometric enrollment.
- **Animated Live Face Scanner**:
  - Glowing HUD targeting reticle & futuristic scan frame.
  - Smooth laser sweep beam and radar pulse ripples.
  - Interactive hover glow effects.
  - Built-in Web Audio chime synthesizer for instant audio confirmation.
  - Dual modes: **Check In** and **Check Out**.
- **Biometric Engine**:
  - **OpenCV YuNet**: Real-time neural face detection.
  - **OpenCV SFace**: 128-dimensional biometric embedding extraction.
  - Anti-duplicate debounce: prevents multiple check-ins within 45 seconds for the same person.
- **Analytics & Attendance Dashboard**:
  - Live metric cards: Total Employees, Present Today, Late Arrivals, Pending Face Registrations.
  - Weekly attendance trend bar chart (Chart.js).
  - Live scan activity feed.
- **Auditing & Export**:
  - Filter attendance records by date, department, status, and name.
  - One-click CSV export for payroll and HR reporting.

---
   
## Project Structure

```plaintext
facetrack-ai/
│
├── app/                      # Core Python Application
│   ├── static/               # CSS, JS, and custom animations
│   │   ├── css/              # Custom styles & scanner hover effects (styles.css)
│   │   └── js/               # Camera stream & frontend interaction scripts (scanner.js, main.js)
│   ├── templates/            # HTML templates (Jinja2 + Tailwind CDN)
│   │   ├── base.html         # Main layout with sidebar & live navigation
│   │   ├── dashboard.html    # Overview stats & weekly charts
│   │   ├── employees.html    # Employee management & face registration modal
│   │   ├── scanner.html      # Animated Live Face Scanner with hover effects
│   │   └── attendance.html   # Attendance logs, filters & CSV export
│   ├── database.py           # SQLAlchemy database connection & auto-seeding
│   ├── models.py             # Employee, Department, FaceEmbedding & Attendance schemas
│   ├── face_recognition.py   # OpenCV YuNet + SFace biometric matching engine
│   └── main.py               # FastAPI app entry point & routes
│
├── ml_models/                # Pre-trained face recognition weight files
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
├── data/                     # SQLite database & uploaded employee avatar photos
├── requirements.txt          # Python dependencies
├── Dockerfile                # Production container deployment for Hostinger VPS
└── README.md
```

---

## Quickstart (Local Development)

### 1. Set Up Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Face Models
Ensure pre-trained ONNX models are present in `ml_models/`. If not, run:
```bash
python download_models.py
```

### 3. Run the Application

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser to:
- **Dashboard**: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
- **Live Face Scanner**: [http://127.0.0.1:8000/scanner](http://127.0.0.1:8000/scanner)
- **Employee Directory**: [http://127.0.0.1:8000/employees](http://127.0.0.1:8000/employees)
- **View Attendance**: [http://127.0.0.1:8000/attendance](http://127.0.0.1:8000/attendance)

---

## Hostinger Deployment Guide

### Option 1: Docker on Hostinger VPS (Recommended)

1. Connect to your Hostinger VPS via SSH:
   ```bash
   ssh root@your_vps_ip
   ```
2. Clone your repository:
   ```bash
   git clone https://github.com/NgetMeas22/FaceTrack-Management-System.git /var/www/facetrack-ai
   cd /var/www/facetrack-ai
   ```
3. Build and launch with Docker:
   ```bash
   docker build -t facetrack-ai .
   docker run -d --name facetrack -p 80:8000 --restart always facetrack-ai
   ```

### Option 2: Systemd & Python on Hostinger VPS (Direct Linux)

1. Install system dependencies:
   ```bash
   apt update && apt install -y python3-pip python3-venv libgl1 libglib2.0-0 nginx
   ```
2. Clone repository & install dependencies:
   ```bash
   cd /var/www/facetrack-ai
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create systemd service (`/etc/systemd/system/facetrack.service`):
   ```ini
   [Unit]
   Description=FaceTrack AI Service
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/var/www/facetrack-ai
   ExecStart=/var/www/facetrack-ai/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
4. Start service:
   ```bash
   systemctl daemon-reload
   systemctl enable facetrack
   systemctl start facetrack
   ```

### Option 3: Hostinger MySQL Database

To connect FaceTrack AI to a Hostinger MySQL / MariaDB database instead of SQLite, set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="mysql+pymysql://u123456789_user:Password@localhost:3306/u123456789_facetrack"
```
FaceTrack AI will automatically connect and create all tables on first startup.




<!-- .\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 -->