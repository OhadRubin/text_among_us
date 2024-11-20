# Version 1.1 Specification: Enhanced Map and Room Management

## Overview

This document details the specifications for **Version 1.1** of the text-based **Among Us** game. Building upon the foundational client-server architecture and basic movement mechanics established in Version 1.0, this update focuses on enhancing the map visualization, implementing room capacity limits, and improving the command system for a more engaging player experience.

## Objectives

- **Enhanced Map Visualization**: Provide players with an ASCII map representation of the game world.
- **Implement Room Capacity System**: Introduce limits on the number of players per room to encourage strategic movement.
- **Improve Command System**: Expand the `look` command and introduce a new `map` command for better in-game navigation.
- **Enhanced Error Handling**: Offer detailed feedback to players regarding movement and room capacities.

---

## Server Components

### 1. Enhanced Map Implementation

#### Map Structure

- **Fixed Map Layout**: Maintain a consistent map layout with predefined rooms and connections.
- **Room Connections**: Represented as a graph where nodes are rooms, and edges are valid paths between them.

```python
def initialize_map(self):
    return {
        'cafeteria': ['upper_engine', 'medbay', 'storage'],
        'upper_engine': ['cafeteria', 'reactor', 'engine_room'],
        'reactor': ['upper_engine', 'security'],
        'security': ['reactor', 'engine_room', 'electrical'],
        'electrical': ['security', 'lower_engine'],
        'lower_engine': ['electrical', 'engine_room', 'storage'],
        'engine_room': ['upper_engine', 'security', 'lower_engine', 'medbay'],
        'storage': ['cafeteria', 'lower_engine'],
        'medbay': ['cafeteria', 'engine_room']
    }
```

### 2. Room Capacity System

#### Room Capacity Limits

- **Standard Rooms**: Maximum of **5 players** per room.
- **Cafeteria**: Can hold up to **10 players** (server maximum).

#### Room Capacity Management

- **Room Occupancy Tracking**: Keep count of the number of players in each room.
  
  ```python
  self.room_occupancy = {room_name: 0 for room_name in self.map_structure.keys()}
  ```

- **Capacity Check Before Movement**:

  ```python
  def can_enter_room(self, room_name):
      capacity = 10 if room_name == 'cafeteria' else 5
      return self.room_occupancy[room_name] < capacity
  ```

#### Movement Handling with Capacity Limits

- **Validate Move with Capacity**:

  ```python
  async def handle_move(self, player_id, destination):
      current_location = self.players[player_id]['location']
      if self.validate_move(current_location, destination) and self.can_enter_room(destination):
          # Update room occupancy
          self.room_occupancy[current_location] -= 1
          self.room_occupancy[destination] += 1
          # Update player location
          self.players[player_id]['location'] = destination
          await self.send_state_update(player_id)
          logging.info(f"Player {player_id} moved to {destination}.")
      else:
          await self.send_error(player_id, "Cannot move to that room. It may be full or inaccessible.")
  ```

### 3. Enhanced Error Handling

- **Detailed Error Messages**: Provide specific reasons for movement failures.

  ```python
  async def send_error(self, player_id, message):
      error_message = {
          "type": "error",
          "payload": {
              "message": message
          },
          "player_id": player_id
      }
      await self.players[player_id]['websocket'].send(json.dumps(error_message))
  ```

- **Logging Room States**: Log room occupancy for monitoring.

  ```python
  logging.info(f"Room occupancy updated: {self.room_occupancy}")
  ```

---

## Client Components

### 1. Enhanced Command-Line Interface

#### New Command: `map`

- **Purpose**: Display an ASCII representation of the map, showing room connections and highlighting the player's current location.

- **Implementation**:

  ```python
  def display_map(self, current_location):
      map_template = """
      [Cafeteria]---[Upper Engine]---[Reactor]
           |              |             |
      [MedBay]---[Engine Room]---[Security]
           |              |             |
      [Storage]---[Lower Engine]---[Electrical]
      """
      highlighted_map = map_template.replace(
          f'[{current_location}]',
          f'[*{current_location}*]'
      )
      print(highlighted_map)
  ```

- **Usage**:

  ```
  > map
  [*Cafeteria*]---[Upper Engine]---[Reactor]
       |              |             |
  [MedBay]---[Engine Room]---[Security]
       |              |             |
  [Storage]---[Lower Engine]---[Electrical]
  ```

#### Enhanced `look` Command

- **Additional Information**: Display room occupancy and indicate if adjacent rooms are full.

- **Implementation**:

  ```python
  def display_current_location(self, location, players_in_room, available_exits):
      print(f"Current Location: {location}")
      print(f"Players here: {players_in_room}/" +
            ("10" if location == "cafeteria" else "5"))
      print("Available Exits:")
      for exit in available_exits:
          status = "FULL" if not self.server_can_enter_room(exit) else ""
          print(f"  - {exit} {status}")
  ```

- **Usage**:

  ```
  > look
  Current Location: Cafeteria
  Players here: 3/10
  Available Exits:
    - Upper Engine
    - MedBay
    - Storage
  ```

  If a room is full:

  ```
  > look
  Current Location: Cafeteria
  Players here: 10/10
  Available Exits:
    - Upper Engine (FULL)
    - MedBay
    - Storage
  ```

### 2. Command Enhancements

- **Improved Command Parsing**: Handle new commands and options.

  ```python
  def parse_command(input_line):
      tokens = input_line.strip().split()
      command = tokens[0]
      args = tokens[1:]
      return command, args

  # Update command loop
  if command == "map":
      display_map(current_location)
  elif command == "look":
      display_current_location(location, players_in_room, available_exits)
  ```

---

## Communication Protocol

### 1. New Message Types

#### Error Messages (Server-to-Client)

- **Purpose**: Inform the client about errors such as full rooms or invalid commands.

- **Format**:

  ```json
  {
    "type": "error",
    "payload": {
      "message": "Cannot move to that room. It may be full or inaccessible."
    },
    "player_id": "player_1"
  }
  ```

### 2. Updated State Messages

- **Include Room Occupancy**: Provide information about the number of players in the current room.

- **Format**:

  ```json
  {
    "type": "state",
    "payload": {
      "location": "cafeteria",
      "players_in_room": 3,
      "available_exits": ["upper_engine", "medbay", "storage"],
      "room_capacity": 10,
      "exits_status": {
        "upper_engine": "available",
        "medbay": "full",
        "storage": "available"
      }
    },
    "player_id": "player_1"
  }
  ```

---

## Game Flow

### Movement with Capacity Limits

1. **Player Inputs Movement Command**:

   - E.g., `move upper_engine`

2. **Client Sends Action Message**:

   - The client sends a move request to the server.

3. **Server Validates Move and Capacity**:

   - Checks if `upper_engine` is adjacent and not at capacity.

4. **Server Updates Location or Sends Error**:

   - If successful, updates player's location and room occupancy.
   - If the room is full, sends an error message.

5. **Server Sends Updated State**:

   - Includes current location, players in room, and exits status.

6. **Client Updates HUD**:

   - Reflects the new state or displays an error message.

---

## Technical Requirements

### 1. Python Compatibility

- **Version**: Python 3.8 or higher.

### 2. Dependencies

- **Updated `requirements.txt`**:

  ```
  asyncio>=3.4.3
  websockets>=10.0
  pytest>=6.0.0
  ```

### 3. Testing

#### Room Capacity Tests

- **Test Movement to Full Room**:

  ```python
  def test_movement_to_full_room():
      game_server = GameServer()
      game_server.room_occupancy['upper_engine'] = 5  # Room is full
      can_enter = game_server.can_enter_room('upper_engine')
      assert can_enter == False
  ```

- **Test Room Occupancy Updates**:

  ```python
  def test_room_occupancy_updates():
      game_server = GameServer()
      player_id = 'test_player'
      game_server.players[player_id] = {'location': 'cafeteria'}
      game_server.room_occupancy['cafeteria'] = 1
      asyncio.run(game_server.handle_move(player_id, 'upper_engine'))
      assert game_server.room_occupancy['cafeteria'] == 0
      assert game_server.room_occupancy['upper_engine'] == 1
  ```

### 4. Logging

- **Log Room Occupancy Changes**:

  ```python
  logging.info(f"Player {player_id} moved to {destination}. Room occupancy: {self.room_occupancy}")
  ```

---

## Implementation Tips

### 1. Update Data Structures

- **Room Occupancy Dictionary**: Initialize and maintain a dictionary to track the number of players in each room.

  ```python
  self.room_occupancy = {room_name: 0 for room_name in self.map_structure}
  ```

### 2. Modify Movement Functions

- **Adjust `handle_move` Function**: Incorporate capacity checks and occupancy updates.

- **Ensure Atomicity**: Prevent race conditions by properly handling asynchronous updates.

### 3. Enhance Client Display Functions

- **Dynamic Exits Display**: Show whether adjacent rooms are full.

  ```python
  def display_available_exits(self, exits_status):
      for exit, status in exits_status.items():
          full_indicator = "(FULL)" if status == "full" else ""
          print(f"  - {exit} {full_indicator}")
  ```

### 4. Expand Testing

- **Concurrent Movement Tests**: Simulate multiple players attempting to enter the same room simultaneously.

- **Edge Case Handling**: Test scenarios where players disconnect unexpectedly.

---

## Conclusion

Version 1.1 enhances the gameplay experience by introducing:

- **Visual Map Representation**: Helps players navigate the game world more intuitively.
- **Room Capacity Limits**: Adds strategic depth by limiting room occupancy.
- **Improved Commands**: Offers players more information and control over their in-game actions.
- **Enhanced Error Handling**: Provides clearer feedback, improving user experience.

These improvements build upon the foundation laid in Version 1.0, setting the stage for more complex game mechanics in future updates.

---

## Next Steps

In the subsequent version, **Version 1.2**, the focus will be on:

- **Server Management**: Implementing server player limits and game start conditions.
- **Advanced State Management**: Enhancing player state tracking and room consistency.
- **Performance Optimizations**: Improving efficiency for better scalability.

---

# Appendix: Summary of Key Enhancements in Version 1.1

- **Map Visualization**:
  - ASCII map displayed via the `map` command.
  - Current location highlighted for easy reference.

- **Room Capacity System**:
  - Standard rooms: Max 5 players.
  - Cafeteria: Max 10 players.
  - Capacity checks before allowing movement.

- **Command Improvements**:
  - New `map` command for map display.
  - Enhanced `look` command with occupancy info and exit statuses.

- **Error Handling**:
  - Specific error messages for full rooms and invalid moves.
  - Error messages sent via a standardized protocol.

- **Server Enhancements**:
  - Room occupancy tracking.
  - Logging of room states and occupancy changes.

---

# Testing Guidelines

## 1. Map Structure Tests

- **Verify Room Connections**: Ensure all rooms are connected as per the specified map.

- **Test Map Display**:

  - Current location is correctly highlighted.
  - Connections between rooms are accurately represented.

## 2. Room Capacity Tests

- **Attempt to Enter Full Room**:

  - Player should receive an error message.
  - Player's location should remain unchanged.

- **Room Occupancy Updates**:

  - Occupancy counts should increment and decrement appropriately with player movements.

## 3. Command Functionality Tests

- **`map` Command**:

  - Displays the map correctly.
  - Highlights the player's current location.

- **`look` Command**:

  - Shows current room, number of players, and available exits.
  - Indicates if adjacent rooms are full.

## 4. Error Handling Tests

- **Invalid Movement**:

  - Moving to a non-adjacent room.
  - Moving to a room that doesn't exist.

- **Full Room Attempt**:

  - Verify error message is received.
  - Check that the player's state remains consistent.

## 5. Concurrency Tests

- **Simultaneous Movements**:

  - Multiple players attempting to enter the same room at once.
  - Ensure room capacity is not exceeded.

## 6. Logging Tests

- **Log Contents**:

  - Verify that logs include room occupancy updates.
  - Check for accurate timestamps and player IDs.

---

# Technical Notes

- **Thread Safety**: Ensure that updates to shared resources (like `room_occupancy`) are thread-safe in the asynchronous environment.

- **Performance Considerations**:

  - Optimize data structures for quick lookups.
  - Minimize blocking operations in asynchronous code.

- **Scalability**: Although the current player limit is 10, design the system to handle potential increases in future versions.

---

# Final Remarks

Implementing these enhancements will provide players with a more immersive and strategic gameplay experience. By carefully managing room capacities and improving navigational tools, players are encouraged to make thoughtful decisions, laying the groundwork for the complex interactions planned in future updates.

---

# Installation and Setup

## Dependencies

Ensure all dependencies are installed as per the updated `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

## Running the Client

```bash
python client.py
```

---

# Contact Information

For any issues or contributions, please contact the development team at [devteam@example.com](mailto:devteam@example.com).

# End of Specification