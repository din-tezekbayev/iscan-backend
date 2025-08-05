#!/bin/bash

# Wait for database to be ready
python wait-for-db.py

# Test imports
python test_imports.py

# Initialize database
python init_db.py

# Start the application
if [ "$RAILWAY_ENVIRONMENT" = "production" ]; then
    # Production with gunicorn
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
else
    # Development
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi