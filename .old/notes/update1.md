# Update 1: Basic Client-Server Communication and Movement

## Overview

This is the first update in a six-part implementation of a **text-based Among Us game**. This update focuses on establishing the core networking infrastructure and basic movement mechanics, which will serve as the foundation for all future updates.

### **Context**

The text-based Among Us game is a multiplayer game where players will eventually take on roles of **Crewmates** and **Impostors**. This initial update implements only the basic movement and networking, without any role-specific features.

### **Objective**

Establish the foundational client-server architecture and enable basic player movement within a simplified map.

---

## Server Components

### **WebSocket Server Setup**

#### Implement an Asynchronous WebSocket Server

- **Libraries Used**: Utilize `asyncio` and the `websockets` library to create an asynchronous WebSocket server.
  
  - **`asyncio`**: Provides the framework for writing single-threaded concurrent code using coroutines, making it suitable for handling multiple simultaneous connections.
  
  - **`websockets`**: Simplifies the implementation of WebSocket servers and clients in Python.

- **Server Initialization**: The server maintains a list of connected players and the game map.

  ```python
  import asyncio
  import websockets

  class GameServer:
      def __init__(self):
          self.players = {}
          self.map_structure = self.initialize_map()
  ```

#### Handle Player Connections and Disconnections Gracefully

- **Connection Handling**: When a player connects, assign a unique ID and store their initial state.

  ```python
  async def handle_connection(self, websocket, path):
      player_id = self.generate_unique_id()
      self.players[player_id] = {
          'websocket': websocket,
          'location': 'spawn_point'
      }
      logging.info(f"Player {player_id} connected.")
      try:
          await self.handle_player_messages(websocket, player_id)
      finally:
          del self.players[player_id]
          logging.info(f"Player {player_id} disconnected.")
  ```

- **Disconnection Handling**: Ensure resources are cleaned up when a player disconnects to prevent memory leaks.

### **Player Session Management**

#### Assign Unique `player_id` to Each Connected Player

- **ID Generation**: Use a UUID or incrementing integer to generate unique player IDs.

  ```python
  import uuid

  def generate_unique_id(self):
      return str(uuid.uuid4())
  ```

#### Maintain a Dictionary of Connected Players with Their Attributes

- **Player Attributes**:

  - **`player_id`**: Unique identifier for each player.
  - **`location`**: The current location of the player on the map.
  - **`websocket`**: The WebSocket connection associated with the player.

  ```python
  self.players = {
      player_id: {
          'websocket': websocket,
          'location': 'spawn_point'
      },
      # ... other players
  }
  ```

### **Map Implementation**

#### Create a Simplified Graph-Based Map

- **Map Structure**: Represent the map as a dictionary or adjacency list to model rooms and their connections.

  ```python
  def initialize_map(self):
      return {
          'cafeteria': ['upper_engine', 'medbay', 'admin'],
          'upper_engine': ['cafeteria', 'reactor', 'security'],
          'medbay': ['cafeteria', 'engine_room'],
          # ... additional rooms and connections
      }
  ```

- **Benefits**:

  - **Easy Navigation**: Simplifies movement validation and pathfinding.
  - **Scalability**: Allows for easy expansion of the map with more rooms and connections.

### **Movement Handling**

#### Process Movement Commands

- **Command Parsing**: Interpret movement commands received from the client.

  ```python
  async def process_message(self, message, player_id):
      data = json.loads(message)
      if data['type'] == 'action':
          action = data['payload']['action']
          if action == 'move':
              await self.handle_move(player_id, data['payload']['destination'])
  ```

#### Update Player Locations on the Server

- **Validate Move**: Ensure the desired move is valid based on the current location and map structure.

  ```python
  def validate_move(self, current_location, destination):
      return destination in self.map_structure.get(current_location, [])
  ```

- **Move Player**: Update the player's location if the move is valid.

  ```python
  async def handle_move(self, player_id, destination):
      current_location = self.players[player_id]['location']
      if self.validate_move(current_location, destination):
          self.players[player_id]['location'] = destination
          await self.send_state_update(player_id)
          logging.info(f"Player {player_id} moved to {destination}.")
      else:
          await self.send_error(player_id, "Invalid move.")
  ```

#### Notify Nearby Players of Movements (If Applicable)

- **Future Implementation**: While not required in this update, set up the framework to notify other players in the same location.

  ```python
  async def notify_nearby_players(self, location, message):
      for player in self.players.values():
          if player['location'] == location:
              await player['websocket'].send(message)
  ```

---

## Client Components

### **CLI Interface**

#### Develop a Command-Line Interface for Player Input

- **Command Parsing**: Accept user input and parse commands.

  ```python
  def parse_command(self, input_line):
      tokens = input_line.strip().split()
      command = tokens[0]
      args = tokens[1:]
      return command, args
  ```

- **Supported Commands**:

  - **`move <destination>`**: Move to an adjacent room.
  - **`look`**: Display current room and available exits.
  - **`players`**: List nearby players.
  - **`help`**: Show available commands.

- **Example Command Loop**:

  ```python
  while True:
      input_line = input("> ")
      command, args = parse_command(input_line)
      if command == "move":
          destination = args[0]
          await send_move_command(destination)
      elif command == "look":
          display_current_location()
      elif command == "players":
          display_nearby_players()
      elif command == "help":
          display_help()
  ```

### **HUD Display**

#### Show the Player's Current Location and Available Exits

- **Display Function**:

  ```python
  def display_current_location(self):
      print(f"Current Location: {self.location}")
      print("Available Exits:")
      for exit in self.available_exits:
          print(f"  - {exit}")
  ```

#### Display Nearby Players

- **Display Function**:

  ```python
  def display_nearby_players(self):
      print("Nearby Players:")
      for player in self.nearby_players:
          print(f"  - {player}")
  ```

#### Example Display

```
Current Location: Cafeteria
Available Exits:
  - Upper Engine
  - MedBay
  - Admin
Nearby Players: player_2, player_5
```

---

## Communication Protocol

### **Message Types**

#### `action` Messages (Client-to-Server)

- **Purpose**: To convey player actions such as movement.

- **Example**:

  ```json
  {
    "type": "action",
    "payload": {
      "action": "move",
      "destination": "upper_engine"
    },
    "timestamp": "2023-10-05T14:48:00Z",
    "player_id": "player_1"
  }
  ```

#### `state` Messages (Server-to-Client)

- **Purpose**: To update the client with the current game state.

- **Example**:

  ```json
  {
    "type": "state",
    "payload": {
      "location": "cafeteria",
      "nearby_players": ["player_2", "player_5"],
      "available_exits": ["upper_engine", "medbay", "admin"]
    },
    "timestamp": "2023-10-05T14:48:01Z",
    "player_id": "player_1"
  }
  ```

### **Message Format**

- **Structure**:

  ```json
  {
    "type": "action" | "state",
    "payload": { /* specific to message type */ },
    "timestamp": "<ISO 8601 timestamp>",
    "player_id": "<unique_player_id>"
  }
  ```

- **Fields**:

  - **`type`**: Identifies the message as an action or state update.
  - **`payload`**: Contains the data relevant to the message.
  - **`timestamp`**: Indicates when the message was sent.
  - **`player_id`**: Identifies the player associated with the message.

---

## Game Flow

### **Free Roam Phase**

- **Overview**: Players can move freely within the map without any role-specific interactions.

#### Movement Sequence

1. **Player Inputs Movement Command**

   - The player types a command like `move upper_engine`.

2. **Client Sends Action Message**

   - The client constructs and sends an action message to the server.

3. **Server Validates Move**

   - The server checks if the destination is a valid adjacent room.

4. **Server Updates Player Location**

   - If valid, the server updates the player's location.

5. **Server Sends State Update**

   - The server sends a state message back to the client with updated information.

6. **Client Updates HUD**

   - The client updates the display to reflect the new state.

---

## Technical Requirements

### **Python Compatibility**

- **Version**: Use **Python 3.8+**.

  - **Reason**: Leverage enhanced `asyncio` features and type hints introduced in Python 3.8.

### **Dependencies**

- **`requirements.txt`**:

  ```text
  asyncio>=3.4.3
  websockets>=10.0
  pytest>=6.0.0
  ```

- **Installation**:

  ```bash
  pip install -r requirements.txt
  ```

### **Testing**

#### Implement Basic Unit Tests

- **Test Movement Validation**:

  ```python
  def test_movement_validation():
      game_server = GameServer()
      game_server.map_structure = {
          'cafeteria': ['upper_engine'],
          'upper_engine': ['cafeteria']
      }
      assert game_server.validate_move('cafeteria', 'upper_engine') == True
      assert game_server.validate_move('upper_engine', 'admin') == False
  ```

- **Test Player Connection**:

  ```python
  @pytest.mark.asyncio
  async def test_player_connection():
      server = GameServer()
      websocket = MockWebSocket()
      await server.handle_connection(websocket, '/')
      assert len(server.players) == 1
  ```

#### Use `pytest` for Testing

- **Run Tests**:

  ```bash
  pytest tests/
  ```

### **Logging**

#### Log Player Connections, Disconnections, and Movements

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
  logging.info(f"Player {player_id} disconnected.")
  ```

---

## Next Steps

After completing this update, the next phase (**Update 2**) will introduce:

- **Player Roles**: Assign roles of Crewmate and Impostor to players.
- **Basic Game Actions**: Implement actions such as killing and reporting.

---

## Implementation Tips

### Start with a Simple Map Layout for Initial Testing

- **Example**:

  ```python
  def initialize_map(self):
      return {
          'cafeteria': ['upper_engine', 'medbay'],
          'upper_engine': ['cafeteria'],
          'medbay': ['cafeteria']
      }
  ```

### Implement Robust Error Handling for WebSocket Connections

- **Handle Exceptions**:

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

### Use Type Hints to Make the Code More Maintainable

- **Example**:

  ```python
  def validate_move(self, current_location: str, destination: str) -> bool:
      return destination in self.map_structure.get(current_location, [])
  ```

### Add Comprehensive Logging for Debugging

- **Include Contextual Information**:

  ```python
  logging.debug(f"Processing message from player {player_id}: {message}")
  ```

### Write Tests for Each Component Before Moving to the Next

- **Test-Driven Development**: Implement unit tests for new features before coding them to ensure correctness.

---

## Conclusion

By completing this update, we've established the foundational infrastructure necessary for a multiplayer text-based Among Us game. We've set up:

- A robust **client-server architecture** using WebSockets.
- Basic **player movement mechanics** within a simplified map.
- A clear **communication protocol** for client-server interactions.
- Essential **testing** and **logging** practices for maintainability.

These components will serve as the building blocks for future updates, where we'll introduce more complex game mechanics and features.


# Map Specifications for Text-Based Among Us

## Room Dimensions and Layout

### Room Dimensions
- Each room is represented as a single node in the graph
- Rooms do not have physical dimensions as this is a text-based game
- Players in the same room can interact with each other regardless of position within the room

### Visual Layout
```
[Cafeteria]---[Upper Engine]---[Reactor]
     |              |             |
[MedBay]---[Engine Room]---[Security]
     |              |             |
[Storage]---[Lower Engine]---[Electrical]
```

- ASCII representation should be shown to players when they use the `map` command
- Each room is connected by `---` to show valid movement paths
- Current room should be highlighted with `[*Room Name*]` when displayed

## Player Limits and Capacity

### Room Capacity
- Maximum 5 players per room (prevents overcrowding and maintains game balance)
- Exception: Cafeteria (spawn room) can hold all players (up to server maximum)
- When a room reaches capacity:
  - Players receive "Room Full" message when attempting to enter
  - Must choose a different adjacent room
  - Can still perform emergency meetings in full rooms

### Server Limits
- Maximum 10 players per game server
- Minimum 4 players to start a game

## Spawn Points

### Primary Spawn
- All players spawn in Cafeteria at game start
- After meetings, players return to their previous locations
- After death, ghost players spawn in their death location

### Implementation
```python
class GameServer:
    def __init__(self):
        self.SPAWN_ROOM = 'cafeteria'
        self.ROOM_CAPACITY = {
            'cafeteria': 10,  # Special case: can hold all players
            'default': 5      # All other rooms
        }
        
    def get_room_capacity(self, room_name: str) -> int:
        return self.ROOM_CAPACITY.get(room_name, self.ROOM_CAPACITY['default'])

    def can_enter_room(self, room_name: str) -> bool:
        current_occupants = len([p for p in self.players.values() 
                               if p['location'] == room_name])
        return current_occupants < self.get_room_capacity(room_name)
```

## Map Constants

### Room Configuration
- Minimum 9 rooms for standard gameplay
- Fixed map layout (not configurable) to maintain game balance
- Required rooms:
  1. Cafeteria (central hub, spawn point)
  2. Upper Engine
  3. Lower Engine
  4. Reactor
  5. Security
  6. Electrical
  7. MedBay
  8. Storage
  9. Engine Room

### Implementation
```python
def initialize_map(self):
    return {
        'cafeteria': ['upper_engine', 'medbay', 'storage'],
        'upper_engine': ['cafeteria', 'reactor', 'engine_room'],
        'reactor': ['upper_engine', 'security'],
        'security': ['reactor', 'engine_room', 'electrical'],
        'electrical': ['security', 'lower_engine'],
        'lower_engine': ['electrical', 'engine_room', 'storage'],
        'engine_room': ['upper_engine', 'security', 'lower_engine'],
        'storage': ['cafeteria', 'lower_engine'],
        'medbay': ['cafeteria', 'engine_room']
    }
```

## Display Commands

### New Command: `map`
```python
def display_map(self, player_location: str) -> None:
    """
    Display ASCII map with current location marked
    """
    map_template = """
    [Cafeteria]---[Upper Engine]---[Reactor]
         |              |             |
    [MedBay]---[Engine Room]---[Security]
         |              |             |
    [Storage]---[Lower Engine]---[Electrical]
    """
    # Highlight current location
    highlighted_map = map_template.replace(
        f'[{player_location}]',
        f'[*{player_location}*]'
    )
    print(highlighted_map)
```

### Updated Look Command
```python
def display_current_location(self):
    print(f"Current Location: {self.location}")
    print(f"Players here: {len(self.get_players_in_room(self.location))}/{self.get_room_capacity(self.location)}")
    print("Available Exits:")
    for exit in self.available_exits:
        if self.can_enter_room(exit):
            print(f"  - {exit}")
        else:
            print(f"  - {exit} (FULL)")
```

## Rationale for Specifications

1. **Room Capacity Limits**
   - Prevents players from all grouping in one room
   - Creates strategic decisions about movement
   - Maintains game balance for impostor gameplay

2. **Fixed Map Layout**
   - Ensures consistent gameplay experience
   - Allows for balanced task distribution
   - Simplifies implementation and testing

3. **Spawn Point Design**
   - Central location provides equal access to all areas
   - Cafeteria capacity exception prevents spawn crowding
   - Maintains original Among Us gameplay feel

4. **Visual Representation**
   - Simple ASCII art maintains text-based nature
   - Clear connection visualization helps navigation
   - Current location highlighting improves user experience 



## Tests

1. Map Structure Tests
- Verify all 9 required rooms exist in the map
- Verify bidirectional connections (if A connects to B, B must connect to A)
- Verify the minimum number of exits for each room matches the ASCII diagram
- Verify no isolated rooms exist (all rooms must be reachable)
- Test that invalid room names cannot be added to the map
- Verify the spawn room (Cafeteria) exists and is properly connected

2. Room Capacity Tests
- Verify Cafeteria can hold maximum server capacity (10 players)
- Verify all other rooms enforce 5-player capacity limit
- Test room entry when at capacity:
  * Attempt to enter full room
  * Verify appropriate "Room Full" message
  * Verify player remains in original location
- Test edge cases:
  * Room at exactly capacity
  * Room with one space remaining
  * Empty room
  * Room with negative player count (error case)

3. Player Spawn Tests
- Verify all players initially spawn in Cafeteria
- Test post-meeting spawn behavior (players return to previous locations)
- Test ghost spawn behavior (spawn at death location)
- Verify spawn behavior with maximum players
- Test spawn behavior when Cafeteria is temporarily at capacity

4. Server Limit Tests
- Verify server enforces 10-player maximum
- Verify game doesn't start with fewer than 4 players
- Test connection handling at server capacity
- Test disconnection/reconnection scenarios
- Verify player count consistency across all rooms

5. Display and Command Tests
- Test map command output:
  * Verify current location is properly highlighted with asterisks
  * Verify ASCII map matches specification
  * Test with player in each possible room
- Test look command output:
  * Verify correct player count display
  * Verify available exits are correctly listed
  * Verify "FULL" indicator appears for full rooms
  * Test with varying room occupancy levels

6. Movement Validation Tests
- Verify movement only between connected rooms
- Test invalid movement attempts:
  * To non-adjacent rooms
  * To non-existent rooms
  * To full rooms
- Verify proper error messages for invalid moves
- Test rapid movement requests
- Test concurrent movement requests from multiple players

7. State Management Tests
- Verify room occupancy counts remain accurate after:
  * Player movements
  * Disconnections
  * Game starts/ends
  * Emergency meetings
- Test player state consistency across server restarts
- Verify no state leaks between different game instances

8. Edge Case Tests
- Test behavior when a player:
  * Attempts to move while in an invalid state
  * Disconnects while moving between rooms
  * Reconnects after unexpected disconnection
- Test system behavior during:
  * Network latency
  * High server load
  * Multiple simultaneous movements
  * Server shutdown/restart

9. Performance Tests
- Measure response time for:
  * Map display with different numbers of players
  * Movement commands under various server loads
  * Room capacity checks with concurrent requests
- Test memory usage with:
  * Maximum player count
  * Extended gameplay sessions
  * Rapid room switching

10. Integration Tests
- Verify correct interaction between:
  * Movement system and room capacity limits
  * Player spawning and room capacity
  * Map display and player location tracking
  * Multiple players moving simultaneously
  * Server limits and room capacity management

11. Security Tests
- Verify players cannot:
  * Move to unauthorized locations
  * Exceed room capacity through rapid movement
  * Manipulate their spawn location
  * Bypass server player limits
- Test input sanitization for commands
- Verify proper handling of malformed messages

12. Clean-up and Resource Management Tests
- Verify proper cleanup after:
  * Player disconnection
  * Game end
  * Server shutdown
- Test resource release for:
  * Player sessions
  * Room occupancy counts
  * Network connections


# Among Us Text-Based Game Version Breakdown

## Version 1.0: Core Movement and Basic Map
**Focus**: Essential networking and movement mechanics

### Features
1. Basic Map Structure
   - Simple 9-room layout without capacity limits
   - Fixed connections between rooms
   - Basic room representation

2. Core Networking
   - WebSocket server setup
   - Basic client-server communication
   - Player connection/disconnection handling
   - Simple session management

3. Basic Movement
   - Simple movement between connected rooms
   - Basic location tracking
   - Movement validation (adjacent rooms only)

4. Basic Commands
   - `move <room>`: Move to adjacent room
   - `look`: Show current room and exits
   - Simple error messages for invalid moves

### Technical Implementation
- Basic WebSocket server
- Simple player state management
- Basic logging system
- Fundamental unit tests for movement and connections

## Version 1.1: Enhanced Map and Room Management
**Focus**: Room management and improved visualization

### Features
1. Enhanced Map Visualization
   - ASCII map display with `map` command
   - Current location highlighting
   - Connection visualization (`---` between rooms)

2. Room Capacity System
   - Implementation of room capacity limits:
     - 5 players per standard room
     - 10 players in Cafeteria
   - "Room Full" notifications
   - Capacity checking before movement

3. Improved Command System
   - Enhanced `look` command with occupancy info
   - Player count display per room
   - Available exits with capacity status

4. Enhanced Error Handling
   - Detailed movement error messages
   - Capacity-related notifications
   - Connection state handling

### Technical Implementation
- Room capacity tracking system
- Enhanced movement validation
- Additional test cases for capacity limits
- Improved logging for room states

## Version 1.2: Server Management and Advanced Features
**Focus**: Server limits and advanced state management

### Features
1. Server Management
   - 10-player server limit
   - 4-player minimum for game start
   - Connection queue management
   - Server state persistence

2. Spawn System
   - Cafeteria as primary spawn point
   - Post-meeting location management
   - Spawn point capacity handling

3. Advanced State Management
   - Player state tracking
   - Room state consistency
   - Concurrent movement handling
   - Disconnection state management

4. Performance Optimizations
   - Efficient room capacity checking
   - Optimized state updates
   - Connection pooling
   - Resource cleanup

### Technical Implementation
- Comprehensive state management system
- Advanced error handling
- Full test suite including:
  - Performance tests
  - Integration tests
  - Security tests
  - Resource management tests

## Migration Notes
- Version 1.0 → 1.1:
  - Add room capacity properties to existing room objects
  - Enhance movement validation to check capacity
  - Update client display system for new visualization

- Version 1.1 → 1.2:
  - Add server management layer
  - Implement spawn point system
  - Enhance state management system
  - Add performance monitoring

## Testing Requirements
### Version 1.0
- Basic movement validation
- Connection handling
- Simple state management
- Command parsing

### Version 1.1
- Room capacity enforcement
- Map display accuracy
- Enhanced movement validation
- Command system expansion

### Version 1.2
- Server limit enforcement
- Spawn system functionality
- State consistency
- Performance benchmarks
- Security validation