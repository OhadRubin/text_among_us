#!/bin/bash
cd all
# Create directory structure
mkdir -p frontend/src/components
mkdir -p backend/game
mkdir -p backend/proxy

# Copy frontend files
echo "Setting up frontend..."
cat > frontend/package.json << 'EOF'
{
  "name": "among-us-clone",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^17.0.2",
    "react-dom": "^17.0.2",
    "react-scripts": "4.0.3",
    "websocket": "^1.0.34"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF

# Copy backend requirements
echo "Setting up backend requirements..."
cat > backend/game/requirements.txt << 'EOF'
websockets==10.0
python-multipart==0.0.5
asyncio==3.4.3
EOF

cat > backend/proxy/requirements.txt << 'EOF'
fastapi==0.68.1
uvicorn==0.15.0
websockets==10.0
python-multipart==0.0.5
EOF

# Copy Docker configurations
echo "Setting up Docker configurations..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - REACT_APP_WS_URL=ws://localhost:8009/ws
      - NODE_ENV=development
    depends_on:
      - proxy_server

  proxy_server:
    build:
      context: ./backend/proxy
      dockerfile: Dockerfile
    ports:
      - "8009:8009"
    environment:
      - GAME_SERVER_URL=ws://game_server:8765
    depends_on:
      - game_server

  game_server:
    build:
      context: ./backend/game
      dockerfile: Dockerfile
    ports:
      - "8765:8765"
    volumes:
      - ./backend/game:/app
    environment:
      - PYTHONUNBUFFERED=1
      - DEBUG=1

networks:
  default:
    driver: bridge
EOF

# Start containers
echo "Starting Docker containers..."
docker-compose up -d

echo "Setup complete! The game should be available at http://localhost:3000" 