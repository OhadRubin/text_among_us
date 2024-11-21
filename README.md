# Text-Based Among Us Implementation Guide

This repository contains the detailed specifications for implementing a Text-Based Among Us game, divided into six progressive updates. Each update builds upon the previous ones, allowing for systematic development and testing.

## Updates Overview

1. [Basic Client-Server Communication and Movement](update1.md)
2. [Role Assignment and Basic Actions](update2.md)
3. [Discussion and Voting Phases](update3.md)
4. [Tasks and Win Conditions](update4.md)
5. [Advanced Impostor Mechanics](update5.md)
6. [Security Enhancements and Configuration Options](update6.md)

## Development Approach

This progressive implementation approach allows developers to:
- **Test and validate** each component thoroughly before moving on
- **Iteratively build** upon previous updates, ensuring stability
- **Adjust and refine** features based on testing outcomes
- **Ensure security and performance** through dedicated updates

Each update file contains detailed specifications for:
- Server Components
- Client Components
- Communication Protocols
- Game Mechanics
- Technical Requirements 

# Among Us Clone

A multiplayer game inspired by Among Us, featuring both CLI and GUI clients.

## Requirements

- Docker and Docker Compose
- Node.js 14+ (for local development)
- Python 3.9+ (for local development)

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

3. Access the game at http://localhost:3000

## Development Setup

### Frontend Development

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

### Backend Development

1. Set up Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install proxy server dependencies:
```bash
cd backend/proxy
pip install -r requirements.txt
```

3. Install game server dependencies:
```bash
cd backend/game
pip install -r requirements.txt
```

4. Run servers locally:
```bash
# Terminal 1 - Proxy Server
cd backend/proxy
uvicorn main:app --host 0.0.0.0 --port 8009

# Terminal 2 - Game Server
cd backend/game
python game_server.py
```

## Architecture

- Frontend (React) - Port 3000
- Proxy Server (FastAPI) - Port 8009
- Game Server (WebSocket) - Port 8765

## Features

- Real-time multiplayer gameplay
- Role-based mechanics (Impostor vs Crewmates)
- Room-based movement system
- In-game chat
- Voting and discussion phases
- Body reporting and emergency meetings 