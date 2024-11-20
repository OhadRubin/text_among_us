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
        # Initialize room occupancy tracking
        self.room_occupancy = {room_name: 0 for room_name in self.map_structure.keys()}
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

    def generate_unique_id(self):
        return str(uuid.uuid4())

    def can_enter_room(self, room_name):
        capacity = 10 if room_name == 'cafeteria' else 5
        return self.room_occupancy[room_name] < capacity

    async def handle_connection(self, websocket, path):
        player_id = self.generate_unique_id()
        initial_location = 'cafeteria'
        self.players[player_id] = {
            'websocket': websocket,
            'location': initial_location
        }
        self.room_occupancy[initial_location] += 1
        logging.info(f"Player {player_id} connected. Room occupancy: {self.room_occupancy}")
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
        if self.validate_move(current_location, destination) and self.can_enter_room(destination):
            # Update room occupancy
            self.room_occupancy[current_location] -= 1
            self.room_occupancy[destination] += 1
            # Update player location
            self.players[player_id]['location'] = destination
            await self.send_state_update(player_id)
            logging.info(f"Player {player_id} moved to {destination}. Room occupancy: {self.room_occupancy}")
        else:
            error_msg = "Room is full" if not self.can_enter_room(destination) else "Invalid move"
            await self.send_error(player_id, error_msg)

    async def send_state_update(self, player_id):
        location = self.players[player_id]['location']
        available_exits = self.map_structure.get(location, [])
        exits_status = {
            exit: "full" if not self.can_enter_room(exit) else "available"
            for exit in available_exits
        }
        state_message = {
            "type": "state",
            "payload": {
                "location": location,
                "players_in_room": self.room_occupancy[location],
                "available_exits": available_exits,
                "room_capacity": 10 if location == 'cafeteria' else 5,
                "exits_status": exits_status
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
                elif message_type == "error":
                    payload = data.get("payload")
                    error_message = payload.get("message")
                    print(f"Error: {error_message}")
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
            if command == "move":
                if args:
                    destination = args[0]
                    await self.send_move_command(destination)
                else:
                    print("Usage: move <destination>")
            elif command == "look":
                self.display_current_location()
            elif command == "map":
                self.display_map()
            elif command == "help":
                self.display_help()
            elif command in ["exit", "q"]:
                await self.disconnect()
                break
            else:
                print("Unknown command. Type 'help' for a list of commands.")

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

    async def disconnect(self):
        self.running = False
        await self.websocket.close()
        print("You have exited the game.")

    def display_current_location(self):
        if not self.location:
            print("Waiting for game state...")
            return

        print(f"\nCurrent Location: {self.location}")
        if hasattr(self, 'state_data'):
            players_in_room = self.state_data.get('players_in_room', 0)
            room_capacity = self.state_data.get('room_capacity', 5)
            exits_status = self.state_data.get('exits_status', {})
            
            print(f"Players here: {players_in_room}/{room_capacity}")
            print("Available Exits:")
            for exit, status in exits_status.items():
                status_indicator = " (FULL)" if status == "full" else ""
                print(f"  - {exit}{status_indicator}")
        else:
            print("Available Exits:")
            for exit in self.available_exits:
                print(f"  - {exit}")

    def display_map(self):
        if not self.location:
            print("Location unknown. Cannot display map.")
            return
        
        highlighted_map = self.map_template.replace(
            f'[{self.location}]',
            f'[*{self.location}*]'
        )
        print(highlighted_map)

    def display_help(self):
        print("Available commands:")
        print("  move <destination> - Move to an adjacent room.")
        print("  look               - Display your current location and available exits.")
        print("  map                - Display the game map with your current location.")
        print("  help               - Show this help message.")
        print("  exit/q             - Exit the game.")


def start_server():
    game_server = GameServer()
    
    asyncio.run(game_server.start_server())

def start_client():
    client = GameClient()
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        print("\nClient closed.")


# usage: python game.py start_server
# usage: python game.py start_client
if __name__ == "__main__":
    fire.Fire()
