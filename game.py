# server.py

import asyncio
import websockets
import uuid
import json
import logging
import fire

class GameServer:
    def __init__(self):
        self.players = {}  # key: player_id, value: dict with 'websocket' and 'location'
        self.map_structure = self.initialize_map()
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('game_server.log'),
                logging.StreamHandler()
            ]
        )

    def initialize_map(self):
        # Simplified map structure
        return {
            'cafeteria': ['upper_engine', 'medbay'],
            'upper_engine': ['cafeteria', 'reactor'],
            'medbay': ['cafeteria'],
            'reactor': ['upper_engine']
        }

    def generate_unique_id(self):
        return str(uuid.uuid4())

    async def handle_connection(self, websocket, path):
        player_id = self.generate_unique_id()
        self.players[player_id] = {
            'websocket': websocket,
            'location': 'cafeteria'
        }
        logging.info(f"Player {player_id} connected.")
        try:
            await self.send_state_update(player_id)
            async for message in websocket:
                await self.process_message(message, player_id)
        except websockets.exceptions.ConnectionClosedError:
            logging.warning(f"Connection closed unexpectedly for player {player_id}.")
        finally:
            del self.players[player_id]
            logging.info(f"Player {player_id} disconnected.")

    async def process_message(self, message, player_id):
        data = json.loads(message)
        if data['type'] == 'action' and data['payload']['action'] == 'move':
            destination = data['payload']['destination']
            await self.handle_move(player_id, destination)
        else:
            await self.send_error(player_id, "Invalid action.")

    def validate_move(self, current_location, destination):
        return destination in self.map_structure.get(current_location, [])

    async def handle_move(self, player_id, destination):
        current_location = self.players[player_id]['location']
        if self.validate_move(current_location, destination):
            self.players[player_id]['location'] = destination
            await self.send_state_update(player_id)
            logging.info(f"Player {player_id} moved to {destination}.")
        else:
            await self.send_error(player_id, "Invalid move.")

    async def send_state_update(self, player_id):
        location = self.players[player_id]['location']
        available_exits = self.map_structure.get(location, [])
        state_message = {
            "type": "state",
            "payload": {
                "location": location,
                "available_exits": available_exits
            },
            "player_id": player_id
        }
        websocket = self.players[player_id]['websocket']
        await websocket.send(json.dumps(state_message))

    async def send_error(self, player_id, message):
        error_message = {
            "type": "error",
            "payload": {
                "message": message
            },
            "player_id": player_id
        }
        websocket = self.players[player_id]['websocket']
        await websocket.send(json.dumps(error_message))

    async def start_server(self):
        server = await websockets.serve(self.handle_connection, 'localhost', 8765)
        logging.info("Server started on ws://localhost:8765")
        await server.wait_closed()


class GameClient:
    def __init__(self):
        self.player_id = None
        self.location = None
        self.available_exits = []
        self.websocket = None
        self.setup_logging()

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
            await asyncio.gather(listener_task, input_task)

    async def receive_messages(self):
        async for message in self.websocket:
            data = json.loads(message)
            message_type = data.get("type")
            if message_type == "state":
                self.player_id = data.get("player_id")
                payload = data.get("payload")
                self.location = payload.get("location")
                self.available_exits = payload.get("available_exits")
                self.display_current_location()
            elif message_type == "error":
                payload = data.get("payload")
                error_message = payload.get("message")
                print(f"Error: {error_message}")
            else:
                print("Received unknown message type.")

    def parse_command(self, input_line):
        tokens = input_line.strip().split()
        if not tokens:
            return None, None
        command = tokens[0]
        args = tokens[1:]
        return command, args

    async def send_commands(self):
        while True:
            try:
                input_line = await asyncio.get_event_loop().run_in_executor(
                    None, input, "> "
                )
                command, args = self.parse_command(input_line)
                if command == "move":
                    if args:
                        destination = args[0]
                        await self.send_move_command(destination)
                    else:
                        print("Usage: move <destination>")
                elif command == "look":
                    self.display_current_location()
                elif command == "help":
                    self.display_help()
                else:
                    print("Unknown command. Type 'help' for a list of commands.")
            except KeyboardInterrupt:
                print("\nExiting game...")
                return

    async def send_move_command(self, destination):
        action_message = {
            "type": "action",
            "payload": {"action": "move", "destination": destination},
            "player_id": self.player_id,
        }
        await self.websocket.send(json.dumps(action_message))

    def display_current_location(self):
        if self.location and self.available_exits:
            print(f"Current Location: {self.location}")
            print("Available Exits:")
            for exit in self.available_exits:
                print(f"  - {exit}")
        else:
            print("Waiting for game state...")

    def display_help(self):
        print("Available commands:")
        print("  move <destination> - Move to an adjacent room.")
        print(
            "  look               - Display your current location and available exits."
        )
        print("  help               - Show this help message.")


def start_server():
    game_server = GameServer()
    asyncio.run(game_server.start_server())
def start_client():
    client = GameClient()
    asyncio.run(client.connect())

# usage: python game.py start_server
# usage: python game.py start_client
if __name__ == "__main__":
    fire.Fire()
