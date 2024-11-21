# client.py

import asyncio
import websockets
import json
import sys

my_player_id = None  # Global variable to store your player ID

async def game_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        print("Connected to the game server.")

        # Create tasks for receiving messages and handling user input
        receive_task = asyncio.create_task(receive_messages(websocket))
        input_task = asyncio.create_task(user_input_handler(websocket))

        # Wait until one of the tasks is completed
        done, pending = await asyncio.wait(
            [receive_task, input_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel the pending task
        for task in pending:
            task.cancel()

async def receive_messages(websocket):
    try:
        async for message in websocket:
            data = json.loads(message)
            await handle_server_message(data)
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed by the server.")
        sys.exit()

async def handle_server_message(data):
    global my_player_id
    message_type = data.get('type')
    if message_type == "player_connected":
        print(f"Player {data['player_id']} connected at location {data['location']}.")
    elif message_type == "player_disconnected":
        print(f"Player {data['player_id']} disconnected.")
    elif message_type == "game_started":
        print("Game has started!")
    elif message_type == "state_update":
        if 'player_id' in data:
            my_player_id = data['player_id']
            print(f"Your player ID is {my_player_id}")
        print("State Update:")
        print(f"  Location: {data['location']}")
        print(f"  Players in room: {', '.join(data['players_in_room'])}")
        print(f"  Available exits: {', '.join(data['available_exits'])}")
        print(f"  Role: {data['role']}")
        print(f"  Status: {data['status']}")
        print(f"  Bodies in room: {', '.join(data['bodies_in_room'])}")
    elif message_type == "player_moved":
        print(f"Player {data['player_id']} moved from {data['from']} to {data['to']}.")
    elif message_type == "player_killed":
        print(f"Player {data['victim']} was killed by {data['killer']} at {data['location']}.")
    elif message_type == "chat_message":
        print(f"{data['player_id']}: {data['message']}")
    elif message_type == "error":
        print(f"Error: {data['message']}")
    elif message_type == "phase_change":
        print(f"Phase changed to {data['phase']}. Duration: {data['duration']} seconds.")
    elif message_type == "vote_received":
        print("Your vote has been received.")
    elif message_type == "player_ejected":
        print(f"Player {data['player_id']} was ejected. Role: {data['role']}.")
    elif message_type == "no_ejection":
        print(data['message'])
    else:
        print(f"Unknown message type: {message_type}")

async def user_input_handler(websocket):
    loop = asyncio.get_event_loop()
    while True:
        # Read user input asynchronously
        user_input = await loop.run_in_executor(None, sys.stdin.readline)
        user_input = user_input.strip()
        if user_input:
            await process_user_input(user_input, websocket)

async def process_user_input(user_input, websocket):
    if user_input.startswith("move "):
        destination = user_input[5:].strip()
        message = {
            "action": "move",
            "destination": destination
        }
        await websocket.send(json.dumps(message))
    elif user_input.startswith("kill "):
        target_id = user_input[5:].strip()
        message = {
            "action": "kill",
            "target": target_id
        }
        await websocket.send(json.dumps(message))
    elif user_input == "report":
        message = {
            "action": "report"
        }
        await websocket.send(json.dumps(message))
    elif user_input.startswith("vote "):
        voted_player = user_input[5:].strip()
        message = {
            "action": "vote",
            "vote": voted_player
        }
        await websocket.send(json.dumps(message))
    elif user_input == "call_meeting":
        message = {
            "action": "call_meeting"
        }
        await websocket.send(json.dumps(message))
    elif user_input.startswith("chat "):
        message_text = user_input[5:].strip()
        message = {
            "action": "chat",
            "message": message_text
        }
        await websocket.send(json.dumps(message))
    elif user_input == "quit":
        print("Exiting game.")
        await websocket.close()
        sys.exit()
    else:
        print("Invalid command. Available commands are:")
        print("  move <destination>")
        print("  kill <target_id>")
        print("  report")
        print("  vote <player_id>")
        print("  call_meeting")
        print("  chat <message>")
        print("  quit")

if __name__ == "__main__":
    asyncio.run(game_client())
