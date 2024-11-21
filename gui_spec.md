This document outlines the technical specifications for implementing a multiplayer game inspired by "Among Us". The project will be split into frontend and backend components, with real-time communication via WebSockets.

## Repository Requirements
This repository must implement:

1. **Frontend**
- React-based game client with WebSocket communication
- Real-time chat functionality  
- Interactive game interface with rooms and player movements
- Support for different game phases (discussion, voting, etc.)

2. **Backend**
- FastAPI-based WebSocket proxy server
- Python game server handling game logic
- Support for both CLI and GUI game clients

## Implementation Requirements

1. **Required Setup Script**
The repository shall include a setup script (`setup.sh`) that creates the directory structure and copies files to their appropriate locations:

```bash
./setup.sh
```

This must:
- Create frontend and backend directories
- Copy game client components
- Set up Docker configuration
- Start the containers


1. **Runtime Requirements**
- Backend servers (proxy and game server) must be operational
- Frontend application must be launched
- Connection must be established through WebSocket on `ws://localhost:8009/ws`

## Architecture Specifications
- Frontend must communicate with proxy server on port 8009
- Proxy must forward messages to game server on port 8765
- Game server must manage game state, player roles, and game mechanics

## Required Features
- Real-time multiplayer interaction
- Role-based gameplay (impostor vs. others)
- Room-based movement system
- Chat functionality
- Voting and discussion phases
- Body reporting and emergency meetings

The application must use Docker for containerization to ensure consistent deployment and runtime across different environments.
