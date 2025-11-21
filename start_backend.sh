#!/bin/bash

# Start FastAPI Backend for Real Estate AI Assistant

echo "🚀 Starting FastAPI Backend..."

# Navigate to project root
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Start FastAPI with uvicorn (from project root, pointing to backend.app)
PYTHONPATH="$(pwd):$PYTHONPATH" python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

echo "✅ Backend running at http://localhost:8000"
echo "📖 API docs at http://localhost:8000/docs"

