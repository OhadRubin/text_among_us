from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import websockets
import logging

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameProxy:
    def __init__(self):
        self.game_server_uri = "ws://localhost:8765"
        self.clients = {}  # Store WebSocket connections

    async def connect_to_game_server(self, client_ws: WebSocket):
        try:
            async with websockets.connect(self.game_server_uri) as game_ws:
                # Store both WebSocket connections
                self.clients[client_ws] = game_ws

                # Create tasks for bidirectional message forwarding
                client_to_game = asyncio.create_task(
                    self.forward_messages(client_ws, game_ws)
                )
                game_to_client = asyncio.create_task(
                    self.forward_messages(game_ws, client_ws)
                )

                # Wait for either connection to close
                await asyncio.gather(client_to_game, game_to_client)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection to game server closed")
        except Exception as e:
            logger.error(f"Error in game server connection: {str(e)}")
        finally:
            if client_ws in self.clients:
                del self.clients[client_ws]

    async def forward_messages(self, source_ws, target_ws):
        try:
            async for message in source_ws:
                await target_ws.send(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error forwarding message: {str(e)}")


game_proxy = GameProxy()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await game_proxy.connect_to_game_server(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if websocket in game_proxy.clients:
            del game_proxy.clients[websocket]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
