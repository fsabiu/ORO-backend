# ORO Backend

Oracle Spatial-based Object Recognition and Operations API - A FastAPI backend service for object recognition and spatial operations.

## Overview

The ORO Backend is a FastAPI application that provides REST API endpoints for:
- Object recognition using machine learning models
- Spatial operations and analysis
- Report generation and processing
- Ruleset management

## Prerequisites

- Python 3.12+
- Conda/Miniconda/MiniForge
- Oracle Database (for spatial operations)
- Required Python packages (see requirements.txt)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ORO-backend
   ```

2. **Create and activate conda environment:**
   ```bash
   conda create -n ORO python=3.12
   conda activate ORO
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (if needed):
   ```bash
   export HOST=0.0.0.0
   export PORT=8000
   export RELOAD=true
   export LOG_LEVEL=info
   ```

## Running the Application

### Option 1: Standard Run (Development)

**Using the startup script (Recommended):**
```bash
cd /home/ubuntu/ORO-backend
conda activate ORO
python run_server.py
```

**Using uvicorn directly:**
```bash
cd /home/ubuntu/ORO-backend
conda activate ORO
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Running the main module:**
```bash
cd /home/ubuntu/ORO-backend
conda activate ORO
python -m app.main
```

### Option 2: Systemd Service (Production)

#### Service Setup

1. **Install the service:**
   ```bash
   # Copy the service file to systemd directory
   sudo cp /home/ubuntu/ORO-backend/oro-backend.service /etc/systemd/system/
   
   # Reload systemd to recognize the new service
   sudo systemctl daemon-reload
   
   # Enable the service to start on boot
   sudo systemctl enable oro-backend
   ```

2. **Start the service:**
   ```bash
   sudo systemctl start oro-backend
   ```

#### Service Management Commands

**Start the service:**
```bash
sudo systemctl start oro-backend
```

**Stop the service:**
```bash
sudo systemctl stop oro-backend
```

**Restart the service:**
```bash
sudo systemctl restart oro-backend
```

**Check service status:**
```bash
sudo systemctl status oro-backend
```

**Enable service on boot:**
```bash
sudo systemctl enable oro-backend
```

**Disable service on boot:**
```bash
sudo systemctl disable oro-backend
```

#### Log Management

**View real-time logs:**
```bash
sudo journalctl -u oro-backend -f
```

**View recent logs:**
```bash
sudo journalctl -u oro-backend -n 50
```

**View logs from today:**
```bash
sudo journalctl -u oro-backend --since today
```

**View logs with timestamps:**
```bash
sudo journalctl -u oro-backend -o short-precise
```

**View error logs only:**
```bash
sudo journalctl -u oro-backend -p err
```

**View logs from specific time:**
```bash
sudo journalctl -u oro-backend --since "2024-01-01 00:00:00"
```

**View logs between specific times:**
```bash
sudo journalctl -u oro-backend --since "2024-01-01 00:00:00" --until "2024-01-01 23:59:59"
```

#### Service Configuration

The service file (`oro-backend.service`) includes:
- **User/Group**: Runs as `ubuntu` user
- **Working Directory**: `/home/ubuntu/ORO-backend`
- **Environment**: Uses the ORO conda environment path
- **ExecStart**: Uses the conda environment's Python to run `run_server.py`
- **Restart Policy**: Automatically restarts on failure with 10-second delay
- **Logging**: Outputs to systemd journal

#### Troubleshooting Service Issues

**Check if service is enabled:**
```bash
sudo systemctl is-enabled oro-backend
```

**Check if service is active:**
```bash
sudo systemctl is-active oro-backend
```

**Reload service configuration (after modifying the service file):**
```bash
sudo systemctl daemon-reload
sudo systemctl restart oro-backend
```

**View detailed service information:**
```bash
sudo systemctl show oro-backend
```

**Check service dependencies:**
```bash
sudo systemctl list-dependencies oro-backend
```

## API Documentation

Once the application is running, access the API documentation:

- **API Base URL:** http://localhost:8000
- **Interactive API Documentation (Swagger):** http://localhost:8000/docs
- **ReDoc Documentation:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

## API Endpoints

### Health Check
- `GET /health` - Check application and database health

### Root
- `GET /` - API information and version

### API v1 Routes
- `/api/v1/rulesets/` - Ruleset management
- `/api/v1/reports/` - Report processing and management

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Host to bind the server |
| `PORT` | `8000` | Port to bind the server |
| `RELOAD` | `true` | Enable auto-reload on code changes |
| `LOG_LEVEL` | `info` | Logging level |

## Development

### Project Structure
```
ORO-backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database connection and operations
│   ├── models.py            # Pydantic models
│   ├── routes/              # API route handlers
│   ├── services/            # Business logic services
│   └── tasks/               # Background task processing
├── db/                      # Database initialization scripts
├── models/                  # Machine learning model files
├── docs/                    # Documentation
├── tests/                   # Test files
├── run_server.py            # Server startup script
├── oro-backend.service      # Systemd service file
└── requirements.txt         # Python dependencies
```

### Testing
```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app
```

## Quick Start Commands

**For Development:**
```bash
conda activate ORO
python run_server.py
```

**For Production Service:**
```bash
# Setup (one-time)
sudo cp oro-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oro-backend

# Start service
sudo systemctl start oro-backend

# Check status
sudo systemctl status oro-backend

# View logs
sudo journalctl -u oro-backend -f
```

## Support

For issues and questions, please check the logs first:
```bash
sudo journalctl -u oro-backend -n 100
```

Then refer to the API documentation at http://localhost:8000/docs when the service is running.