#!/bin/bash

# Enhanced start script for iScan backend on Ubuntu server
set -e  # Exit on any error

echo "=== Starting iScan Backend ==="

# Wait for database to be ready
echo "Waiting for database connection..."
python wait-for-db.py

# Test imports
echo "Testing Python imports..."
python test_imports.py

# Test FTP connection
echo "Testing FTP connection..."
python test_ftp.py || echo "Warning: FTP test failed, continuing..."

# Initialize database
echo "Initializing database..."
python init_db.py

# Start the application (no Railway check needed)
echo "Starting application..."

if [ "$DEBUG" = "true" ] || [ "$NODE_ENV" = "development" ]; then
    echo "Running in DEVELOPMENT mode with auto-reload..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
else
    echo "Running in PRODUCTION mode..."
    # Check if gunicorn is available
    if command -v gunicorn &> /dev/null; then
        echo "Using Gunicorn with Uvicorn workers..."
        exec gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --access-logfile - --error-logfile - --log-level info
    else
        echo "Using Uvicorn..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
    fi
fi
