import asyncio
import websockets
import uuid
import json
from dataclasses import dataclass, asdict
import pygame
import logging
from typing import Dict, Set, Optional

# Data Models
@dataclass
class Player:
    id: str
    location: str
    role: str = "Crewmate"
    is_alive: bool = True

@dataclass
class GameState:
    players: Dict[str, Player]
    bodies: Set[str]
    map_layout: Dict[str, list]

    def to_dict(self):
        return {
            "players": {pid: asdict(p) for pid, p in self.players.items()},
            "bodies": list(self.bodies),
            "map_layout": self.map_layout
        }

class GameServer:
    def __init__(self):
        self.state = GameState(
            players={},
            bodies=set(),
            map_layout={
                "cafeteria": ["storage", "medbay"],
                "storage": ["cafeteria", "electrical"],
                "electrical": ["storage", "reactor"],
                "reactor": ["electrical", "medbay"],
                "medbay": ["reactor", "cafeteria"]
            }
        )
        self.connections = {}  # websocket -> player_id

    def assign_roles(self):
        import random
        player_ids = list(self.state.players.keys())
        if len(player_ids) >= 4:
            impostor = random.choice(player_ids)
            self.state.players[impostor].role = "Impostor"

    async def handle_connection(self, websocket):
        player_id = str(uuid.uuid4())
        player = Player(id=player_id, location="cafeteria")
        self.state.players[player_id] = player
        self.connections[websocket] = player_id

        if len(self.state.players) >= 4:
            self.assign_roles()

        try:
            await self.broadcast_state()
            async for message in websocket:
                await self.handle_message(websocket, message)
        finally:
            if player_id in self.state.players:
                del self.state.players[player_id]
            del self.connections[websocket]
            await self.broadcast_state()

    async def handle_message(self, websocket, message):
        data = json.loads(message)
        player_id = self.connections[websocket]
        player = self.state.players[player_id]

        if data["action"] == "move":
            new_location = data["location"]
            if new_location in self.state.map_layout[player.location]:
                player.location = new_location
                await self.broadcast_state()

        elif data["action"] == "kill":
            if player.role == "Impostor" and player.is_alive:
                target_id = data["target"]
                target = self.state.players.get(target_id)
                if target and target.location == player.location and target.is_alive:
                    target.is_alive = False
                    self.state.bodies.add(target_id)
                    await self.broadcast_state()

        elif data["action"] == "report":
            if player.is_alive:
                for body_id in list(self.state.bodies):
                    if self.state.players[body_id].location == player.location:
                        self.state.bodies.remove(body_id)
                        await self.broadcast_state()

    async def broadcast_state(self):
        if not self.connections:
            return
        state_msg = json.dumps({"type": "state", "data": self.state.to_dict()})
        await asyncio.gather(
            *[ws.send(state_msg) for ws in self.connections]
        )

    async def start(self):
        async with websockets.serve(self.handle_connection, "localhost", 8765):
            await asyncio.Future()  # run forever

class GameClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.websocket = None
        self.player_id = None
        self.game_state = None
        self.running = True
        self.selected_player = None  # For targeting kills
        self.movement_cooldown = 0  # Add cooldown for movement

        # Room positions on screen
        self.room_positions = {
            "cafeteria": (400, 100),
            "storage": (400, 300),
            "electrical": (200, 300),
            "reactor": (200, 500),
            "medbay": (600, 300)
        }

        # Room navigation mapping
        self.room_directions = {
            "cafeteria": {"w": None, "a": None, "s": "storage", "d": "medbay"},
            "storage": {"w": "cafeteria", "a": "electrical", "s": None, "d": None},
            "electrical": {"w": None, "a": None, "s": "reactor", "d": "storage"},
            "reactor": {"w": "electrical", "a": None, "s": None, "d": "medbay"},
            "medbay": {"w": "cafeteria", "a": "reactor", "s": None, "d": None}
        }

        # UI element positions
        self.action_button_rect = pygame.Rect(650, 500, 100, 40)

    def draw_room(self, name, position, is_current):
        color = (100, 100, 255) if is_current else (50, 50, 50)
        pygame.draw.circle(self.screen, color, position, 30)
        text = self.font.render(name, True, (255, 255, 255))
        text_rect = text.get_rect(center=(position[0], position[1] + 50))
        self.screen.blit(text, text_rect)

    def draw_connections(self, map_layout):
        for room, connections in map_layout.items():
            start = self.room_positions[room]
            for connected_room in connections:
                end = self.room_positions[connected_room]
                pygame.draw.line(self.screen, (100, 100, 100), start, end, 2)

    def draw_player_list(self):
        y = 50
        click_areas = {}
        current_location = self.game_state["players"][self.player_id]["location"]
        my_role = self.game_state["players"][self.player_id]["role"]

        for pid, player in self.game_state["players"].items():
            if pid == self.player_id:
                role = f"You ({player['role']})"
            else:
                role = "Player"

            status = "Dead" if not player["is_alive"] else player["location"]
            text = f"{role} - {status}"

            if (player["location"] == current_location and 
                pid != self.player_id and 
                player["is_alive"]):
                color = (0, 255, 0)
                if pid == self.selected_player:
                    color = (255, 255, 0)
            else:
                color = (255, 0, 0) if not player["is_alive"] else (255, 255, 255)

            text_surf = self.font.render(text, True, color)
            text_rect = pygame.Rect(10, y, 300, 25)
            self.screen.blit(text_surf, (10, y))

            if player["location"] == current_location and player["is_alive"] and pid != self.player_id:
                click_areas[text_rect] = pid

            y += 30

        return click_areas

    def draw_action_buttons(self):
        if not self.game_state or not self.player_id:
            return

        current_player = self.game_state["players"][self.player_id]
        current_location = current_player["location"]

        bodies_in_room = [bid for bid in self.game_state["bodies"] 
                         if self.game_state["players"][bid]["location"] == current_location]

        if bodies_in_room and current_player["is_alive"]:
            pygame.draw.rect(self.screen, (255, 0, 0), self.action_button_rect)
            text = self.font.render("REPORT", True, (255, 255, 255))
            text_rect = text.get_rect(center=self.action_button_rect.center)
            self.screen.blit(text, text_rect)
            return "report"

        if (current_player["role"] == "Impostor" and 
            self.selected_player and 
            current_player["is_alive"]):
            target = self.game_state["players"][self.selected_player]
            if target["location"] == current_location and target["is_alive"]:
                pygame.draw.rect(self.screen, (200, 0, 0), self.action_button_rect)
                text = self.font.render("KILL", True, (255, 255, 255))
                text_rect = text.get_rect(center=self.action_button_rect.center)
                self.screen.blit(text, text_rect)
                return "kill"

        return None

    def draw_controls_help(self):
        help_text = [
            "Controls:",
            "WASD - Move between rooms",
            "SPACE - Report/Kill",
            "Click player name to target"
        ]
        y = 400
        for line in help_text:
            text = self.font.render(line, True, (200, 200, 200))
            self.screen.blit(text, (10, y))
            y += 25

    def render(self):
        self.screen.fill((0, 0, 0))

        if not self.game_state or not self.player_id:
            text = self.font.render("Connecting...", True, (255, 255, 255))
            self.screen.blit(text, (350, 280))
            pygame.display.flip()
            return None, None

        self.draw_connections(self.game_state["map_layout"])
        current_location = self.game_state["players"][self.player_id]["location"]
        for room, pos in self.room_positions.items():
            self.draw_room(room, pos, room == current_location)

        click_areas = self.draw_player_list()
        action_type = self.draw_action_buttons()
        self.draw_controls_help()

        pygame.display.flip()
        return click_areas, action_type

    async def handle_movement(self):
        if self.movement_cooldown > 0:
            self.movement_cooldown -= 1
            return

        keys = pygame.key.get_pressed()
        current_location = self.game_state["players"][self.player_id]["location"]
        direction = None

        if keys[pygame.K_w]:
            direction = "w"
        elif keys[pygame.K_s]:
            direction = "s"
        elif keys[pygame.K_a]:
            direction = "a"
        elif keys[pygame.K_d]:
            direction = "d"

        if direction and self.room_directions[current_location][direction]:
            new_location = self.room_directions[current_location][direction]
            await self.websocket.send(json.dumps({
                "action": "move",
                "location": new_location
            }))
            self.movement_cooldown = 15  # Add delay between movements

    async def connect(self):
        async with websockets.connect("ws://localhost:8765") as websocket:
            self.websocket = websocket
            try:
                async for message in websocket:
                    data = json.loads(message)
                    if data["type"] == "state":
                        self.game_state = data["data"]
                        if not self.player_id:
                            for pid, player in self.game_state["players"].items():
                                if player["location"] == "cafeteria":
                                    self.player_id = pid
                                    break
                        await self.game_loop()
            except websockets.exceptions.ConnectionClosed:
                self.running = False

    async def game_loop(self):
        while self.running:
            click_areas, action_type = self.render()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    await self.handle_click(event.pos, click_areas, action_type)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    await self.handle_action(action_type)

            await self.handle_movement()
            await asyncio.sleep(1/60)

    async def handle_action(self, action_type):
        if action_type == "kill" and self.selected_player:
            await self.websocket.send(json.dumps({
                "action": "kill",
                "target": self.selected_player
            }))
            self.selected_player = None
        elif action_type == "report":
            await self.websocket.send(json.dumps({
                "action": "report"
            }))

    # async def handle_click(self, pos, click_areas, action_type):
    #     if not self.game_state or not self.player_id:
    #         return

    #     # Check for clicks on player names
    #     click_pos = pygame.Rect(pos[0], pos[1], 1, 1)
    #     for area_rect, pid in click_areas.items() if click_areas else []:
    #         if area_rect.colliderect(click_pos):
    #             self.selected_player = pid
    #             return

    def draw_player_list(self):
        y = 50
        click_areas = []  # Changed from dict to list of tuples
        current_location = self.game_state["players"][self.player_id]["location"]
        my_role = self.game_state["players"][self.player_id]["role"]

        for pid, player in self.game_state["players"].items():
            if pid == self.player_id:
                role = f"You ({player['role']})"
            else:
                role = "Player"

            status = "Dead" if not player["is_alive"] else player["location"]
            text = f"{role} - {status}"

            if (
                player["location"] == current_location
                and pid != self.player_id
                and player["is_alive"]
            ):
                color = (0, 255, 0)
                if pid == self.selected_player:
                    color = (255, 255, 0)
            else:
                color = (255, 0, 0) if not player["is_alive"] else (255, 255, 255)

            text_surf = self.font.render(text, True, color)
            text_rect = pygame.Rect(10, y, 300, 25)
            self.screen.blit(text_surf, (10, y))

            if (
                player["location"] == current_location
                and player["is_alive"]
                and pid != self.player_id
            ):
                click_areas.append((text_rect, pid))  # Store as tuple

            y += 30

        return click_areas

    async def handle_click(self, pos, click_areas, action_type):
        if not self.game_state or not self.player_id:
            return

        # Check for clicks on player names
        click_pos = pygame.Rect(pos[0], pos[1], 1, 1)
        for rect, pid in (
            click_areas if click_areas else []
        ):  # Iterate over list of tuples
            if rect.colliderect(click_pos):
                self.selected_player = pid
                return


async def main(mode):
    if mode == "server":
        server = GameServer()
        await server.start()
    else:
        client = GameClient()
        await client.connect()
# python wasd_game.py server
# python wasd_game.py client

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in ["server", "client"]:
        print("Usage: python game.py [server|client]")
        sys.exit(1)
    
    asyncio.run(main(sys.argv[1]))
