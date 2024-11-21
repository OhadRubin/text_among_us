# server.py

import asyncio
import websockets
import uuid
import json
import logging
import fire
import random

import pygame
import sys
from typing import Dict, Optional, Any, Callable, List
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import time


# Event types constants
class GameEvents:
    PLAYER_MOVED = "player_moved"
    PLAYER_KILLED = "player_killed"
    BODY_REPORTED = "body_reported"
    EMERGENCY_MEETING = "emergency_meeting"
    PHASE_CHANGED = "phase_changed"
    PLAYER_VOTED = "player_voted"
    PLAYER_CONNECTED = "player_connected"
    PLAYER_DISCONNECTED = "player_disconnected"
    CHAT_MESSAGE = "chat_message"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    ERROR_OCCURRED = "error_occurred"
    PLAYER_EJECTED = "player_ejected"
    NO_EJECTION = "no_ejection"
    VOTE_CONFIRMATION = "vote_confirmation"


class GameServer:
    def __init__(self):
        self.players = {}  # key: player_id, value: dict with 'websocket' and 'location'
        self.map_structure = self.initialize_map()
        self.roles = {}  # player_id -> role
        self.player_status = {}  # player_id -> "alive" or "dead"
        self.bodies = {}  # player_id -> location
        self.PROXIMITY_RADIUS = "same_room"  # Bodies can only be reported in same room
        self.setup_logging()
        self.exit_buttons = {}  # Store button rectangles for click detection
        self.game_started = False
        self.current_phase = "free_roam"
        self.discussion_timer = 60  # Configurable discussion duration in seconds
        self.voting_timer = 30      # Configurable voting duration in seconds
        self.votes = {}             # player_id -> voted_player_id or "skip"
        self.emergency_meetings = {}  # player_id -> number of meetings called
        self.max_emergency_meetings = 1  # Configurable max number of meetings per player

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler("game_server.log"), logging.StreamHandler()],
        )

    def initialize_map(self):
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

    def generate_unique_id(self):
        return str(uuid.uuid4())

    async def handle_connection(self, websocket, path):
        if self.game_started:
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "payload": {
                            "message": "Game already in progress. Please wait."
                        },
                    }
                )
            )
            return

        player_id = self.generate_unique_id()
        initial_location = "cafeteria"
        self.players[player_id] = {"websocket": websocket, "location": initial_location}
        self.player_status[player_id] = "alive"

        # Broadcast new player connection
        await self.broadcast_message(
            {
                "type": "player_update",
                "payload": {
                    "event": GameEvents.PLAYER_CONNECTED,
                    "player_id": player_id,
                    "location": initial_location,
                },
            }
        )

        # Update state for all players in the initial room
        await self.update_room_players(initial_location)

        # Check if we should start the game and assign roles
        if len(self.players) >= 6 and not self.game_started:
            self.assign_roles()
            self.game_started = True
            logging.info("Game started with {} players".format(len(self.players)))
            # Broadcast game start
            await self.broadcast_message(
                {
                    "type": "game_update",
                    "payload": {"event": GameEvents.GAME_STARTED},
                }
            )

        logging.info(f"Player {player_id} connected.")
        try:
            await self.send_state_update(player_id)
            async for message in websocket:
                await self.process_message(message, player_id)
        except websockets.exceptions.ConnectionClosedError:
            logging.warning(f"Connection closed unexpectedly for player {player_id}.")
        finally:
            # Broadcast player disconnection before cleanup
            current_location = self.players[player_id]["location"]

            if player_id in self.roles:
                del self.roles[player_id]
            if player_id in self.player_status:
                del self.player_status[player_id]
            del self.players[player_id]

            await self.broadcast_message(
                {
                    "type": "player_update",
                    "payload": {
                        "event": GameEvents.PLAYER_DISCONNECTED,
                        "player_id": player_id,
                        "location": current_location,
                    },
                }
            )

            # Update state for players in the room where disconnection occurred
            await self.update_room_players(current_location)

            logging.info(f"Player {player_id} disconnected.")

    def assign_roles(self):
        # Check if there are enough players
        if len(self.players) < 6:
            return

        player_ids = list(self.players.keys())
        total_players = len(player_ids)
        impostor_count = 1 if total_players <= 7 else 2  # Adjusted threshold for 2 impostors

        # Randomly select impostors
        impostor_ids = random.sample(player_ids, impostor_count)

        # Clear existing roles before reassigning
        self.roles.clear()

        # Assign roles to all players
        for player_id in player_ids:
            role = "Impostor" if player_id in impostor_ids else "Crewmate"
            self.roles[player_id] = role
            
            # Send individual role update to each player
            asyncio.create_task(self.send_state_update(player_id))

        logging.info(f"Roles assigned. Impostors: {impostor_ids}")

    async def process_message(self, message, player_id):
        data = json.loads(message)
        if data["type"] == "action":
            action = data["payload"]["action"]
            if self.current_phase == "discussion":
                if action == GameEvents.CHAT_MESSAGE:
                    message_text = data["payload"]["message"]
                    await self.handle_chat(player_id, message_text)
            elif self.current_phase == "voting":
                if action == GameEvents.PLAYER_VOTED:
                    voted_player = data["payload"]["vote"]
                    await self.handle_vote(player_id, voted_player)
            else:
                if self.player_status.get(player_id) != "alive":
                    await self.send_error(player_id, "You are dead and cannot perform actions.")
                    return
                if action == "move":
                    destination = data["payload"]["destination"]
                    await self.handle_move(player_id, destination)
                elif action == "kill":
                    target_id = data["payload"].get("target")
                    await self.handle_kill(player_id, target_id)
                elif action == "report":
                    await self.handle_report(player_id)
                elif action == "call_meeting":
                    await self.handle_emergency_meeting(player_id)
                else:
                    await self.send_error(player_id, "Invalid action.")

    def validate_move(self, current_location, destination):
        return destination in self.map_structure.get(current_location, [])

    async def handle_move(self, player_id, destination):
        if self.player_status.get(player_id) != "alive":
            await self.send_error(player_id, "You are dead and cannot move.")
            return
        current_location = self.players[player_id]["location"]
        if self.validate_move(current_location, destination):
            self.players[player_id]["location"] = destination

            # Broadcast movement to all players
            await self.broadcast_message({
                "type": "movement",
                "payload": {
                    "player_id": player_id,
                    "from": current_location,
                    "to": destination,
                }
            })

            # Send individual state updates to affected rooms' players
            await self.update_room_players(current_location)  # Update players in the old room
            await self.update_room_players(destination)  # Update players in the new room

            logging.info(f"Player {player_id} moved to {destination}.")
        else:
            await self.send_error(player_id, "Invalid move")

    async def update_room_players(self, room_name):
        """Send state updates to all players in a specific room"""
        for pid, player_data in self.players.items():
            if player_data["location"] == room_name:
                await self.send_state_update(pid)

    async def handle_kill(self, killer_id, target_id):
        if not target_id:
            await self.send_error(killer_id, "No target specified for kill action.")
            return
        if not self.validate_kill(killer_id, target_id):
            await self.send_error(killer_id, "Invalid kill attempt")
            return

        self.player_status[target_id] = "dead"
        location = self.players[target_id]["location"]
        self.bodies[target_id] = location

        # Update all players in the room where the kill occurred
        for pid, player_data in self.players.items():
            if player_data["location"] == location:
                await self.send_state_update(pid)

        # Notify others in the room
        await self.broadcast_message({
            "type": "event",
            "payload": {
                "event": GameEvents.PLAYER_KILLED,
                "killer": killer_id,
                "victim": target_id,
                "location": location,
            }
        })

    def validate_kill(self, killer_id, target_id):
        return (
            self.roles.get(killer_id) == "Impostor"
            and self.player_status.get(killer_id) == "alive"
            and self.player_status.get(target_id) == "alive"
            and self.players[killer_id]["location"]
            == self.players[target_id]["location"]
        )

    async def handle_report(self, reporter_id):
        if not self.validate_report(reporter_id):
            await self.send_error(reporter_id, "No bodies nearby to report")
            return

        # Get all bodies in reporter's room
        reporter_location = self.players[reporter_id]["location"]
        reported_bodies = [
            body_id
            for body_id, location in self.bodies.items()
            if location == reporter_location
        ]

        # Remove bodies from the game after reporting
        for body_id in reported_bodies:
            del self.bodies[body_id]

        await self.broadcast_message(
            {
                "type": "event",
                "payload": {
                    "event": GameEvents.BODY_REPORTED,
                    "reporter": reporter_id,
                    "location": reporter_location,
                    "bodies": reported_bodies,
                },
            }
        )

        # Start the discussion phase after a report
        await self.start_discussion_phase()

    def validate_report(self, reporter_id):
        # Check if reporter is alive
        if self.player_status.get(reporter_id) != "alive":
            return False

        # Check if there are any bodies in the same room
        reporter_location = self.players[reporter_id]["location"]
        return any(
            location == reporter_location for body_id, location in self.bodies.items()
        )

    async def broadcast_message(self, message, alive_only=False):
        for player_id, player in self.players.items():
            if alive_only and self.player_status.get(player_id) != "alive":
                continue
            await player["websocket"].send(json.dumps(message))

    async def send_state_update(self, player_id):
        location = self.players[player_id]["location"]
        if self.player_status.get(player_id) != "alive":
            available_exits = []
            exits_status = {}
        else:
            available_exits = self.map_structure.get(location, [])
            exits_status = {
                exit: "available" for exit in available_exits  # All exits are now always available
            }

        # Get bodies in current room
        bodies_in_room = [
            body_id for body_id, body_loc in self.bodies.items() if body_loc == location
        ]

        state_message = {
            "type": "state",
            "payload": {
                "location": location,
                "players_in_room": self.get_players_in_room(location),
                "available_exits": available_exits,
                "exits_status": exits_status,
                "role": self.roles.get(player_id),
                "status": self.player_status.get(player_id),
                "bodies_in_room": bodies_in_room,
            },
            "player_id": player_id,
        }
        await self.players[player_id]["websocket"].send(json.dumps(state_message))

    def get_players_in_room(self, location):
        return {
            pid: {
                "status": self.player_status[pid],
                "role": self.roles.get(pid, "unknown"),
            }
            for pid, data in self.players.items()
            if data["location"] == location and self.player_status.get(pid) == "alive"
        }

    async def send_error(self, player_id, message):
        error_message = {
            "type": "error",
            "payload": {"message": message},
            "player_id": player_id,
        }
        websocket = self.players[player_id]["websocket"]
        await websocket.send(json.dumps(error_message))

    async def start_server(self):
        server = await websockets.serve(self.handle_connection, "localhost", 8765)
        logging.info("Server started on ws://localhost:8765")
        await server.wait_closed()

    async def start_discussion_phase(self):
        self.current_phase = "discussion"
        self.votes.clear()
        # Notify all players about the discussion phase
        await self.broadcast_message({
            "type": "phase_update",
            "payload": {
                "phase": "discussion",
                "duration": self.discussion_timer
            }
        })
        # Start the discussion timer
        await asyncio.sleep(self.discussion_timer)
        # Transition to voting phase
        await self.start_voting_phase()

    async def start_voting_phase(self):
        self.current_phase = "voting"
        # Notify all players about the voting phase
        await self.broadcast_message({
            "type": "phase_update",
            "payload": {
                "phase": "voting",
                "duration": self.voting_timer
            }
        })
        # Start the voting timer
        await asyncio.sleep(self.voting_timer)
        # Tally votes and handle ejection
        await self.tally_votes()
        # Return to free roam phase
        self.current_phase = "free_roam"
        await self.broadcast_message({
            "type": "phase_update",
            "payload": {
                "phase": "free_roam"
            }
        })

    async def handle_chat(self, player_id, message_text):
        if self.player_status.get(player_id) != "alive":
            await self.send_error(player_id, "Dead players cannot chat.")
            return
        # Broadcast chat message to all alive players
        await self.broadcast_message({
            "type": "chat",
            "payload": {
                "player_id": player_id,
                "message": message_text
            }
        }, alive_only=True)

    async def handle_vote(self, player_id, voted_player):
        if self.player_status.get(player_id) != "alive":
            await self.send_error(player_id, "Dead players cannot vote.")
            return
        if player_id in self.votes:
            await self.send_error(player_id, "You have already voted.")
            return
        if voted_player not in self.players and voted_player != "skip":
            await self.send_error(player_id, "Invalid vote.")
            return
        self.votes[player_id] = voted_player
        await self.players[player_id]["websocket"].send(json.dumps({
            "type": "vote_confirmation",
            "payload": {
                "message": "Vote received."
            }
        }))

    async def tally_votes(self):
        vote_counts = {}
        for vote in self.votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
        if vote_counts:
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
            if len(candidates) == 1 and candidates[0] != "skip":
                ejected_player = candidates[0]
                self.player_status[ejected_player] = "dead"
                await self.broadcast_message({
                    "type": "event",
                    "payload": {
                        "event": GameEvents.PLAYER_VOTED,
                        "player_id": ejected_player,
                        "role_revealed": self.roles.get(ejected_player)
                    }
                })
            else:
                # Tie or majority chose to skip
                await self.broadcast_message({
                    "type": "event",
                    "payload": {
                        "event": "no_ejection",
                        "message": "No one was ejected."
                    }
                })
        else:
            # No votes cast
            await self.broadcast_message({
                "type": "event",
                "payload": {
                    "event": "no_ejection",
                    "message": "No votes cast. No one was ejected."
                }
            })

    async def handle_emergency_meeting(self, player_id):
        if self.player_status.get(player_id) != "alive":
            await self.send_error(player_id, "Dead players cannot call meetings.")
            return
        meetings_called = self.emergency_meetings.get(player_id, 0)
        if meetings_called >= self.max_emergency_meetings:
            await self.send_error(player_id, "No emergency meetings left.")
            return
        self.emergency_meetings[player_id] = meetings_called + 1
        await self.start_discussion_phase()
