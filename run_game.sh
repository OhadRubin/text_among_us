#!/bin/bash

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "tmux is not installed. Please install it first."
    echo "On Ubuntu/Debian: sudo apt-get install tmux"
    echo "On MacOS: brew install tmux"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install websockets python-multipart asyncio fastapi uvicorn watchdog

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Create new tmux session named 'among-us-dev' in detached mode
tmux new-session -d -s among-us-dev

# Split window into three panes
tmux split-window -h
# tmux split-window -v

# Send commands to each pane
# Game server with auto-reload
tmux send-keys -t among-us-dev:0.0 "python game_server.py" C-m

# Proxy server with auto-reload
# Frontend with development server
tmux send-keys -t among-us-dev:0.1 "cd frontend && npm run dev" C-m

# Attach to the tmux session
tmux attach-session -t among-us-dev

# Note: To exit, press Ctrl+B then type :kill-session 