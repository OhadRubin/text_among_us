# server.py

import asyncio
import websockets
import uuid
import json
import logging
import random

# Simplified Game Server for an Among Us-like game


PLAYER_NAMES = ["Alice", "Bob", "Charlie", "Dave", "Eve", "Mallory", "Trent"]

class Player:
    def __init__(self, player_id, websocket):
        self.id = player_id
        self.websocket = websocket
        self.location = "cafeteria"
        self.role = "Crewmate"
        self.is_alive = True
        self.emergency_meetings_left = 1


class GameServer:
    def __init__(self):
        self.players = {}
        self.bodies = {}  # player_id -> location
        self.map_layout = self.initialize_map()
        self.phase = "free_roam"
        self.votes = {}
        self.logger = self.setup_logger()
        self.game_started = False
        self.min_players = 3
        self.impostor_ratio = 0.2
        self.discussion_duration = 60
        self.voting_duration = 30
        self.max_emergency_meetings = 1

    def setup_logger(self):
        logger = logging.getLogger("GameServer")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    async def handle_connection(self, websocket, path):
        player_id = PLAYER_NAMES[len(self.players)]
        player = Player(player_id, websocket)
        self.players[player_id] = player

        await self.broadcast(
            {
                "type": "player_connected",
                "player_id": player_id,
                "location": player.location,
            }
        )

        if len(self.players) >= self.min_players and not self.game_started:
            self.assign_roles()
            self.game_started = True
            self.logger.info(f"Game started with {len(self.players)} players.")
            await self.broadcast({"type": "game_started"})

        self.logger.info(f"Player {player_id} connected.")
        try:
            await self.send_state_update(player_id)
            async for message_str in websocket:
                message = json.loads(message_str)
                await self.process_message(player_id, message)
        except websockets.exceptions.ConnectionClosedError:
            self.logger.warning(f"Player {player_id} disconnected unexpectedly.")
        finally:
            if player_id in self.players:
                del self.players[player_id]
                await self.broadcast(
                    {"type": "player_disconnected", "player_id": player_id}
                )
                self.logger.info(f"Player {player_id} disconnected.")

    def assign_roles(self):
        player_ids = list(self.players.keys())
        impostor_count = max(1, int(len(player_ids) * self.impostor_ratio))
        impostor_ids = random.sample(player_ids, impostor_count)
        for player_id in player_ids:
            player = self.players[player_id]
            player.role = "Impostor" if player_id in impostor_ids else "Crewmate"
            asyncio.create_task(self.send_state_update(player_id))

    async def process_message(self, player_id, message):
        action = message.get("action")
        if action == "move":
            destination = message.get("destination")
            await self.handle_move(player_id, destination)
        elif action == "kill":
            target_id = message.get("target")
            await self.handle_kill(player_id, target_id)
        elif action == "report":
            await self.handle_report(player_id)
        elif action == "vote":
            voted_player = message.get("vote")
            await self.handle_vote(player_id, voted_player)
        elif action == "call_meeting":
            await self.handle_emergency_meeting(player_id)
        elif action == "chat":
            message_text = message.get("message")
            await self.handle_chat(player_id, message_text)
        else:
            await self.send_error(player_id, "Invalid action.")

    async def handle_move(self, player_id, destination):
        player = self.players[player_id]
        if destination in self.map_layout.get(player.location, []):
            old_location = player.location
            player.location = destination
            
            # Broadcast movement to everyone
            await self.broadcast({
                "type": "player_moved",
                "player_id": player_id,
                "from": old_location,
                "to": destination,
            })
            
            # Send state updates to all players in both old and new locations
            for pid, p in self.players.items():
                if p.location in [old_location, destination]:
                    await self.send_state_update(pid)
        else:
            await self.send_error(player_id, "Invalid move.")

    async def handle_kill(self, killer_id, target_id):
        killer = self.players.get(killer_id)
        target = self.players.get(target_id)
        if (
            killer
            and target
            and killer.role == "Impostor"
            and killer.is_alive
            and target.is_alive
            and killer.location == target.location
        ):
            target.is_alive = False
            self.bodies[target_id] = target.location
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

    async def handle_report(self, reporter_id):
        reporter = self.players[reporter_id]
        location = reporter.location
        if any(body_loc == location for body_loc in self.bodies.values()):
            await self.start_discussion_phase()
        else:
            await self.send_error(reporter_id, "No bodies to report here.")

    async def handle_vote(self, player_id, voted_player):
        if player_id not in self.votes:
            self.votes[player_id] = voted_player
            await self.send_message(player_id, {"type": "vote_received"})
            if len(self.votes) >= len([p for p in self.players.values() if p.is_alive]):
                await self.tally_votes()
        else:
            await self.send_error(player_id, "You have already voted.")

    async def handle_emergency_meeting(self, player_id):
        player = self.players[player_id]
        if player.emergency_meetings_left > 0:
            player.emergency_meetings_left -= 1
            await self.start_discussion_phase()
        else:
            await self.send_error(player_id, "No emergency meetings left.")

    async def handle_chat(self, player_id, message_text):
        player = self.players[player_id]
        if self.phase == "discussion" and player.is_alive:
            await self.broadcast(
                {
                    "type": "chat_message",
                    "player_id": player_id,
                    "message": message_text,
                }
            )
        else:
            await self.send_error(player_id, "Cannot chat now.")

    async def start_discussion_phase(self):
        self.phase = "discussion"
        await self.broadcast(
            {
                "type": "phase_change",
                "phase": "discussion",
                "duration": self.discussion_duration,
            }
        )
        await asyncio.sleep(self.discussion_duration)
        await self.start_voting_phase()

    async def start_voting_phase(self):
        self.phase = "voting"
        await self.broadcast(
            {
                "type": "phase_change",
                "phase": "voting",
                "duration": self.voting_duration,
            }
        )
        await asyncio.sleep(self.voting_duration)
        await self.tally_votes()
        self.phase = "free_roam"

    async def tally_votes(self):
        vote_counts = {}
        for vote in self.votes.values():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
        if vote_counts:
            max_votes = max(vote_counts.values())
            candidates = [
                pid for pid, count in vote_counts.items() if count == max_votes
            ]
            if len(candidates) == 1 and candidates[0] != "skip":
                ejected_player_id = candidates[0]
                ejected_player = self.players[ejected_player_id]
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
        self.votes.clear()

    async def send_state_update(self, player_id):
        player = self.players[player_id]
        location = player.location
        available_exits = self.map_layout.get(location, [])
        players_in_room = [
            pid for pid, p in self.players.items() if p.location == location
        ]
        bodies_in_room = [pid for pid, loc in self.bodies.items() if loc == location]
        state = {
            "type": "state_update",
            "location": location,
            "players_in_room": players_in_room,
            "available_exits": available_exits,
            "role": player.role,
            "status": "alive" if player.is_alive else "dead",
            "bodies_in_room": bodies_in_room,
        }
        await self.send_message(player_id, state)

    async def send_error(self, player_id, message):
        await self.send_message(player_id, {"type": "error", "message": message})

    async def send_message(self, player_id, message):
        player = self.players[player_id]
        await player.websocket.send(json.dumps(message))

    async def broadcast(self, message):
        message_str = json.dumps(message)
        # Create a list of players to remove
        disconnected_players = []
        
        for player_id, player in self.players.items():
            try:
                await player.websocket.send(message_str)
            except websockets.exceptions.ConnectionClosedError:
                # Mark this player for removal
                disconnected_players.append(player_id)
                self.logger.info(f"Player {player_id} disconnected during broadcast")
        
        # Remove disconnected players
        for player_id in disconnected_players:
            del self.players[player_id]

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

    async def start_server(self):
        server = await websockets.serve(self.handle_connection, "localhost", 8765)
        self.logger.info("Server started on ws://localhost:8765")
        await server.wait_closed()


if __name__ == "__main__":
    server = GameServer()
    asyncio.run(server.start_server())
