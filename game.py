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


class GameServer:
    def __init__(self):
        self.players = {}  # key: player_id, value: dict with 'websocket' and 'location'
        self.map_structure = self.initialize_map()
        # Initialize room occupancy tracking
        self.room_occupancy = {room_name: 0 for room_name in self.map_structure.keys()}
        # Add new role-related attributes
        self.roles = {}  # player_id -> role
        self.player_status = {}  # player_id -> "alive" or "dead"
        self.bodies = {}  # player_id -> location
        self.PROXIMITY_RADIUS = "same_room"  # Bodies can only be reported in same room
        self.setup_logging()
        self.exit_buttons = {}  # Store button rectangles for click detection
        self.game_started = (
            False  # Added to prevent role reassignment and new connections mid-game
        )

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

    def can_enter_room(self, room_name):
        capacity = 10 if room_name == "cafeteria" else 5
        return self.room_occupancy[room_name] < capacity

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
        self.room_occupancy[initial_location] += 1

        # Broadcast new player connection
        await self.broadcast_message(
            {
                "type": "player_update",
                "payload": {
                    "event": "connected",
                    "player_id": player_id,
                    "location": initial_location,
                },
            }
        )

        # Update state for all players in the initial room
        await self.update_room_players(initial_location)

        # Check if we should start the game and assign roles
        if len(self.players) >= 4 and not self.game_started:
            self.assign_roles()
            self.game_started = True
            logging.info("Game started with {} players".format(len(self.players)))
            # Broadcast game start
            await self.broadcast_message(
                {
                    "type": "game_update",
                    "payload": {"event": "game_started"},
                }
            )

        logging.info(f"Player {player_id} connected. Room occupancy: {self.room_occupancy}")
        try:
            await self.send_state_update(player_id)
            async for message in websocket:
                await self.process_message(message, player_id)
        except websockets.exceptions.ConnectionClosedError:
            logging.warning(f"Connection closed unexpectedly for player {player_id}.")
        finally:
            # Broadcast player disconnection before cleanup
            current_location = self.players[player_id]["location"]
            self.room_occupancy[current_location] -= 1

            if player_id in self.roles:
                del self.roles[player_id]
            if player_id in self.player_status:
                del self.player_status[player_id]
            del self.players[player_id]

            await self.broadcast_message(
                {
                    "type": "player_update",
                    "payload": {
                        "event": "disconnected",
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
        if len(self.players) < 4:
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
            if self.player_status.get(player_id) != "alive":
                await self.send_error(
                    player_id, "You are dead and cannot perform actions."
                )
                return
            action = data["payload"]["action"]
            if action == "move":
                destination = data["payload"]["destination"]
                await self.handle_move(player_id, destination)
            elif action == "kill":
                target_id = data["payload"].get("target")
                await self.handle_kill(player_id, target_id)
            elif action == "report":
                await self.handle_report(player_id)
            else:
                await self.send_error(player_id, "Invalid action.")

    def validate_move(self, current_location, destination):
        return destination in self.map_structure.get(current_location, [])

    async def handle_move(self, player_id, destination):
        if self.player_status.get(player_id) != "alive":
            await self.send_error(player_id, "You are dead and cannot move.")
            return
        current_location = self.players[player_id]["location"]
        if self.validate_move(current_location, destination) and self.can_enter_room(
            destination
        ):
            # Update room occupancy
            self.room_occupancy[current_location] -= 1
            self.room_occupancy[destination] += 1
            # Update player location
            self.players[player_id]["location"] = destination

            # Broadcast movement to all players
            await self.broadcast_message(
                {
                    "type": "movement",
                    "payload": {
                        "player_id": player_id,
                        "from": current_location,
                        "to": destination,
                    },
                }
            )

            # Send individual state updates to affected rooms' players
            await self.update_room_players(
                current_location
            )  # Update players in the old room
            await self.update_room_players(
                destination
            )  # Update players in the new room

            logging.info(
                f"Player {player_id} moved to {destination}. Room occupancy: {self.room_occupancy}"
            )
        else:
            error_msg = (
                "Room is full"
                if not self.can_enter_room(destination)
                else "Invalid move"
            )
            await self.send_error(player_id, error_msg)

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
        self.bodies[target_id] = self.players[target_id]["location"]
        # Update room occupancy when player dies
        location = self.players[target_id]["location"]
        self.room_occupancy[location] -= 1

        await self.send_state_update(killer_id)
        await self.send_state_update(target_id)

        # Notify others in the room
        await self.broadcast_message(
            {
                "type": "event",
                "payload": {
                    "event": "player_killed",
                    "killer": killer_id,
                    "victim": target_id,
                    "location": location,
                },
            }
        )

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
                    "event": "body_reported",
                    "reporter": reporter_id,
                    "location": reporter_location,
                    "bodies": reported_bodies,
                },
            }
        )

    def validate_report(self, reporter_id):
        # Check if reporter is alive
        if self.player_status.get(reporter_id) != "alive":
            return False

        # Check if there are any bodies in the same room
        reporter_location = self.players[reporter_id]["location"]
        return any(
            location == reporter_location for body_id, location in self.bodies.items()
        )

    async def broadcast_message(self, message):
        for player in self.players.values():
            await player["websocket"].send(json.dumps(message))

    async def send_state_update(self, player_id):
        location = self.players[player_id]["location"]
        if self.player_status.get(player_id) != "alive":
            available_exits = []
            exits_status = {}
        else:
            available_exits = self.map_structure.get(location, [])
            exits_status = {
                exit: "full" if not self.can_enter_room(exit) else "available"
                for exit in available_exits
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
                "room_capacity": 10 if location == "cafeteria" else 5,
                "exits_status": exits_status,
                "role": self.roles.get(player_id),
                "status": self.player_status.get(player_id),
                "bodies_in_room": bodies_in_room,  # Add bodies in room to state
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


class CliGameClient:
    def __init__(self):
        self.player_id = None
        self.location = None
        self.available_exits = []
        self.websocket = None
        self.setup_logging()
        self.running = True  # Flag to control the main loop
        self.map_template = """
        [cafeteria]---[upper_engine]---[reactor]
             |              |             |
        [medbay]---[engine_room]---[security]
             |              |             |
        [storage]---[lower_engine]---[electrical]
        """

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )

    async def connect(self):
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            self.websocket = websocket
            logging.info("Connected to the game server.")
            # Start listener and input tasks
            listener_task = asyncio.create_task(self.receive_messages())
            input_task = asyncio.create_task(self.send_commands())
            await asyncio.wait(
                [listener_task, input_task], return_when=asyncio.FIRST_COMPLETED
            )
            # Cancel any pending tasks
            listener_task.cancel()
            input_task.cancel()
            logging.info("Disconnected from the game server.")

    async def receive_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get("type")
                if message_type == "state":
                    self.player_id = data.get("player_id")
                    payload = data.get("payload")
                    self.location = payload.get("location")
                    self.available_exits = payload.get("available_exits")
                    self.state_data = payload  # Store the complete state data
                    self.display_current_location()
                elif message_type == "movement":
                    payload = data.get("payload")
                    player = payload.get("player_id")
                    from_room = payload.get("from")
                    to_room = payload.get("to")
                    if player != self.player_id:  # Don't show own movements
                        print(f"\nPlayer {player} moved from {from_room} to {to_room}")
                        print("> ", end="", flush=True)  # Restore prompt
                elif message_type == "player_update":
                    payload = data.get("payload")
                    player = payload.get("player_id")
                    event = payload.get("event")
                    location = payload.get("location")
                    if player != self.player_id:
                        print(f"\nPlayer {player} {event} in {location}")
                        print("> ", end="", flush=True)  # Restore prompt
                elif message_type == "error":
                    payload = data.get("payload")
                    error_message = payload.get("message")
                    print(f"Error: {error_message}")
                elif message_type == "event":
                    payload = data.get("payload")
                    event = payload.get("event")
                    if event == "body_reported":
                        print(f"\nBody reported by Player {payload.get('reporter')}")
                        print("> ", end="", flush=True)
                    elif event == "player_killed":
                        print(f"\nPlayer {payload.get('victim')} was killed")
                        print("> ", end="", flush=True)
                else:
                    print("Received unknown message type.")
        except websockets.exceptions.ConnectionClosed:
            pass  # Handle the connection being closed
        finally:
            self.running = False  # Stop the input loop

    def parse_command(self, input_line):
        tokens = input_line.strip().split()
        if not tokens:
            return None, None
        command = tokens[0]
        args = tokens[1:]
        return command, args

    async def send_commands(self):
        while self.running:
            input_line = await asyncio.get_event_loop().run_in_executor(
                None, input, "> "
            )

            command, args = self.parse_command(input_line)
            if command == "move" and args:
                await self.send_move_command(args[0])
            elif command == "kill" and args:
                await self.send_kill_command(args[0])
            elif command == "report":
                await self.send_report_command()
            elif command == "look":
                self.display_current_location()
            elif command == "help":
                self.display_help()
            elif command in ["exit", "q"]:
                await self.disconnect()
                break
            else:
                print("Unknown command. Type 'help' for available commands.")

    async def send_move_command(self, destination):
        if self.player_id is None:
            print("You are not connected to the server yet.")
            return
        action_message = {
            "type": "action",
            "payload": {"action": "move", "destination": destination},
            "player_id": self.player_id,
        }
        await self.websocket.send(json.dumps(action_message))

    async def send_kill_command(self, target_id):
        action_message = {
            "type": "action",
            "payload": {"action": "kill", "target": target_id},
            "player_id": self.player_id,
        }
        await self.websocket.send(json.dumps(action_message))

    async def send_report_command(self):
        action_message = {
            "type": "action",
            "payload": {"action": "report"},
            "player_id": self.player_id,
        }
        await self.websocket.send(json.dumps(action_message))

    async def disconnect(self):
        self.running = False
        await self.websocket.close()
        print("You have exited the game.")

    def display_current_location(self):
        if not self.location:
            print("Waiting for game state...")
            return

        print(f"\nCurrent Location: {self.location}")
        if hasattr(self, "state_data"):
            role = self.state_data.get("role", "Unknown")
            status = self.state_data.get("status", "Unknown")
            print(f"Role: {role}")
            print(f"Status: {status}")

            # Show if there are any bodies in the room
            bodies_in_room = self.state_data.get("bodies_in_room", [])
            if bodies_in_room:
                print("\nDead bodies in this room:")
                for body_id in bodies_in_room:
                    print(f"  - Body of Player {body_id}")

            players_in_room = self.state_data.get("players_in_room", {})
            if players_in_room:
                print("\nPlayers in this room:")
                for pid, data in players_in_room.items():
                    if pid != self.player_id:
                        print(f"  - Player {pid} ({data['status']})")

    def display_map(self):
        if not self.location:
            print("Location unknown. Cannot display map.")
            return

        highlighted_map = self.map_template.replace(
            f"[{self.location}]", f"[*{self.location}*]"
        )
        print(highlighted_map)

    def display_help(self):
        print("Available commands:")
        print("  move <destination> - Move to an adjacent room")
        print("  kill <player_id>   - (Impostor only) Kill a player in the same room")
        print("  report            - Report a dead body in your location")
        print("  look              - Display your current location and available exits")
        print("  map               - Display the game map with your current location")
        print("  help              - Show this help message")
        print("  exit/q            - Exit the game")


class GuiGameClient:
    def __init__(self):
        self.player_id = None
        self.location = None
        self.available_exits = []
        self.websocket = None
        self.setup_logging()
        self.running = True
        self.state_data = {}
        self.screen = None
        self.clock = None
        self.font = None
        self.map_structure = self.initialize_map()
        self.room_positions = self.define_room_positions()
        self.selected_player = None  # For selecting players to interact with
        self.show_help = False  # Toggle help display
        self.exit_buttons = {}  # Store button rectangles for click detection
        self.action_buttons = {}  # Store action button rectangles
        self.bodies_in_room = set()  # Track dead bodies in current room

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
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

    def define_room_positions(self):
        # Define positions for each room on the screen
        return {
            "cafeteria": (400, 100),
            "upper_engine": (200, 100),
            "reactor": (100, 200),
            "security": (200, 300),
            "electrical": (300, 400),
            "lower_engine": (200, 500),
            "engine_room": (300, 200),
            "storage": (400, 500),
            "medbay": (500, 200),
        }

    async def connect(self):
        uri = "ws://localhost:8765"
        self.websocket = await websockets.connect(uri)
        logging.info("Connected to the game server.")
        # Initialize Pygame
        self.init_pygame()
        # Create a task for receiving messages
        receive_task = asyncio.create_task(self.receive_messages())
        try:
            # Run the game loop
            await self.game_loop()
        finally:
            # Ensure we close the websocket and cancel the receive task
            receive_task.cancel()
            await self.websocket.close()
            logging.info("Disconnected from the game server.")

    async def receive_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                message_type = data.get("type")
                if message_type == "state":
                    self.player_id = data.get("player_id")
                    payload = data.get("payload")
                    self.location = payload.get("location")
                    self.available_exits = payload.get("available_exits")
                    self.state_data = payload
                    self.bodies_in_room = set(payload.get("bodies_in_room", []))
                elif message_type == "movement":
                    payload = data.get("payload")
                    player = payload.get("player_id")
                    from_room = payload.get("from")
                    to_room = payload.get("to")
                    if player != self.player_id:
                        logging.info(
                            f"Player {player} moved from {from_room} to {to_room}"
                        )
                elif message_type == "player_update":
                    payload = data.get("payload")
                    player = payload.get("player_id")
                    event = payload.get("event")
                    location = payload.get("location")
                    if player != self.player_id:
                        logging.info(f"Player {player} {event} in {location}")
                elif message_type == "error":
                    payload = data.get("payload")
                    error_message = payload.get("message")
                    logging.error(f"Error: {error_message}")
                elif message_type == "event":
                    payload = data.get("payload")
                    event = payload.get("event")
                    if event == "body_reported":
                        logging.info(
                            f"Body reported by Player {payload.get('reporter')}"
                        )
                    elif event == "player_killed":
                        logging.info(f"Player {payload.get('victim')} was killed")
                else:
                    logging.info("Received unknown message type.")
        except websockets.exceptions.ConnectionClosed:
            pass  # Handle the connection being closed
        finally:
            self.running = False  # Stop the game loop

    def init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Among Us - Pygame Client")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

    async def game_loop(self):
        while self.running:
            await self.handle_events()
            self.update_game_state()
            self.render()
            # Limit frame rate to 60 FPS
            await asyncio.sleep(1 / 60)
        pygame.quit()

    async def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                await self.disconnect()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                await self.handle_click(event.pos, event.button)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    self.show_help = not self.show_help
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                    await self.disconnect()
                elif event.key == pygame.K_l:
                    self.display_current_location()
                elif event.key == pygame.K_m:
                    self.display_map()

    async def handle_click(self, position, button):
        # Check action buttons first
        for (action, target_id), button_rect in self.action_buttons.items():
            if button_rect.collidepoint(position):
                if action == "kill":
                    await self.send_kill_command(target_id)
                    return
                elif action == "report":
                    await self.send_report_command()
                    return

        # Check destination buttons
        for exit_name, button_rect in self.exit_buttons.items():
            if button_rect.collidepoint(position):
                await self.send_move_command(exit_name)
                return

        # Check player slots
        if self.state_data:
            players_in_room = self.state_data.get("players_in_room", {})
            grid_cols = 3
            item_width = (self.screen.get_width() - 80) // grid_cols
            item_height = 40
            start_y = 70  # Adjust based on your layout

            for i, pid in enumerate(players_in_room.keys()):
                row = i // grid_cols
                col = i % grid_cols
                x = 40 + (col * item_width)
                y = start_y + (row * (item_height + 5))

                player_rect = pygame.Rect(x, y, item_width - 10, item_height)
                if player_rect.collidepoint(position):
                    if pid != self.player_id:
                        self.selected_player = pid
                        logging.info(f"Selected Player {pid}")
                    return

        self.selected_player = None

    def update_game_state(self):
        # Update any necessary game state here
        pass

    def render(self):
        self.screen.fill((0, 0, 0))  # Clear screen with black background
        self.exit_buttons.clear()  # Clear old exit buttons before adding new ones

        # Constants for layout
        MARGIN = 20
        TOP_INFO_HEIGHT = 30
        PLAYERS_BOX_HEIGHT = 220
        DESTINATIONS_BOX_HEIGHT = 150
        BOX_WIDTH = self.screen.get_width() - (MARGIN * 2)

        # Draw top info bar (role and status)
        if self.state_data:
            role = self.state_data.get("role", "Unknown")
            status = self.state_data.get("status", "Unknown")
            info_text = f"Role: {role} | Status: {status}"
            info_surface = self.font.render(info_text, True, (255, 255, 255))
            self.screen.blit(info_surface, (MARGIN, MARGIN))

        # Draw Players Box
        players_box_rect = pygame.Rect(
            MARGIN, MARGIN + TOP_INFO_HEIGHT, BOX_WIDTH, PLAYERS_BOX_HEIGHT
        )
        pygame.draw.rect(self.screen, (40, 40, 40), players_box_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), players_box_rect, 2)

        # Players box title
        title = self.font.render(
            f"Players in {self.location or 'Unknown'}", True, (200, 200, 200)
        )
        self.screen.blit(title, (MARGIN + 10, MARGIN + TOP_INFO_HEIGHT + 10))

        # Display players in a grid with action buttons
        if self.state_data:
            players_in_room = self.state_data.get("players_in_room", {})
            grid_cols = 3
            item_width = (BOX_WIDTH - 40) // grid_cols
            item_height = 60  # Increased height to accommodate buttons
            start_y = MARGIN + TOP_INFO_HEIGHT + 50

            self.action_buttons.clear()  # Clear old action buttons

            for i, (pid, data) in enumerate(players_in_room.items()):
                if pid == self.player_id:
                    continue  # Skip rendering buttons for self

                row = i // grid_cols
                col = i % grid_cols
                x = MARGIN + 20 + (col * item_width)
                y = start_y + (row * (item_height + 5))

                # Player slot background
                player_rect = pygame.Rect(x, y, item_width - 10, item_height)
                bg_color = (70, 70, 70) if pid == self.selected_player else (50, 50, 50)
                pygame.draw.rect(self.screen, bg_color, player_rect)
                pygame.draw.rect(self.screen, (100, 100, 100), player_rect, 1)

                # Player text
                player_text = f"Player {pid[:8]}"
                text_color = (
                    (100, 255, 100) if data["status"] == "alive" else (255, 100, 100)
                )
                player_surface = self.font.render(player_text, True, text_color)
                text_rect = player_surface.get_rect(
                    midleft=(x + 5, y + 15)  # Adjusted y position
                )
                self.screen.blit(player_surface, text_rect)

                # Add action buttons if conditions are met
                if (
                    data["status"] == "alive"
                    and self.state_data.get("role") == "Impostor"
                    and self.state_data.get("status") == "alive"
                ):
                    kill_button = pygame.Rect(x + 5, y + 30, 60, 20)
                    pygame.draw.rect(self.screen, (200, 0, 0), kill_button)
                    kill_text = self.font.render("Kill", True, (255, 255, 255))
                    kill_text_rect = kill_text.get_rect(center=kill_button.center)
                    self.screen.blit(kill_text, kill_text_rect)
                    self.action_buttons[("kill", pid)] = kill_button

        # Only show report button if there are bodies in the current room
        if self.state_data:
            bodies_in_room = self.state_data.get("bodies_in_room", [])
            if bodies_in_room and self.state_data.get("status") == "alive":
                report_button = pygame.Rect(
                    self.screen.get_width() - 150,
                    MARGIN + TOP_INFO_HEIGHT + 10,
                    100,
                    30,
                )
                pygame.draw.rect(self.screen, (255, 0, 0), report_button)
                report_text = self.font.render("REPORT", True, (255, 255, 255))
                report_text_rect = report_text.get_rect(center=report_button.center)
                self.screen.blit(report_text, report_text_rect)
                self.action_buttons[("report", None)] = report_button

        # Draw Destinations Box
        dest_box_y = self.screen.get_height() - DESTINATIONS_BOX_HEIGHT - MARGIN
        dest_box_rect = pygame.Rect(
            MARGIN, dest_box_y, BOX_WIDTH, DESTINATIONS_BOX_HEIGHT
        )
        pygame.draw.rect(self.screen, (40, 40, 40), dest_box_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), dest_box_rect, 2)

        # Destinations title
        dest_title = self.font.render("Available Destinations", True, (200, 200, 200))
        self.screen.blit(dest_title, (MARGIN + 10, dest_box_y + 10))

        # Display available exits as buttons
        if self.available_exits:
            button_width = min(200, (BOX_WIDTH - 40) // len(self.available_exits))
            button_margin = 10
            total_buttons_width = (button_width + button_margin) * len(
                self.available_exits
            )
            start_x = (self.screen.get_width() - total_buttons_width) // 2

            for i, exit_name in enumerate(self.available_exits):
                x = start_x + (i * (button_width + button_margin))
                y = dest_box_y + 50

                # Button background
                button_rect = pygame.Rect(x, y, button_width, 40)
                pygame.draw.rect(self.screen, (0, 50, 100), button_rect)
                pygame.draw.rect(self.screen, (0, 100, 200), button_rect, 2)

                # Exit text
                exit_surface = self.font.render(exit_name, True, (200, 200, 255))
                text_rect = exit_surface.get_rect(center=button_rect.center)
                self.screen.blit(exit_surface, text_rect)

                # Store button rect for click detection
                self.exit_buttons[exit_name] = button_rect

        # Display help hint
        help_text = "Press H for help"
        help_surface = self.font.render(help_text, True, (150, 150, 150))
        help_rect = help_surface.get_rect(
            bottomright=(self.screen.get_width() - MARGIN, self.screen.get_height() - 5)
        )
        self.screen.blit(help_surface, help_rect)

        pygame.display.flip()

    def render_help(self):
        help_text_lines = [
            "Controls:",
            "Left-click on adjacent rooms to move.",
            "Left-click on a player to select.",
            "Right-click to perform an action on selected player (kill).",
            "Middle-click to report a dead body.",
            "Press 'h' to toggle this help.",
            "Press 'l' to display current location.",
            "Press 'm' to display the map.",
            "Press 'Esc' to exit the game.",
        ]
        y_offset = 200
        for line in help_text_lines:
            help_surface = self.font.render(line, True, (255, 255, 255))
            self.screen.blit(help_surface, (50, y_offset))
            y_offset += 30

    def display_current_location(self):
        if not self.location:
            logging.info("Waiting for game state...")
            return

        logging.info(f"Current Location: {self.location}")
        if self.state_data:
            role = self.state_data.get("role", "Unknown")
            status = self.state_data.get("status", "Unknown")
            logging.info(f"Role: {role}")
            logging.info(f"Status: {status}")

            players_in_room = self.state_data.get("players_in_room", {})
            if players_in_room:
                logging.info("Players in this room:")
                for pid, data in players_in_room.items():
                    if pid != self.player_id:
                        logging.info(f"  - Player {pid} ({data['status']})")

    def display_map(self):
        logging.info("Map is displayed on the game screen.")

    async def send_move_command(self, destination):
        if self.player_id is None:
            logging.info("You are not connected to the server yet.")
            return
        action_message = {
            "type": "action",
            "payload": {"action": "move", "destination": destination},
            "player_id": self.player_id,
        }
        await self.websocket.send(json.dumps(action_message))

    async def send_kill_command(self, target_id):
        if target_id:
            action_message = {
                "type": "action",
                "payload": {"action": "kill", "target": target_id},
                "player_id": self.player_id,
            }
            await self.websocket.send(json.dumps(action_message))
        else:
            logging.info("No player selected to kill.")

    async def send_report_command(self):
        action_message = {
            "type": "action",
            "payload": {"action": "report"},
            "player_id": self.player_id,
        }
        await self.websocket.send(json.dumps(action_message))

    async def disconnect(self):
        self.running = False
        if self.websocket is not None and not self.websocket.closed:
            await self.websocket.close()
        logging.info("You have exited the game.")


def start_gui_client():
    client = GuiGameClient()
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print("\nClient closed.")
        sys.exit()


def start_server():
    game_server = GameServer()

    asyncio.run(game_server.start_server())


def start_cli_client():
    client = CliGameClient()
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print("\nClient closed.")


# python game.py start_server
# python game.py start_cli_client
# python game.py start_gui_client
if __name__ == "__main__":
    fire.Fire()
