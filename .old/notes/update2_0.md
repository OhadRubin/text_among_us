# Update 2.0: Core Role System Implementation

## Overview

This update implements the foundational role system and basic actions for the Text-Based Among Us game. It introduces the core distinction between Crewmates and Impostors, along with essential role-specific actions.

## Key Features

1. Basic Role Assignment System
2. Core Role-Based Actions (Kill/Report)
3. Player Status Tracking
4. Enhanced State Management
5. Basic Command Interface

## Detailed Specifications

### 1. Role Assignment System

#### Role Distribution Logic
```python:game.py
class GameServer:
    def __init__(self):
        # Existing initialization...
        self.roles = {}  # player_id -> role
        self.player_status = {}  # player_id -> "alive" or "dead"
        self.bodies = {}  # player_id -> location

    def assign_roles(self):
        player_ids = list(self.players.keys())
        if not player_ids:
            return
            
        # Determine number of impostors based on player count
        total_players = len(player_ids)
        impostor_count = 1 if total_players <= 5 else 2
        
        # Randomly select impostors
        impostor_ids = random.sample(player_ids, impostor_count)
        
        # Assign roles to all players
        for player_id in player_ids:
            self.roles[player_id] = "Impostor" if player_id in impostor_ids else "Crewmate"
            self.player_status[player_id] = "alive"
```

### 2. Core Actions Implementation

#### Kill Action (Impostor Only)
```python:game.py
    async def handle_kill(self, killer_id, target_id):
        if not self.validate_kill(killer_id, target_id):
            await self.send_error(killer_id, "Invalid kill attempt")
            return
            
        # Execute kill
        self.player_status[target_id] = "dead"
        self.bodies[target_id] = self.players[target_id]["location"]
        
        # Update relevant players
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

#### Report Action (All Players)
```python:game.py
    async def handle_report(self, reporter_id):
        if not self.validate_report(reporter_id):
            await self.send_error(reporter_id, "Nothing to report")
            return
            
        # Broadcast report event
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
            location == reporter_location
            for body_id, location in self.bodies.items()
        )
```

### 3. Enhanced State Management

#### State Updates
```python:game.py
    async def send_state_update(self, player_id):
        state_message = {
            "type": "state",
            "payload": {
                "location": self.players[player_id]["location"],
                "role": self.roles.get(player_id),
                "status": self.player_status.get(player_id),
                "players_in_room": self.get_players_in_room(self.players[player_id]["location"]),
                "available_exits": self.map_structure.get(self.players[player_id]["location"], [])
            },
            "player_id": player_id
        }
        await self.players[player_id]["websocket"].send(json.dumps(state_message))

    def get_players_in_room(self, location):
        return {
            pid: {
                "status": self.player_status[pid],
                "role": self.roles[pid] if pid == self.player_id else "unknown"
            }
            for pid, data in self.players.items()
            if data["location"] == location
        }
```

### 4. Command Interface

#### Client-Side Command Processing
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
            elif command == "move" and args:
                await self.send_move_command(args[0])
            elif command == "look":
                self.display_current_location()
            elif command == "help":
                self.display_help()
            else:
                print("Unknown command. Type 'help' for available commands.")

    async def send_kill_command(self, target_id):
        await self.send_action("kill", {"target": target_id})
    
    async def send_report_command(self):
        await self.send_action("report", {})
```

### 5. Display Updates

#### Enhanced Location Display
```python:game.py
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
            
            players_here = self.state_data.get('players_in_room', {})
            if players_here:
                print("\nPlayers in this room:")
                for pid, data in players_here.items():
                    if pid != self.player_id:
                        print(f"  - Player {pid} ({data['status']})")
```

## Testing Requirements

### 1. Role Assignment Tests
```python:tests/test_roles.py
def test_role_distribution():
    game = GameServer()
    # Test with 5 players
    players = {f"player_{i}": {} for i in range(5)}
    game.assign_roles(players)
    
    impostor_count = sum(1 for p in players.values() if p["role"] == "Impostor")
    assert impostor_count == 1

    # Test with 8 players
    players = {f"player_{i}": {} for i in range(8)}
    game.assign_roles(players)
    
    impostor_count = sum(1 for p in players.values() if p["role"] == "Impostor")
    assert impostor_count == 2
```

### 2. Action Tests
```python:tests/test_actions.py
async def test_kill_action():
    game = GameServer()
    killer_id = "impostor"
    target_id = "crewmate"
    
    # Setup test scenario
    game.roles[killer_id] = "Impostor"
    game.roles[target_id] = "Crewmate"
    game.player_status[killer_id] = "alive"
    game.player_status[target_id] = "alive"
    game.players[killer_id] = {"location": "cafeteria"}
    game.players[target_id] = {"location": "cafeteria"}
    
    # Test kill action
    await game.handle_kill(killer_id, target_id)
    assert game.player_status[target_id] == "dead"
    assert target_id in game.bodies

async def test_report_action():
    game = GameServer()
    reporter_id = "reporter"
    dead_id = "dead_player"
    
    # Setup test scenario
    game.players[reporter_id] = {"location": "cafeteria"}
    game.bodies[dead_id] = "cafeteria"
    
    # Test report action
    assert game.validate_report(reporter_id)
```

## Migration Guide

1. Update Server Initialization:
   - Add role tracking
   - Add player status tracking
   - Add body tracking

2. Implement Role Assignment:
   - Add role distribution logic
   - Update player initialization

3. Add Core Actions:
   - Implement kill action
   - Implement report action
   - Add validation logic

4. Update State Management:
   - Extend state updates
   - Add role-specific information
   - Update display logic

5. Enhance Client Interface:
   - Add new commands
   - Update display methods
   - Add role-specific feedback

## Security Considerations

1. Role Information:
   - Only send role information to the respective player
   - Validate all role-based actions server-side

2. Action Validation:
   - Verify player roles before allowing actions
   - Validate spatial requirements (same room for kills)
   - Ensure player status checks (alive/dead)

3. State Management:
   - Validate all state transitions
   - Protect sensitive information
   - Prevent unauthorized state modifications


## Notes

- Dead players can still see game state but cannot perform actions
- Role assignment happens at game start
- Body locations are tracked for reporting
- Players can only see roles of other players during specific game phases