# game_server.py

import asyncio
import websockets
import json
import logging
import random
from collections import defaultdict

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


class Player:
    """Represents a player in the game."""

    def __init__(self, player_id, websocket):
        self.id = player_id
        self.websocket = websocket
        self.location = "cafeteria"
        self.role = "Crewmate"
        self.is_alive = True
        self.emergency_meetings_left = 1


class GameState:
    """Holds the current state of the game."""

    def __init__(self):
        self.players = {}
        self.bodies = {}  # Maps player_id to location where they died
        self.map_layout = self.initialize_map()
        self.phase = "free_roam"
        self.votes = {}
        self.game_started = False
        self.min_players = 3
        self.impostor_ratio = 0.2
        self.discussion_duration = 60
        self.voting_duration = 30
        self.max_emergency_meetings = 1
        self.logger = self.setup_logger()

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


class GameServer:
    """Main game server class that orchestrates the game."""

    def __init__(self):
        self.event_manager = EventManager()
        self.state = GameState()
        self.setup_event_listeners()

    def setup_event_listeners(self):
        """Registers event handlers with the EventManager."""
        em = self.event_manager
        em.register("player_connected", self.on_player_connected)
        em.register("player_disconnected", self.on_player_disconnected)
        em.register("action_move", self.on_action_move)
        em.register("action_kill", self.on_action_kill)
        em.register("action_report", self.on_action_report)
        em.register("action_vote", self.on_action_vote)
        em.register("action_call_meeting", self.on_action_call_meeting)
        em.register("action_chat", self.on_action_chat)

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
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Server is full"
                }))
                return
            
            # Generate player ID first
            player_id = PLAYER_NAMES[len(self.state.players)]
            player = Player(player_id, websocket)
            self.state.players[player_id] = player

            # Send initial welcome message
            await self.send_message(player_id, {
                "type": "welcome",
                "player_id": player_id
            })

            # Dispatch player_connected event
            await self.event_manager.dispatch("player_connected", {"player_id": player_id})

            # Check if game should start
            if (len(self.state.players) >= self.state.min_players
                and not self.state.game_started):
                self.assign_roles()
                self.state.game_started = True
                self.state.logger.info(f"Game started with {len(self.state.players)} players.")
                await self.broadcast({"type": "game_started"})

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
            self.state.logger.error(f"Error handling connection: {str(e)}")
        finally:
            if player_id in self.state.players:
                await self.event_manager.dispatch(
                    "player_disconnected", {"player_id": player_id}
                )

    # Event Handlers
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

    async def on_player_disconnected(self, data):
        """Handles a player disconnection event."""
        player_id = data["player_id"]
        if player_id in self.state.players:
            del self.state.players[player_id]
            await self.broadcast(
                {
                    "type": "player_disconnected",
                    "player_id": player_id,
                }
            )
            self.state.logger.info(f"Player {player_id} disconnected.")

    async def on_action_move(self, data):
        """Handles player movement actions."""
        player_id = data["player_id"]
        destination = data.get("destination")
        player = self.state.players[player_id]
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

    async def on_action_kill(self, data):
        """Handles kill actions initiated by Impostors."""
        killer_id = data["player_id"]
        target_id = data.get("target")
        killer = self.state.players.get(killer_id)
        target = self.state.players.get(target_id)
        if (
            killer
            and target
            and killer.role == "Impostor"
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

    async def on_action_report(self, data):
        """Handles body report actions."""
        reporter_id = data["player_id"]
        reporter = self.state.players[reporter_id]
        location = reporter.location
        if any(body_loc == location for body_loc in self.state.bodies.values()):
            await self.start_discussion_phase()
        else:
            await self.send_error(reporter_id, "No bodies to report here.")

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
            player.role = "Impostor" if player_id in impostor_ids else "Crewmate"
            asyncio.create_task(self.send_state_update(player_id))

    async def start_discussion_phase(self):
        """Initiates the discussion phase after a body is reported or a meeting is called."""
        self.state.phase = "discussion"
        self.state.votes.clear()
        
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
            candidates = [
                pid for pid, count in vote_counts.items() if count == max_votes
            ]
            if len(candidates) == 1 and candidates[0] != "skip":
                ejected_player_id = candidates[0]
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

    async def send_message(self, player_id, message):
        """Sends a message to a specific player."""
        player = self.state.players[player_id]
        try:
            self.state.logger.info(f"Sending message to {player_id}: {message['type']}")
            await player.websocket.send(json.dumps(message))
            self.state.logger.info(f"Message sent successfully to {player_id}")
        except websockets.exceptions.ConnectionClosedError:
            self.state.logger.warning(
                f"Could not send message to {player_id}; connection closed."
            )
        except Exception as e:
            self.state.logger.error(f"Error sending message to {player_id}: {str(e)}")

    async def broadcast(self, message):
        """Broadcasts a message to all connected players."""
        message_str = json.dumps(message)
        self.state.logger.info(f"Broadcasting message type: {message['type']}")
        disconnected_players = []

        # Create a copy of players to avoid modification during iteration
        players_copy = dict(self.state.players)
        
        for player_id, player in players_copy.items():
            try:
                await player.websocket.send(message_str)
                self.state.logger.info(f"Broadcast successful to {player_id}")
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


if __name__ == "__main__":
    server = GameServer()
    asyncio.run(server.start_server())
