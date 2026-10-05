#!/bin/bash

# PDF Chat & Summarizer - Startup Script
echo "🚀 Starting AI RAG System (Backend + Frontend)"
echo "==============================================="

# Start FastAPI backend in the background
echo "🔌 Starting FastAPI backend on port 8000..."
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a couple seconds for backend to initialize
sleep 2

# Start Streamlit frontend
echo "🎯 Starting Streamlit frontend..."
echo "📱 The app will open in your browser at http://localhost:8501"
echo "🛑 Press Ctrl+C to stop both applications"
echo ""

uv run streamlit run frontend/app.py

# Cleanup backend when streamlit stops
kill $BACKEND_PID
