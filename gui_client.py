# game_client.py

import asyncio
import websockets
import json
import logging
import pygame
import sys


class GameClient:
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
                elif message_type == "error":
                    payload = data.get("payload")
                    error_message = payload.get("message")
                    logging.error(f"Error: {error_message}")
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
        # Check if a room was clicked
        for room_name, room_pos in self.room_positions.items():
            room_rect = pygame.Rect(room_pos[0] - 50, room_pos[1] - 50, 100, 100)
            if room_rect.collidepoint(position):
                if room_name in self.map_structure.get(self.location, []):
                    await self.send_move_command(room_name)
                elif room_name == self.location:
                    logging.info(f"You are already in {room_name}.")
                else:
                    logging.info(f"Cannot move to {room_name} from {self.location}.")
                break
        else:
            # Check for player interactions
            if self.state_data:
                players_in_room = self.state_data.get("players_in_room", {})
                y_offset = 40
                for pid, data in players_in_room.items():
                    if pid != self.player_id:
                        player_rect = pygame.Rect(10, y_offset, 200, 20)
                        if player_rect.collidepoint(position):
                            self.selected_player = pid
                            logging.info(f"Selected Player {pid}")
                            break
                        y_offset += 30
                else:
                    self.selected_player = None

            # Perform actions based on mouse button
            if button == 1:  # Left-click
                pass  # No action
            elif button == 3:  # Right-click
                if self.selected_player:
                    await self.send_kill_command(self.selected_player)
                else:
                    logging.info("No player selected to kill.")
            elif button == 2:  # Middle-click
                await self.send_report_command()

    def update_game_state(self):
        # Update any necessary game state here
        pass

    def render(self):
        self.screen.fill((0, 0, 0))  # Clear screen with black

        # Draw connections between rooms
        for room_name, exits in self.map_structure.items():
            start_pos = self.room_positions[room_name]
            for exit_room in exits:
                end_pos = self.room_positions[exit_room]
                pygame.draw.line(self.screen, (255, 255, 255), start_pos, end_pos, 2)

        # Draw rooms
        for room_name, room_pos in self.room_positions.items():
            color = (100, 100, 100)  # Default room color
            if room_name == self.location:
                color = (0, 255, 0)  # Current location
            elif room_name in self.map_structure.get(self.location, []):
                color = (0, 0, 255)  # Adjacent rooms
            pygame.draw.circle(self.screen, color, room_pos, 50)
            text = self.font.render(room_name, True, (255, 255, 255))
            text_rect = text.get_rect(center=room_pos)
            self.screen.blit(text, text_rect)

        # Display player info
        if self.state_data:
            role = self.state_data.get("role", "Unknown")
            status = self.state_data.get("status", "Unknown")
            info_text = f"Role: {role} | Status: {status}"
            info_surface = self.font.render(info_text, True, (255, 255, 255))
            self.screen.blit(info_surface, (10, 10))

            # Display players in the same room
            players_in_room = self.state_data.get("players_in_room", {})
            y_offset = 40
            header_text = "Players in this room:"
            header_surface = self.font.render(header_text, True, (255, 255, 0))
            self.screen.blit(header_surface, (10, y_offset))
            y_offset += 20

            for pid, data in players_in_room.items():
                if pid != self.player_id:
                    player_text = f"Player {pid} ({data['status']})"
                    player_surface = self.font.render(
                        player_text, True, (255, 255, 255)
                    )
                    player_rect = player_surface.get_rect(topleft=(10, y_offset))
                    self.screen.blit(player_surface, player_rect)
                    if pid == self.selected_player:
                        # Highlight selected player
                        pygame.draw.rect(self.screen, (255, 0, 0), player_rect, 2)
                    y_offset += 30

        # Display help information
        if self.show_help:
            self.render_help()

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
        # Since the current location is always displayed, we can log it
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
        # The map is always displayed in the game window
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


def start_client():
    client = GameClient()
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print("\nClient closed.")
        sys.exit()


if __name__ == "__main__":
    start_client()
