#!/bin/bash

# Create directory structure
mkdir -p frontend/components frontend/pages backend

# Copy files to their respective directories
cp gameclient.js frontend/components/GameClient.js
cp index.js frontend/pages/
cp proxy.py backend/
cp simple_server.py backend/

# Create necessary configuration files
echo "Creating configuration files..."

# Copy Dockerfiles and other configuration files
# (Content from the files above would be written here)

# Build and start the containers
docker-compose up --build 