#!/bin/bash
echo "🚀 Starting Sonos API Demo..."
cd demo_api
pip install -r requirements.txt
uvicorn sonos_api_demo:app --host 0.0.0.0 --port 8000 --reload
