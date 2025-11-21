#!/bin/bash
# Launch script for Real Estate Multi-Agent Assistant

echo "🏢 Real Estate Multi-Agent Assistant"
echo "===================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python3.11 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local file not found"
    echo "   Please create it with your HuggingFace API token:"
    echo "   echo 'HUGGINGFACE_API_TOKEN=your_token_here' > .env.local"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🚀 Starting Streamlit application..."
echo ""

streamlit run frontend/streamlit_app.py

