# game_server.py

import asyncio
import websockets
import json
import logging
import random
from collections import defaultdict
from pydantic import BaseModel
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pydantic import ValidationError
from enum import Enum

# Simplified Game Server for an Among Us-like game with an event-based architecture

PLAYER_NAMES = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Mallory", "Trent", "Frank", "Grace", "Henry", "Ivy", "Jack", "Kelly", "Luna", "Max", "Nina", "Oscar", "Penny", "Quinn", "Ruby", "Sam"]


class EventManager:
    """Manages event registration and dispatching."""

    def __init__(self):
        self.listeners = defaultdict(list)

    def register(self, event_type, callback):
        """Registers a callback for a specific event type."""
        self.listeners[event_type].append(callback)

    async def dispatch(self, event_type, data):
        """Dispatches an event to all registered callbacks."""
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                await callback(data)


def event(event_type):
    def decorator(func):
        func._event_type = event_type
        return func

    return decorator


class TaskState(Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE" 
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"

    def __str__(self):
        return self.value
    
    def to_json(self):
        return self.value


class PlayerRole(Enum):
    IMPOSTOR = "Impostor"
    CREWMATE = "Crewmate"

    def __str__(self):
        return self.value
    
    def to_json(self):
        return self.value

class Task(BaseModel):
    """Represents a task in the game."""
    name: str
    room: str
    turns_remaining: int
    state: TaskState = TaskState.INACTIVE
    og_number_of_turns: Optional[int] = None

    def start(self) -> bool:
        self.og_number_of_turns = self.turns_remaining
        if self.state == TaskState.INACTIVE:
            self.state = TaskState.ACTIVE
            return True
        return False

    def tick(self) -> bool:
        if self.state == TaskState.ACTIVE:
            self.turns_remaining -= 1
            if self.turns_remaining <= 0:
                self.state = TaskState.COMPLETED
                return True
        return False

    def interrupt(self) -> bool:
        if self.state == TaskState.ACTIVE:
            self.state = TaskState.INTERRUPTED
            self.turns_remaining = self.og_number_of_turns
            return True
        return False


from typing import Any
class Player(BaseModel):
    """Represents a player in the game."""
    id: str
    websocket: Any
    location: str = "cafeteria"
    role: PlayerRole = PlayerRole.CREWMATE
    is_alive: bool = True
    emergency_meetings_left: int = 1
    tasks: Optional[Dict[str, Task]] = None
    active_task: Optional[str] = None
    movement_locked: bool = False  # Added movement_locked attribute

    def assign_tasks(self):
        if self.role == PlayerRole.CREWMATE:
            # this is just for now...
            self.tasks = {f"Task 1": Task(name=f"Task 1", room="cafeteria", turns_remaining=1)}
        else: # Impostor
            self.tasks = dict()


@dataclass
class GameState:
    """Holds the current state of the game."""
    players: Dict[str, Player] = field(default_factory=dict)
    bodies: Dict[str, str] = field(default_factory=dict)
    map_layout: Dict[str, List[str]] = field(default_factory=dict)
    phase: str = "free_roam"
    votes: Dict[str, str] = field(default_factory=dict)
    game_started: bool = False
    min_players: int = 3
    impostor_ratio: float = 0.2
    discussion_duration: int = 60
    voting_duration: int = 30
    max_emergency_meetings: int = 1
    completed_tasks: int = 0
    task_tick_interval: int = 5
    logger: logging.Logger = field(init=False)
    disconnected_players: Dict[str, Player] = field(
        default_factory=dict
    )  # To handle disconnected players

    def __post_init__(self):
        self.logger = self.setup_logger()
        self.map_layout = self.initialize_map()

    def setup_logger(self):
        """Sets up the logger for the server."""
        logger = logging.getLogger("GameServer")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def initialize_map(self):
        """Initializes the game map layout."""
        return {
            "cafeteria": ["upper_engine", "medbay", "storage"],
            "upper_engine": ["cafeteria", "reactor", "engine_room"],
            "reactor": ["upper_engine", "security"],
            "security": ["reactor", "engine_room", "electrical"],
            "electrical": ["security", "lower_engine"],
            "lower_engine": ["electrical", "engine_room", "storage"],
            "engine_room": ["upper_engine", "security", "lower_engine", "medbay"],
            "storage": ["cafeteria", "lower_engine"],
            "medbay": ["cafeteria", "engine_room"],
        }


class GameEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, PlayerRole):
            return obj.value
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class GameServer:
    """Main game server class that orchestrates the game."""

    def __init__(self):
        self.event_manager = EventManager()
        self.state = GameState()
        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Registers event handlers using the @event decorator."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_event_type"):
                event_type = attr._event_type
                self.event_manager.register(event_type, attr)

    async def start_server(self):
        """Starts the WebSocket server."""
        server = await websockets.serve(self.handle_connection, "localhost", 8765)
        self.state.logger.info("Server started on ws://localhost:8765")
        await server.wait_closed()

    async def handle_connection(self, websocket, path):
        """Handles a new player connection."""
        player_id = None
        try:
            # Check if server is full
            if len(self.state.players) >= len(PLAYER_NAMES):
                await websocket.send(
                    json.dumps({"type": "error", "message": "Server is full"})
                )
                return

            # Generate player ID first
            player_id = PLAYER_NAMES[len(self.state.players)]
            # If the player is reconnecting
            # if player_id in self.state.disconnected_players:
            #     player = self.state.disconnected_players[player_id]
            #     player.websocket = websocket  # Update websocket
            #     self.state.players[player_id] = player
            #     del self.state.disconnected_players[player_id]
            #     self.state.logger.info(f"Player {player_id} reconnected.")
            #     # Send task list update
            #     # TODO: fix me 
            #     # await self.send_task_list_update(player_id)
            # else:
            if True:
                player = Player(id=player_id, websocket=websocket)
                self.state.players[player_id] = player

                # Send initial welcome message
                await self.send_message(
                    player_id, {"type": "welcome", "player_id": player_id}
                )

                # Dispatch player_connected event
                await self.event_manager.dispatch(
                    "player_connected", {"player_id": player_id}
                )

                # Check if game should start
                if (
                    len(self.state.players) >= self.state.min_players
                    and not self.state.game_started
                ):
                    # Assign tasks and roles to players
                    self.assign_roles()
                    self.state.game_started = True
                    self.state.logger.info(
                        f"Game started with {len(self.state.players)} players."
                    )
                    await self.broadcast({"type": "game_started"})

                    # self.assign_tasks_to_players()

                    # # Send task list updates to all players
                    # for pid in self.state.players:
                    #     await self.send_task_list_update(pid)

                self.state.logger.info(f"Player {player_id} connected.")

                # Send initial state update
                await self.send_state_update(player_id)

            # Handle incoming messages
            async for message_str in websocket:
                try:
                    message = json.loads(message_str)
                    action = message.get("action")
                    if action:
                        message["player_id"] = player_id  # Include player_id in message
                        await self.event_manager.dispatch(f"action_{action}", message)
                    else:
                        await self.send_error(player_id, "Invalid action.")
                except json.JSONDecodeError:
                    await self.send_error(player_id, "Invalid message format.")

        except websockets.exceptions.ConnectionClosedError:
            self.state.logger.warning(f"Player {player_id} disconnected unexpectedly.")
        except Exception as e:
            import traceback
            self.state.logger.error(
                f"Error handling connection: {str(e)}\nException type: {type(e).__name__}\nTraceback: {traceback.format_exc()}"
            )
        finally:
            if player_id in self.state.players:
                await self.event_manager.dispatch(
                    "player_disconnected", {"player_id": player_id}
                )

    # Event Handlers
    @event("player_connected")
    async def on_player_connected(self, data):
        """Handles a new player connection event."""
        player_id = data["player_id"]
        player = self.state.players[player_id]
        await self.broadcast(
            {
                "type": "player_connected",
                "player_id": player_id,
                "location": player.location,
            }
        )

    @event("player_disconnected")
    async def on_player_disconnected(self, data):
        """Handles a player disconnection event."""
        player_id = data["player_id"]
        if player_id in self.state.players:
            # Interrupt player's task
            # await self.interrupt_player_task(player_id, reason="disconnect")
            # player = self.state.players[player_id]
            # # Store player's tasks in disconnected_players
            # self.state.disconnected_players[player_id] = player
            del self.state.players[player_id]
            await self.broadcast(
                {
                    "type": "player_disconnected",
                    "player_id": player_id,
                }
            )
            self.state.logger.info(f"Player {player_id} disconnected.")

    @event("action_move")
    async def on_action_move(self, data):
        """Handles player movement actions."""
        player_id = data["player_id"]
        destination = data.get("destination")
        player = self.state.players[player_id]
        if player.movement_locked:
            await self.send_error(player_id, "Cannot move while performing a task.")
            return
        if destination in self.state.map_layout.get(player.location, []):
            old_location = player.location
            player.location = destination

            # Broadcast movement to everyone
            await self.broadcast(
                {
                    "type": "player_moved",
                    "player_id": player_id,
                    "from": old_location,
                    "to": destination,
                }
            )

            # Send state updates to all players in both old and new locations
            for pid, p in self.state.players.items():
                if p.location in [old_location, destination]:
                    await self.send_state_update(pid)
        else:
            await self.send_error(player_id, "Invalid move.")

    @event("action_kill")
    async def on_action_kill(self, data):
        """Handles kill actions initiated by Impostors."""
        killer_id = data["player_id"]
        target_id = data.get("target")
        killer = self.state.players.get(killer_id)
        target = self.state.players.get(target_id)
        if (
            killer
            and target
            and killer.role == PlayerRole.IMPOSTOR
            and killer.is_alive
            and target.is_alive
            and killer.location == target.location
        ):
            target.is_alive = False
            self.state.bodies[target_id] = target.location
            await self.broadcast(
                {
                    "type": "player_killed",
                    "killer": killer_id,
                    "victim": target_id,
                    "location": target.location,
                }
            )
            await self.send_state_update(target_id)
        else:
            await self.send_error(killer_id, "Invalid kill attempt.")

    @event("action_report")
    async def on_action_report(self, data):
        """Handles body report actions."""
        reporter_id = data["player_id"]
        reporter = self.state.players[reporter_id]
        location = reporter.location
        if any(body_loc == location for body_loc in self.state.bodies.values()):
            await self.start_discussion_phase()
        else:
            await self.send_error(reporter_id, "No bodies to report here.")

    @event("action_vote")
    async def on_action_vote(self, data):
        """Handles voting actions during the voting phase."""
        player_id = data["player_id"]
        voted_player = data.get("vote")
        if player_id not in self.state.votes:
            self.state.votes[player_id] = voted_player
            await self.send_message(player_id, {"type": "vote_received"})
            if len(self.state.votes) >= len(
                [p for p in self.state.players.values() if p.is_alive]
            ):
                await self.tally_votes()
        else:
            await self.send_error(player_id, "You have already voted.")

    @event("action_call_meeting")
    async def on_action_call_meeting(self, data):
        """Handles emergency meeting calls."""
        player_id = data["player_id"]
        player = self.state.players[player_id]

        # Check if player has meetings left
        if player.emergency_meetings_left > 0:
            # Decrement available meetings
            player.emergency_meetings_left -= 1

            # Send notification about who called the meeting
            await self.broadcast({
                "type": "emergency_meeting_called",
                "player_id": player_id
            })

            # Start discussion phase
            await self.start_discussion_phase()
        else:
            await self.send_error(player_id, "No emergency meetings left.")

    @event("action_chat")
    async def on_action_chat(self, data):
        """Handles chat messages during the discussion phase."""
        player_id = data["player_id"]
        message_text = data.get("message")
        player = self.state.players[player_id]

        if self.state.phase == "discussion":
            if not player.is_alive:
                message_text = f"[GHOST] {message_text}"
                # Create separate messages for living and dead players
                ghost_message = {
                    "type": "chat_message",
                    "player_id": player_id,
                    "message": message_text,
                }
                # Only send ghost messages to dead players
                for pid, p in self.state.players.items():
                    if not p.is_alive:
                        await self.send_message(pid, ghost_message)
            else:
                # Living players' messages go to everyone but without ghost tag
                await self.broadcast({
                    "type": "chat_message",
                    "player_id": player_id,
                    "message": message_text,
                })
        else:
            await self.send_error(player_id, "Cannot chat now.")

    # Helper methods
    def assign_roles(self):
        """Randomly assigns roles to players at the start of the game."""
        player_ids = list(self.state.players.keys())
        impostor_count = max(1, int(len(player_ids) * self.state.impostor_ratio))
        impostor_ids = random.sample(player_ids, impostor_count)
        for player_id in player_ids:
            player = self.state.players[player_id]
            player.role = PlayerRole.IMPOSTOR if player_id in impostor_ids else PlayerRole.CREWMATE
            asyncio.create_task(self.send_state_update(player_id))

    async def start_discussion_phase(self):
        """Initiates the discussion phase after a body is reported or a meeting is called."""
        self.state.phase = "discussion"
        self.state.votes.clear()

        # Interrupt tasks for all players
        for player_id, player in self.state.players.items():
            await self.interrupt_player_task(player_id, reason="discussion")

        # Send state updates without waiting
        for player_id, player in self.state.players.items():
            location = player.location
            message = {
                "type": "phase_change",
                "phase": "discussion",
                "duration": self.state.discussion_duration,
                # Include all state data
                "location": location,
                "players_in_room": [pid for pid, p in self.state.players.items() if p.location == location],
                "available_exits": self.state.map_layout.get(location, []),
                "role": player.role,
                "status": "alive" if player.is_alive else "dead",
                "bodies_in_room": [pid for pid, loc in self.state.bodies.items() if loc == location],
                "alive_players": [pid for pid, p in self.state.players.items() if p.is_alive],
                "emergency_meetings_left": player.emergency_meetings_left,
            }
            asyncio.create_task(self.send_message(player_id, message))

        # Start phase timer in a separate task
        asyncio.create_task(self.run_discussion_timer())

    async def run_discussion_timer(self):
        """Runs the discussion phase timer in a separate task."""
        await asyncio.sleep(self.state.discussion_duration)
        await self.start_voting_phase()

    async def start_voting_phase(self):
        """Initiates the voting phase after the discussion phase ends."""
        self.state.phase = "voting"
        await self.broadcast(
            {
                "type": "phase_change",
                "phase": "voting",
                "duration": self.state.voting_duration,
            }
        )
        await asyncio.sleep(self.state.voting_duration)
        await self.tally_votes()
        self.state.phase = "free_roam"

    async def tally_votes(self):
        """Tallies votes and processes ejection if necessary."""
        vote_counts = {}
        for vote in self.state.votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        if vote_counts:
            max_votes = max(vote_counts.values())
            # select all players with max votes... wait, there could be a tie?
            candidates = [
                pid for pid, count in vote_counts.items() if count == max_votes 
            ]

            if len(candidates) == 1 and candidates[0] != "skip":
                # Interrupt ejected player's task if any
                ejected_player_id = candidates[0]
                await self.interrupt_player_task(ejected_player_id, reason="death")
                ejected_player = self.state.players[ejected_player_id]
                ejected_player.is_alive = False
                await self.broadcast(
                    {
                        "type": "player_ejected",
                        "player_id": ejected_player_id,
                        "role": ejected_player.role,
                    }
                )
            else:
                await self.broadcast(
                    {"type": "no_ejection", "message": "No one was ejected."}
                )
        else:
            await self.broadcast({"type": "no_ejection", "message": "No votes cast."})
        self.state.votes.clear()

    async def send_state_update(self, player_id):
        """Sends the current game state to a specific player."""
        player = self.state.players[player_id]
        location = player.location
        available_exits = self.state.map_layout.get(location, [])
        players_in_room = [
            pid for pid, p in self.state.players.items() if p.location == location
        ]
        bodies_in_room = [
            pid for pid, loc in self.state.bodies.items() if loc == location
        ]
        alive_players = [pid for pid, p in self.state.players.items() if p.is_alive]
        state = {
            "type": "state_update",
            "location": location,
            "players_in_room": players_in_room,
            "available_exits": available_exits,
            "role": player.role,
            "status": "alive" if player.is_alive else "dead",
            "bodies_in_room": bodies_in_room,
            "alive_players": alive_players,
            "emergency_meetings_left": player.emergency_meetings_left,
        }
        await self.send_message(player_id, state)

    async def send_error(self, player_id, message):
        """Sends an error message to a specific player."""
        await self.send_message(player_id, {"type": "error", "message": message})

    async def send_message(self, player_id: str, message_dict: dict):
        """Sends a message to a specific player."""
        player = self.state.players[player_id]
        try:
            await player.websocket.send(json.dumps(message_dict, cls=GameEncoder))
        except websockets.exceptions.ConnectionClosedError:
            self.state.logger.warning(
                f"Could not send message to {player_id}; connection closed."
            )
        except Exception as e:
            self.state.logger.error(f"Error sending message to {player_id}: {str(e)}")

    async def broadcast(self, message):
        """Broadcasts a message to all connected players."""
        message_str = json.dumps(message, cls=GameEncoder)
        disconnected_players = []

        players_copy = dict(self.state.players)

        for player_id, player in players_copy.items():
            try:
                await player.websocket.send(message_str)
            except websockets.exceptions.ConnectionClosedError:
                disconnected_players.append(player_id)
                self.state.logger.warning(
                    f"Player {player_id} disconnected during broadcast"
                )
            except Exception as e:
                self.state.logger.error(f"Error broadcasting to {player_id}: {str(e)}")

        # Remove disconnected players
        for player_id in disconnected_players:
            await self.event_manager.dispatch(
                "player_disconnected", {"player_id": player_id}
            )

    async def send_task_list_update(self, player_id: str):
        """Sends the task list update to the player."""
        player = self.state.players[player_id]
        tasks_list = []
        for task_name, task in player.tasks.items():
            task_info = {
                "name": task.name,
                "complete": task.state == TaskState.COMPLETED,
                "active": task.state == TaskState.ACTIVE,
                "turns_required": task.turns_required,
                "turns_remaining": task.turns_remaining,
                "room": task.room,
            }
            tasks_list.append(task_info)
        global_progress = self.calculate_global_progress()
        message = {
            "type": "state_update",
            "tasks": tasks_list,
            "global_progress": global_progress,
        }
        await self.send_message(player_id, message)

    def calculate_global_progress(self) -> float:
        """Calculates the global task completion progress."""
        completed_tasks = 0
        total_tasks = self.state.total_crewmate_tasks
        # Include tasks from connected players
        for player in self.state.players.values():
            if player.role == PlayerRole.CREWMATE:
                for task in player.tasks.values():
                    if task.state == TaskState.COMPLETED:
                        completed_tasks += 1
        # Include tasks from disconnected players
        # for player in self.state.disconnected_players.values():
        #     if player.role == PlayerRole.CREWMATE:
        #         for task in player.tasks.values():
        #             if task.state == TaskState.COMPLETED:
        #                 completed_tasks += 1
        if total_tasks == 0:
            return 0.0
        progress = completed_tasks / total_tasks
        return round(progress, 3)

    @event("action_task")
    async def on_action_task(self, data: dict):
        """Handles player attempting to start a task."""
        player_id = data["player_id"]
        task_name = data["task_name"]

        valid, reason = self.validate_task_start(player_id, task_name)
        if not valid:
            await self.send_error(player_id, reason)
            return

        # Start the task
        player = self.state.players[player_id]
        task = player.tasks[task_name]
        started = task.start()
        if not started:
            await self.send_error(player_id, "Task could not be started")
            return

        player.active_task = task_name
        player.movement_locked = True  # Prevent movement

        # Send task_started message to player
        await self.send_message(
            player_id,
            {
                "type": "task_started",
                "task_name": task_name,
                "turns_remaining": task.turns_remaining,
            },
        )

        # Broadcast task_progress with status="started"
        await self.broadcast(
            {
                "type": "task_progress",
                "player_id": player_id,
                "task_name": task_name,
                "status": "started",
                "turns_remaining": task.turns_remaining,
            }
        )

    async def send_task_list_update(self, player_id: str):
        """Sends the task list update to the player."""
        player = self.state.players[player_id]
        tasks_list = []
        for task_name, task in player.tasks.items():
            task_info = {
                "name": task.name,
                "complete": task.state == TaskState.COMPLETED,
                "active": task.state == TaskState.ACTIVE,
                "turns_required": task.turns_required,
                "turns_remaining": task.turns_remaining,
                "room": task.room,
            }
            tasks_list.append(task_info)
        global_progress = self.calculate_global_progress()
        message = {
            "type": "state_update",
            "tasks": tasks_list,
            "global_progress": global_progress,
        }
        await self.send_message(player_id, message)

    def validate_task_start(self, player_id: str, task_name: str) -> tuple[bool, str]:
        """Validates if a player can start a task."""
        player = self.state.players[player_id]

        # Follow validation order from spec:
        if not player.is_alive:
            return False, "Player is not alive"
        if self.state.phase != "free_roam":
            return False, "Not in free roam phase"
        if task_name not in player.tasks:
            return False, "Task not assigned to player"
        if player.location != player.tasks[task_name].room:
            return False, "Player is not in the correct room"
        if player.active_task is not None:
            return False, "Player has another active task"
        return True, None

    async def interrupt_player_task(self, player_id: str, reason: str):
        """Interrupts the active task of a player."""
        player = self.state.players[player_id]
        if player.active_task:
            task_name = player.active_task
            task = player.tasks[task_name]
            interrupted = task.interrupt()
            if interrupted:
                player.movement_locked = False
                player.active_task = None
                # Send task_interrupted message to player
                await self.send_message(
                    player_id,
                    {
                        "type": "task_interrupted",
                        "task_name": task_name,
                        "reason": reason,
                    },
                )
                # Update task list display
                pass
                await self.send_task_list_update(player_id)

    async def task_tick_loop(self):
        """Main loop that processes task ticks every task_tick_interval seconds."""
        while True:
            await asyncio.sleep(self.state.task_tick_interval)
            await self.process_task_ticks()

    async def process_task_ticks(self):
        """Processes task ticks for all active tasks."""
        for player_id, player in self.state.players.items():
            if player.active_task:
                task_name = player.active_task
                task = player.tasks[task_name]
                task_completed = task.tick()
                # Send task_progress message to player
                await self.send_message(
                    player_id,
                    {
                        "type": "task_progress",
                        "task_name": task_name,
                        "turns_remaining": task.turns_remaining,
                    },
                )
                if task_completed:
                    # Task is completed
                    player.movement_locked = False  # Release movement lock
                    player.active_task = None
                    global_progress = self.calculate_global_progress()
                    # Broadcast task_complete message to all players
                    await self.broadcast(
                        {
                            "type": "task_complete",
                            "player_id": player_id,
                            "task_name": task_name,
                            "global_progress": global_progress,
                        }
                    )
                    # Check for crew victory
                    if global_progress >= 1.0:
                        await self.broadcast({"type": "crew_victory"})
                        # End the game (not implemented here)
                    else:
                        # Update task list display
                        pass
                        # await self.send_task_list_update(player_id)
                else:
                    # Task not yet completed
                    pass


if __name__ == "__main__":
    server = GameServer()
    asyncio.run(server.start_server())
