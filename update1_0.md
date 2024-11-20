# Version 1.0 Specification: Basic Client-Server Communication and Movement

## Overview

This document outlines the specifications for **Version 1.0** of a text-based **Among Us** game. The focus is on establishing the core networking infrastructure and enabling basic player movement within a simplified map. This foundational version sets the stage for future updates that will introduce more complex game mechanics.

## Objectives

- **Establish Client-Server Architecture**: Implement a robust asynchronous WebSocket server to handle multiple client connections.
- **Enable Basic Movement**: Allow players to move between rooms in a simplified map structure.
- **Implement Basic Commands**: Provide a command-line interface for players to interact with the game.

---

## Server Components

### 1. WebSocket Server Setup

- **Libraries**: Use `asyncio` and `websockets` to create the server.
  - `asyncio`: For handling asynchronous operations.
  - `websockets`: For WebSocket protocol implementation.
- **Server Initialization**: Maintain a dictionary of connected players and initialize the game map.

```python
import asyncio
import websockets

class GameServer:
    def __init__(self):
        self.players = {}
        self.map_structure = self.initialize_map()

    async def start_server(self):
        server = await websockets.serve(self.handle_connection, 'localhost', 8765)
        await server.wait_closed()
```

### 2. Player Session Management

- **Assign Unique Player IDs**: Use UUIDs to uniquely identify players.
  
  ```python
  import uuid

  def generate_unique_id(self):
      return str(uuid.uuid4())
  ```
  
- **Handle Connections**: Add players to the `self.players` dictionary upon connection.

  ```python
  async def handle_connection(self, websocket, path):
      player_id = self.generate_unique_id()
      self.players[player_id] = {
          'websocket': websocket,
          'location': 'cafeteria'
      }
      await self.handle_player_messages(websocket, player_id)
  ```

### 3. Map Implementation

- **Simplified Map Structure**: Represent the map as a graph (dictionary) of rooms and their connections.

  ```python
  def initialize_map(self):
      return {
          'cafeteria': ['upper_engine', 'medbay'],
          'upper_engine': ['cafeteria', 'reactor'],
          'medbay': ['cafeteria'],
          'reactor': ['upper_engine']
      }
  ```

### 4. Movement Handling

- **Process Movement Commands**: Receive and interpret movement commands from clients.

  ```python
  async def process_message(self, message, player_id):
      data = json.loads(message)
      if data['type'] == 'action' and data['payload']['action'] == 'move':
          await self.handle_move(player_id, data['payload']['destination'])
  ```
  
- **Validate and Update Movement**: Check if the move is valid and update the player's location.

  ```python
  def validate_move(self, current_location, destination):
      return destination in self.map_structure.get(current_location, [])

  async def handle_move(self, player_id, destination):
      current_location = self.players[player_id]['location']
      if self.validate_move(current_location, destination):
          self.players[player_id]['location'] = destination
          await self.send_state_update(player_id)
      else:
          await self.send_error(player_id, "Invalid move.")
  ```

---

## Client Components

### 1. Command-Line Interface (CLI)

- **User Input Parsing**: Accept and parse commands from the player.

  ```python
  def parse_command(input_line):
      tokens = input_line.strip().split()
      command = tokens[0]
      args = tokens[1:]
      return command, args
  ```

- **Supported Commands**:
  - `move <destination>`: Move to an adjacent room.
  - `look`: Display the current location and available exits.
  - `help`: Show available commands.

- **Command Loop Example**:

  ```python
  while True:
      input_line = input("> ")
      command, args = parse_command(input_line)
      if command == "move":
          destination = args[0]
          await send_move_command(destination)
      elif command == "look":
          display_current_location()
      elif command == "help":
          display_help()
  ```

### 2. HUD Display

- **Display Current Location and Exits**:

  ```python
  def display_current_location(location, available_exits):
      print(f"Current Location: {location}")
      print("Available Exits:")
      for exit in available_exits:
          print(f"  - {exit}")
  ```

- **Example Display**:

  ```
  Current Location: Cafeteria
  Available Exits:
    - Upper Engine
    - MedBay
  ```

---

## Communication Protocol

### 1. Message Types

- **Action Messages (Client-to-Server)**: Used to send player actions.

  ```json
  {
    "type": "action",
    "payload": {
      "action": "move",
      "destination": "upper_engine"
    },
    "player_id": "player_1"
  }
  ```

- **State Messages (Server-to-Client)**: Used to update the client on the game state.

  ```json
  {
    "type": "state",
    "payload": {
      "location": "upper_engine",
      "available_exits": ["cafeteria", "reactor"]
    },
    "player_id": "player_1"
  }
  ```

### 2. Message Format

- **Structure**:

  ```json
  {
    "type": "action" | "state",
    "payload": { /* message-specific data */ },
    "player_id": "<unique_player_id>"
  }
  ```

---

## Game Flow

### Movement Sequence

1. **Player Inputs Command**: The player types `move upper_engine`.
2. **Client Sends Action Message**: The command is sent to the server.
3. **Server Validates Move**: Checks if `upper_engine` is adjacent to `cafeteria`.
4. **Server Updates Location**: Player's location is updated if valid.
5. **Server Sends State Update**: New location and available exits are sent back.
6. **Client Updates HUD**: The client displays the updated location and exits.

---

## Technical Requirements

### 1. Python Compatibility

- **Version**: Python 3.8 or higher.

### 2. Dependencies

- **`requirements.txt`**:

  ```
  asyncio>=3.4.3
  websockets>=10.0
  ```

- **Installation**:

  ```bash
  pip install -r requirements.txt
  ```

### 3. Testing

- **Unit Tests**: Implement tests for movement validation and player connections.

  ```python
  def test_validate_move():
      game_server = GameServer()
      assert game_server.validate_move('cafeteria', 'upper_engine') == True
      assert game_server.validate_move('upper_engine', 'medbay') == False
  ```

- **Testing Framework**: Use `pytest`.

  ```bash
  pytest tests/
  ```

### 4. Logging

- **Setup Logging**:

  ```python
  import logging

  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(levelname)s - %(message)s',
      handlers=[
          logging.FileHandler('game_server.log'),
          logging.StreamHandler()
      ]
  )
  ```

- **Usage**:

  ```python
  logging.info(f"Player {player_id} connected.")
  logging.info(f"Player {player_id} moved to {destination}.")
  ```

---

## Implementation Tips

- **Start Simple**: Begin with a minimal map for testing.

  ```python
  def initialize_map(self):
      return {
          'cafeteria': ['upper_engine', 'medbay'],
          'upper_engine': ['cafeteria'],
          'medbay': ['cafeteria']
      }
  ```

- **Error Handling**: Implement robust exception handling for WebSocket connections.

  ```python
  async def handle_player_messages(self, websocket, player_id):
      try:
          async for message in websocket:
              await self.process_message(message, player_id)
      except websockets.exceptions.ConnectionClosedError:
          logging.warning(f"Connection closed unexpectedly for player {player_id}.")
      finally:
          del self.players[player_id]
  ```

- **Use Type Hints**: Enhance code readability and maintainability.

  ```python
  def validate_move(self, current_location: str, destination: str) -> bool:
      return destination in self.map_structure.get(current_location, [])
  ```

- **Write Tests Early**: Implement tests alongside development for each component.

---

## Conclusion

By implementing the specifications outlined in Version 1.0, you will establish the foundational infrastructure for a multiplayer text-based Among Us game. This includes:

- A robust **client-server architecture** using WebSockets.
- Basic **player movement** within a simplified map.
- A clear **communication protocol** for client-server interactions.
- Essential **testing** and **logging** practices.

These components will serve as the building blocks for future updates, where more complex game mechanics and features will be introduced.

---

## Next Steps

After completing Version 1.0, the next phase will focus on:

- **Introducing Player Roles**: Assigning roles such as Crewmate and Impostor.
- **Implementing Game Actions**: Adding actions like killing and reporting.

---

# Appendix: Summary of Key Components

- **Map Structure**: A simplified graph representing rooms and their connections.
- **Player State**: Each player has a unique ID, current location, and WebSocket connection.
- **Commands**:
  - `move <destination>`: Move to an adjacent room.
  - `look`: Display current location and exits.
- **Message Protocol**:
  - **Action Messages**: Client-to-server messages for player actions.
  - **State Messages**: Server-to-client messages updating the game state.