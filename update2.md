
This repository contains the detailed specifications for implementing a Text-Based Among Us game, divided into six progressive updates. Each update builds upon the previous ones, allowing for systematic development and testing.

# Update 2: Role Assignment and Basic Actions

## Overview

Building upon the foundational client-server architecture from Update 1, this update introduces core gameplay mechanics inspired by *Among Us*. Players are assigned specific roles—**Crewmate** or **Impostor**—which dictate their objectives and available actions within the game. Impostors aim to eliminate Crewmates without being detected, while Crewmates strive to identify and report any suspicious activities. A cooldown system is implemented to regulate the frequency of critical actions, ensuring balanced gameplay. An action priority system is also established to manage the execution order of simultaneous actions.

---

## Key Features

- **Role Assignment System**: Randomized distribution of Crewmate and Impostor roles to players.
- **Basic Actions**: Implementation of `kill` and `report` actions, specific to player roles.
- **Cooldown Management**: Enforcement of action cooldown periods to prevent action spamming.
- **Action Priority System**: Hierarchical handling of actions to resolve conflicts.
- **Role-Specific Command Interface**: Extension of the client interface to support role-dependent commands.

---

## Objectives

- Introduce player roles (**Crewmate** and **Impostor**) with distinct objectives.
- Implement basic actions like `kill` (Impostors) and `report` (Crewmates).
- Establish a cooldown system for regulating action frequency.
- Develop an action priority system to handle simultaneous actions effectively.
- Enhance the client interface to accommodate new role-specific commands.

---

## Detailed Specifications

### Server Components

#### 1. Role Assignment

- **Role Distribution Logic**:
  - Upon game start, the server randomly assigns roles to all connected players.
    - **Impostor Count**: Determine the number of Impostors based on total players (e.g., 1 Impostor for up to 5 players, 2 Impostors for 6-10 players).
  - **Confidentiality**: Role assignments are securely communicated only to the respective players.
- **Player Attribute Updates**:
  - Extend the player data model to include:
    - `role`: `"Crewmate"` or `"Impostor"`.
    - `status`: `"alive"` or `"dead"`.
    - `cooldown_timer`: Numerical value representing remaining cooldown time (Impostors only).

#### 2. Action Handling

- **Kill Action (Impostors Only)**:
  - **Command**: `kill <player_id>`.
  - **Conditions**:
    - The target player is in the same room and is `alive`.
    - The Impostor is not under cooldown.
  - **Execution**:
    - Update the target's `status` to `"dead"`.
    - Record the location of the body for potential reports.
    - Initiate the Impostor's cooldown timer.
  - **Notifications**:
    - Send a confirmation to the Impostor.
    - Do not notify other players immediately (maintain stealth).
- **Report Action (Crewmates Only)**:
  - **Command**: `report`.
  - **Conditions**:
    - A dead body is present in the current room.
  - **Execution**:
    - Transition the game to the **Discussion Phase**.
    - Notify all players of the reported body.
  - **Notifications**:
    - Broadcast a `report_event` to all players.

#### 3. Cooldown Management

- **Implementation**:
  - **Cooldown Duration**: Configurable parameter (e.g., 30 seconds).
  - **Tracking**:
    - Each Impostor has an individual `cooldown_timer`.
    - The timer decreases over time or through game ticks.
- **Enforcement**:
  - Prevent Impostors from performing `kill` actions while their `cooldown_timer` is active.
- **Client Feedback**:
  - Inform Impostors of their remaining cooldown time.

#### 4. Action Priority System

- **Priority Levels**:
  - **Highest**: `report`.
  - **Medium**: `kill`.
  - **Lowest**: `movement`, `non-critical actions`.
- **Conflict Resolution**:
  - Actions with higher priority preempt or override lower-priority actions.
  - If a `report` and a `kill` occur simultaneously, the `report` takes precedence.

### Client Components

#### 1. Command Interface

- **Role-Based Commands**:
  - **Impostors**:
    - `kill <player_id>`: Attempt to eliminate a player.
  - **Crewmates**:
    - `report`: Report a dead body in the current room.
- **Command Availability**:
  - Commands are context-sensitive and only available when conditions are met (e.g., `kill` command appears only when an Impostor is in the same room as another player).

#### 2. HUD Enhancements

- **Role Display**:
  - Upon game start, display the player's assigned role privately.
- **Cooldown Indicator**:
  - For Impostors, show a countdown timer after performing a `kill`.
- **Nearby Players List**:
  - Display a list of players in the same room with their `player_id`s.
  - Indicate which players can be targeted for actions.

### Communication Protocol

#### 1. Message Types

- **Action Messages** (`action`):
  - `kill`: Sent by Impostors attempting a kill.
  - `report`: Sent by Crewmates reporting a body.
- **Event Messages** (`event`):
  - `kill_event`: Server notification of a kill (to relevant players).
  - `report_event`: Server notification initiating the Discussion Phase.
- **State Updates** (`state_update`):
  - Inform players of changes in game state (e.g., deaths, cooldowns).

#### 2. Message Handling

- **Validation**:
  - Server validates all actions against game rules and player states.
- **Security**:
  - Prevent clients from sending unauthorized actions (e.g., a Crewmate sending a `kill` action).
- **Error Handling**:
  - Send informative error messages when actions fail (e.g., "You cannot kill while in cooldown.").

### Game Flow

#### 1. Free Roam Phase Updates

- **Player Actions**:
  - Players can move between rooms and perform role-specific actions.
- **Action Execution**:
  - Actions are processed based on their priority and validation checks.
- **Transition to Discussion Phase**:
  - Triggered by a successful `report` action.
  - Movement and actions are temporarily halted.
  - (Note: Discussion mechanics to be implemented in future updates.)

### Technical Requirements

#### 1. Action Validation

- **Server-Side Checks**:
  - Confirm the player's role and status before executing actions.
  - Ensure target players are valid and in correct states.

#### 2. Testing

- **Unit Tests**:
  - Test role assignment logic.
  - Validate action processing and priority handling.
  - Verify cooldown timers and enforcement.
- **Integration Tests**:
  - Simulate multiplayer scenarios to test interactions between players.

#### 3. Logging

- **Action Logging**:
  - Record all player actions with timestamps.
  - Log important game events for auditing and debugging purposes.

---

## Implementation Details

### Server-Side Data Structures

- **Player Object**:
  ```python
  class Player:
      def __init__(self, player_id, websocket):
          self.player_id = player_id
          self.websocket = websocket
          self.role = None  # 'Crewmate' or 'Impostor'
          self.status = 'alive'  # 'alive' or 'dead'
          self.location = 'cafeteria'
          self.cooldown_timer = 0  # Seconds remaining
  ```
- **Game State Management**:
  - Maintain a list or dictionary of all `Player` objects.
  - Track dead bodies and their locations for reporting.

### Cooldown Mechanics

- **Timer Implementation**:
  - Use asynchronous tasks or scheduled callbacks to decrement cooldown timers.
- **Action Blocking**:
  - Check `cooldown_timer` before allowing an Impostor to perform a `kill`.

### Action Priority Handling

- **Processing Queue**:
  - Implement an action queue where actions are sorted based on priority.
- **Atomic Actions**:
  - Ensure actions are processed atomically to prevent race conditions.

### Security Measures

- **Role Confidentiality**:
  - Only send role information to the respective player.
  - Encrypt or securely transmit sensitive data if necessary.

---

## User Experience Enhancements

- **Instructions**:
  - Provide clear instructions to players about their role and available commands.
- **Feedback**:
  - Immediate feedback on successful or failed actions.
- **Accessibility**:
  - Ensure that the client interface is user-friendly and accessible to all players.

---

## FAQ

### 1. Why use an Action Queue in a realtime system?

Despite being a realtime game, an Action Queue is necessary for several reasons:

- **Near-Simultaneous Actions**: Multiple players may perform actions within milliseconds of each other. The queue ensures these are processed in a consistent, deterministic order.

- **Network Latency**: Players have varying network conditions. Example:
  ```
  Player A (100ms latency): Initiates kill at t=0
  Player B (20ms latency): Initiates report at t=10
  ```
  Without a queue, B's action might reach the server first despite A acting earlier.

- **Action Priority**: Some actions (like reports) must take precedence over others (like kills). The queue enforces this hierarchy consistently.

Here's how the queue implementation might look:
```python
class ActionQueue:
    def __init__(self):
        self.actions = []
        
    def add_action(self, action):
        # Priority levels: report = 3, kill = 2, movement = 1
        priority = self.get_priority(action)
        timestamp = action.timestamp
        
        # Insert action in correct position based on priority and timestamp
        self.actions.append((priority, timestamp, action))
        self.actions.sort(reverse=True)  # Higher priority first
        
    async def process_queue(self):
        while self.actions:
            priority, timestamp, action = self.actions.pop(0)
            await self.execute_action(action)
```

The queue ensures:
- Actions are processed in a consistent, deterministic order
- Higher priority actions (like reports) take precedence
- Within the same priority level, actions are processed in chronological order

This helps maintain game integrity and prevents exploits that could arise from network timing differences or near-simultaneous actions.

---

## Conclusion

This expanded specification for Update 2 provides a comprehensive blueprint for introducing role assignments and basic actions into the game. By carefully implementing these features with attention to detail in action handling, cooldown management, and security, we set a strong foundation for more complex gameplay elements in future updates.


# Version 2.0: Core Role System
**Focus**: Basic role assignment and fundamental role-based actions

## Overview
This version implements the foundational role system, introducing the core distinction between Crewmates and Impostors. It focuses on basic role-specific actions while maintaining simplicity and stability.

## Key Features
1. Basic Role System
2. Basic Role Commands
3. Command Interface Updates
4. HUD Updates

## Detailed Specifications

### 1. Role Assignment System

#### Role Distribution Logic
```python:game.py
def assign_roles(self, players):
    total_players = len(players)
    impostor_count = 1 if total_players <= 5 else 2
    
    # Randomly select impostors
    impostor_ids = random.sample(list(players.keys()), impostor_count)
    
    # Assign roles to players
    for player_id in players:
        role = "Impostor" if player_id in impostor_ids else "Crewmate"
        players[player_id]["role"] = role
        players[player_id]["status"] = "alive"
```

#### Player Model Extension
```python:game.py
class Player:
    def __init__(self, player_id, websocket):
        self.player_id = player_id
        self.websocket = websocket
        self.role = None  # 'Crewmate' or 'Impostor'
        self.status = 'alive'  # 'alive' or 'dead'
        self.location = 'cafeteria'
```

### 2. Basic Role Commands

#### Kill Command (Impostors)
```python:game.py
async def handle_kill(self, player_id, target_id):
    if not self.validate_kill(player_id, target_id):
        await self.send_error(player_id, "Invalid kill attempt")
        return
        
    target = self.players[target_id]
    target["status"] = "dead"
    await self.send_state_update(player_id)
    
def validate_kill(self, killer_id, target_id):
    killer = self.players[killer_id]
    target = self.players[target_id]
    return (
        killer["role"] == "Impostor" and
        killer["status"] == "alive" and
        target["status"] == "alive" and
        killer["location"] == target["location"]
    )
```

#### Report Command (All Players)
```python:game.py
async def handle_report(self, player_id):
    if not self.validate_report(player_id):
        await self.send_error(player_id, "No body to report")
        return
        
    await self.broadcast_report(player_id)
    
def validate_report(self, player_id):
    location = self.players[player_id]["location"]
    return any(
        p["status"] == "dead" and p["location"] == location
        for p in self.players.values()
    )
```

### 3. Command Interface Updates

#### Role-Based Command Visibility
```python:game.py
def get_available_commands(self, player):
    commands = ["look", "move", "report"]
    if player["role"] == "Impostor":
        commands.append("kill")
    return commands
```

### 4. HUD Updates

#### State Message Extension
```python:game.py
async def send_state_update(self, player_id):
    player = self.players[player_id]
    state_message = {
        "type": "state",
        "payload": {
            "location": player["location"],
            "role": player["role"],
            "status": player["status"],
            "available_commands": self.get_available_commands(player),
            "players_in_room": self.get_players_in_room(player["location"])
        },
        "player_id": player_id
    }
    await player["websocket"].send(json.dumps(state_message))
```

## Testing Requirements

### Role Assignment Tests
```python:tests/test_roles.py
def test_role_distribution():
    game = GameServer()
    # Simulate 5 players
    players = {f"player_{i}": {} for i in range(5)}
    game.assign_roles(players)
    
    impostor_count = sum(1 for p in players.values() if p["role"] == "Impostor")
    assert impostor_count == 1

def test_kill_validation():
    game = GameServer()
    # Setup test scenario
    killer = {"role": "Impostor", "status": "alive", "location": "cafeteria"}
    target = {"role": "Crewmate", "status": "alive", "location": "cafeteria"}
    
    assert game.validate_kill(killer, target) == True
```

## Migration Guide

1. Update Player Model:
   - Add role and status fields
   - Initialize new players with these fields

2. Implement Role Assignment:
   - Add role distribution logic
   - Ensure secure role communication

3. Add Basic Commands:
   - Implement kill command
   - Implement report command
   - Add command validation

4. Update Client Interface:
   - Add role display
   - Show available commands based on role
   - Display player status

## Security Considerations

1. Role Information:
   - Only send role information to the respective player
   - Validate all role-based actions server-side

2. Action Validation:
   - Verify player role before allowing actions
   - Validate spatial requirements (same room for kills)
   - Ensure player status checks (alive/dead)

## Next Steps for Version 2.1

1. Implement action priority system
2. Add sophisticated body reporting
3. Enhance validation checks
4. Implement atomic action processing 


# Update 2.0.1: Basic Role System

## Overview
This update introduces the core role system with minimal complexity. Players are assigned either Crewmate or Impostor roles, with basic kill and report actions.

## Key Features
- Role assignment (Crewmate/Impostor)
- Basic kill action for Impostors
- Basic report action for finding dead players
- Simple player status tracking (alive/dead)

## Server Components

### Role Assignment
```python:game.py
class GameServer:
    def __init__(self):
        # Existing initialization...
        self.roles = {}  # player_id -> role
        self.player_status = {}  # player_id -> "alive" or "dead"

    def assign_roles(self):
        player_ids = list(self.players.keys())
        if not player_ids:
            return
            
        # Always assign one impostor
        impostor_id = random.choice(player_ids)
        
        for player_id in player_ids:
            self.roles[player_id] = "Impostor" if player_id == impostor_id else "Crewmate"
            self.player_status[player_id] = "alive"
```

### Kill Action
```python:game.py
    async def handle_kill(self, killer_id, target_id):
        # Basic validation
        if not self.validate_kill(killer_id, target_id):
            await self.send_error(killer_id, "Invalid kill attempt")
            return
            
        # Execute kill
        self.player_status[target_id] = "dead"
        await self.send_state_update(killer_id)
        await self.send_state_update(target_id)
    
    def validate_kill(self, killer_id, target_id):
        return (
            self.roles.get(killer_id) == "Impostor" and
            self.player_status[killer_id] == "alive" and
            self.player_status[target_id] == "alive" and
            self.players[killer_id]["location"] == self.players[target_id]["location"]
        )
```

### Report Action
```python:game.py
    async def handle_report(self, reporter_id):
        if not self.validate_report(reporter_id):
            await self.send_error(reporter_id, "Nothing to report")
            return
            
        # Start discussion (implementation in Update 3)
        await self.broadcast_message({
            "type": "event",
            "payload": {
                "event": "body_reported",
                "reporter": reporter_id,
                "location": self.players[reporter_id]["location"]
            }
        })
    
    def validate_report(self, reporter_id):
        reporter_location = self.players[reporter_id]["location"]
        return any(
            pid for pid, status in self.player_status.items()
            if status == "dead" and 
            self.players[pid]["location"] == reporter_location
        )
```

### State Updates
```python:game.py
    async def send_state_update(self, player_id):
        # Extend existing state update
        state_message = {
            "type": "state",
            "payload": {
                "location": self.players[player_id]["location"],
                "role": self.roles.get(player_id),
                "status": self.player_status.get(player_id),
                "players_in_room": self.room_occupancy[self.players[player_id]["location"]],
                "available_exits": self.map_structure.get(self.players[player_id]["location"], [])
            },
            "player_id": player_id
        }
        await self.players[player_id]["websocket"].send(json.dumps(state_message))
```

### Room State Display
```python:game.py
    def get_players_in_room(self, location):
        return {
            pid: self.player_status[pid]
            for pid, data in self.players.items()
            if data["location"] == location
        }
```

## Client Components

### Command Interface Updates
```python:game.py
class GameClient:
    async def send_commands(self):
        while self.running:
            input_line = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            
            command, args = self.parse_command(input_line)
            if command == "kill" and args:
                await self.send_kill_command(args[0])
            elif command == "report":
                await self.send_report_command()
            # ... existing commands ...
    
    async def send_kill_command(self, target_id):
        await self.send_action("kill", {"target": target_id})
    
    async def send_report_command(self):
        await self.send_action("report", {})
    
    async def send_action(self, action_type, payload):
        message = {
            "type": "action",
            "payload": {"action": action_type, **payload},
            "player_id": self.player_id
        }
        await self.websocket.send(json.dumps(message))
```

### Display Updates
```python:game.py
class GameClient:
    def display_current_location(self):
        if not self.location:
            print("Waiting for game state...")
            return

        print(f"\nCurrent Location: {self.location}")
        if hasattr(self, 'state_data'):
            role = self.state_data.get('role', 'Unknown')
            status = self.state_data.get('status', 'Unknown')
            print(f"Role: {role}")
            print(f"Status: {status}")
            
            # Show other players in room (needed for kill targeting)
            players_here = self.state_data.get('players_in_room', {})
            if players_here:
                print("\nPlayers in this room:")
                for pid, status in players_here.items():
                    if pid != self.player_id:  # Don't show self
                        print(f"  - Player {pid} ({status})")
```

## Testing Requirements

1. Role Assignment
   - Test single impostor assignment
   - Verify all players get roles
   - Check role persistence

2. Kill Action
   - Test valid kill (same room)
   - Test invalid kills (different room, non-impostor)
   - Verify status updates

3. Report Action
   - Test valid report (dead player in room)
   - Test invalid report (no dead players)
   - Verify event broadcast

## Migration Steps

1. Add role and status tracking to GameServer
2. Implement basic kill and report commands
3. Update state message format
4. Add role-specific command handling
5. Update client display

## Security Notes

- Role information is only sent to the respective player
- All actions are validated server-side
- Basic location and status checks prevent invalid actions

## Next Steps (for future updates)

1. Add cooldown system
2. Implement discussion phase
3. Add more sophisticated body handling
4. Enhance kill mechanics (range, animations) 

### Game State Notes
- Dead players can still see game state but cannot perform actions
- Role assignment happens at game start (implementation of game start trigger pending for future update)
- broadcast_message implementation will be added in Update 3 with discussion phase
- 

# Version 2.1: Action System Enhancement
**Focus**: Sophisticated action handling and priority system

## Overview
This version builds upon the basic role system by implementing a robust action handling system with priorities, enhanced validation, and improved state management.

## Key Features
1. Action Priority System
2. Enhanced Body Reporting
3. Improved Command Interface
4. State Management Updates

## Detailed Specifications

### 1. Action Priority System

#### Action Queue Implementation
```python:game.py
class ActionQueue:
    def __init__(self):
        self.actions = []
        self.priorities = {
            "report": 3,
            "kill": 2,
            "move": 1
        }
    
    def add_action(self, action):
        priority = self.priorities.get(action["type"], 0)
        timestamp = time.time()
        self.actions.append({
            "priority": priority,
            "timestamp": timestamp,
            "action": action
        })
        self.actions.sort(key=lambda x: (-x["priority"], x["timestamp"]))
    
    async def process_queue(self):
        while self.actions:
            action_data = self.actions.pop(0)
            await self.execute_action(action_data["action"])
```

#### Action Processing
```python:game.py
async def execute_action(self, action):
    action_type = action["type"]
    player_id = action["player_id"]
    
    if action_type == "report":
        await self.handle_report(player_id)
    elif action_type == "kill":
        await self.handle_kill(player_id, action["target_id"])
    elif action_type == "move":
        await self.handle_move(player_id, action["destination"])
```

### 2. Enhanced Body Reporting

#### Body State Management
```python:game.py
class Body:
    def __init__(self, player_id, location, timestamp):
        self.player_id = player_id
        self.location = location
        self.timestamp = timestamp
        self.reported = False

class GameServer:
    def __init__(self):
        self.bodies = {}  # player_id -> Body
    
    def create_body(self, player_id):
        location = self.players[player_id]["location"]
        self.bodies[player_id] = Body(player_id, location, time.time())
    
    async def handle_kill(self, killer_id, target_id):
        if await self.validate_kill(killer_id, target_id):
            self.players[target_id]["status"] = "dead"
            self.create_body(target_id)
            await self.notify_kill(killer_id, target_id)
```

#### Enhanced Report Validation
```python:game.py
def validate_report(self, reporter_id):
    reporter_location = self.players[reporter_id]["location"]
    unreported_bodies = [
        body for body in self.bodies.values()
        if body.location == reporter_location and not body.reported
    ]
    return bool(unreported_bodies)
```

### 3. Improved Command Interface

#### Context-Sensitive Commands
```python:game.py
def get_available_commands(self, player):
    base_commands = ["look", "move"]
    if player["status"] != "alive":
        return base_commands
        
    commands = base_commands + ["report"]
    if player["role"] == "Impostor":
        location = player["location"]
        if self.get_valid_targets(player["player_id"], location):
            commands.append("kill")
    
    return commands

def get_valid_targets(self, player_id, location):
    return [
        p_id for p_id, p in self.players.items()
        if p_id != player_id
        and p["location"] == location
        and p["status"] == "alive"
    ]
```

### 4. State Management

#### Room State Tracking
```python:game.py
class Room:
    def __init__(self, name):
        self.name = name
        self.players = set()
        self.bodies = set()
    
    def add_player(self, player_id):
        self.players.add(player_id)
    
    def remove_player(self, player_id):
        self.players.remove(player_id)
    
    def add_body(self, body_id):
        self.bodies.add(body_id)
    
    def get_state(self):
        return {
            "players": list(self.players),
            "bodies": list(self.bodies)
        }
```

## Testing Requirements

### Action Priority Tests
```python:tests/test_actions.py
async def test_action_priority():
    queue = ActionQueue()
    
    # Add actions in reverse priority order
    queue.add_action({"type": "move", "player_id": "p1"})
    queue.add_action({"type": "kill", "player_id": "p2"})
    queue.add_action({"type": "report", "player_id": "p3"})
    
    # First action should be report (highest priority)
    first_action = queue.actions[0]["action"]
    assert first_action["type"] == "report"

async def test_simultaneous_actions():
    game = GameServer()
    
    # Simulate near-simultaneous kill and report
    await game.process_action({"type": "kill", "player_id": "p1", "target_id": "p2"})
    await game.process_action({"type": "report", "player_id": "p3"})
    
    # Report should take precedence
    assert game.current_phase == "discussion"
```

## Migration Guide

1. Implement Action Queue:
   - Add ActionQueue class
   - Modify action handling to use queue
   - Update action processing logic

2. Enhance Body System:
   - Add Body class
   - Update kill handling
   - Improve report validation

3. Update State Management:
   - Add Room class
   - Implement room state tracking
   - Update state synchronization

## Security Considerations

1. Action Validation:
   - Verify action timestamps
   - Validate action sequences
   - Prevent action spoofing

2. State Consistency:
   - Ensure atomic state updates
   - Validate state transitions
   - Maintain action order

## Next Steps for Version 2.2

1. Implement cooldown system
2. Add advanced HUD features
3. Enhance security measures
4. Balance gameplay mechanics 



# Version 2.2: Cooldown and Polish
**Focus**: Cooldown system implementation and gameplay balance

## Overview
This version introduces a sophisticated cooldown system for actions, enhances the HUD with visual feedback, and implements additional security measures for a polished gameplay experience.

## Key Features
1. Cooldown System
2. Advanced HUD Features
3. Enhanced Security
4. Gameplay Balance

## Detailed Specifications

### 1. Cooldown System

#### Cooldown Management
```python:game.py
class CooldownManager:
    def __init__(self):
        self.cooldowns = {}  # player_id -> {action_type: timestamp}
        self.durations = {
            "kill": 30.0,  # seconds
            "report": 5.0
        }
    
    def start_cooldown(self, player_id, action_type):
        if player_id not in self.cooldowns:
            self.cooldowns[player_id] = {}
        self.cooldowns[player_id][action_type] = time.time()
    
    def get_remaining_cooldown(self, player_id, action_type):
        if player_id not in self.cooldowns:
            return 0
        
        last_use = self.cooldowns[player_id].get(action_type, 0)
        elapsed = time.time() - last_use
        duration = self.durations[action_type]
        
        return max(0, duration - elapsed)
    
    def is_action_available(self, player_id, action_type):
        return self.get_remaining_cooldown(player_id, action_type) == 0
```

#### Action Integration
```python:game.py
class GameServer:
    def __init__(self):
        self.cooldown_manager = CooldownManager()
    
    async def handle_kill(self, killer_id, target_id):
        if not self.cooldown_manager.is_action_available(killer_id, "kill"):
            await self.send_error(killer_id, "Kill action is on cooldown")
            return
            
        if await self.validate_kill(killer_id, target_id):
            self.cooldown_manager.start_cooldown(killer_id, "kill")
            await self.execute_kill(killer_id, target_id)
```

### 2. Advanced HUD Features

#### Enhanced State Updates
```python:game.py
async def send_state_update(self, player_id):
    player = self.players[player_id]
    cooldowns = {
        action: self.cooldown_manager.get_remaining_cooldown(player_id, action)
        for action in ["kill", "report"]
    }
    
    state_message = {
        "type": "state",
        "payload": {
            "location": player["location"],
            "role": player["role"],
            "status": player["status"],
            "cooldowns": cooldowns,
            "available_actions": self.get_available_actions(player_id),
            "nearby_players": self.get_nearby_players(player_id),
            "room_state": self.get_room_state(player["location"])
        },
        "player_id": player_id
    }
    await player["websocket"].send(json.dumps(state_message))
```

#### Action Availability Display
```python:game.py
def get_available_actions(self, player_id):
    player = self.players[player_id]
    actions = []
    
    for action in ["move", "report", "kill"]:
        if self.is_action_valid(player_id, action):
            cooldown = self.cooldown_manager.get_remaining_cooldown(player_id, action)
            actions.append({
                "type": action,
                "available": cooldown == 0,
                "cooldown": cooldown
            })
    
    return actions
```

### 3. Enhanced Security

#### Action Validation
```python:game.py
class ActionValidator:
    def __init__(self, game_server):
        self.game = game_server
    
    def validate_action(self, player_id, action_type, **kwargs):
        if not self.validate_player_state(player_id):
            return False
            
        if not self.game.cooldown_manager.is_action_available(player_id, action_type):
            return False
            
        validation_method = getattr(self, f"validate_{action_type}", None)
        if validation_method:
            return validation_method(player_id, **kwargs)
            
        return False
    
    def validate_player_state(self, player_id):
        player = self.game.players.get(player_id)
        return player and player["status"] == "alive"
```

### 4. Gameplay Balance

#### Dynamic Cooldown Adjustment
```python:game.py
class DynamicCooldownManager(CooldownManager):
    def __init__(self):
        super().__init__()
        self.base_durations = self.durations.copy()
    
    def adjust_cooldowns(self, player_count):
        # Adjust kill cooldown based on player count
        self.durations["kill"] = self.base_durations["kill"] * (
            0.8 if player_count <= 4 else 
            1.0 if player_count <= 7 else 
            1.2
        )
```

## Testing Requirements

### Cooldown Tests
```python:tests/test_cooldowns.py
async def test_cooldown_system():
    game = GameServer()
    player_id = "test_player"
    
    # Test initial cooldown state
    assert game.cooldown_manager.is_action_available(player_id, "kill")
    
    # Test cooldown after action
    await game.handle_kill(player_id, "target")
    assert not game.cooldown_manager.is_action_available(player_id, "kill")
    
    # Test cooldown expiration
    await asyncio.sleep(31)  # Wait for cooldown
    assert game.cooldown_manager.is_action_available(player_id, "kill")
```

## Migration Guide

1. Implement Cooldown System:
   - Add CooldownManager class
   - Integrate cooldowns with actions
   - Update state management

2. Enhance HUD:
   - Update state message format
   - Add cooldown display
   - Improve action availability feedback

3. Implement Security Measures:
   - Add ActionValidator
   - Enhance state validation
   - Implement anti-cheat measures

## Security Considerations

1. Cooldown Enforcement:
   - Server-side cooldown validation
   - Prevent client-side cooldown manipulation
   - Secure cooldown state storage

2. Action Validation:
   - Comprehensive state validation
   - Secure action processing
   - Anti-spam measures

## Performance Optimizations

1. Cooldown Calculations:
   - Cache cooldown states
   - Optimize timestamp comparisons
   - Efficient state updates

## Conclusion

Version 2.2 completes the core gameplay mechanics with:
- Robust cooldown system
- Enhanced user feedback
- Improved security measures
- Balanced gameplay mechanics

The system is now ready for additional feature development in future versions. 