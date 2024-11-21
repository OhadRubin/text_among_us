Certainly! I'll help you implement the meeting room functionality. We'll modify the server code so that when a body is reported, all alive players are moved to the cafeteria, and they are notified about the meeting. Here's how you can do it:

1. **Add a meeting state to the server** to track if a meeting is in progress.
2. **Modify the `handle_report` method** to start the meeting when a body is reported.
3. **Implement `start_meeting` and `end_meeting` methods** to manage the meeting flow.
4. **Adjust action handling** to prevent players from performing actions during a meeting.
5. **Update client code** to handle the new meeting events and state updates.

---

### **1. Add a Meeting State**

In the `GameServer` class, add a new attribute `self.meeting_in_progress` to track if a meeting is currently happening.

```python
class GameServer:
    def __init__(self):
        # ... existing initialization code ...
        self.meeting_in_progress = False  # Tracks if a meeting is in progress
```

### **2. Modify the `handle_report` Method**

When a body is reported, initiate the meeting by calling `start_meeting`.

```python
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

    # Start the meeting
    await self.start_meeting(reporter_id, reported_bodies)
```

### **3. Implement `start_meeting` and `end_meeting` Methods**

Create methods to handle the meeting logic, moving players to the cafeteria and notifying them.

```python
async def start_meeting(self, reporter_id, reported_bodies):
    self.meeting_in_progress = True

    # Move all alive players to the cafeteria
    for pid, pdata in self.players.items():
        if self.player_status.get(pid) == "alive":
            current_location = pdata["location"]
            if current_location != "cafeteria":
                # Update room occupancy
                self.room_occupancy[current_location] -= 1
                self.room_occupancy["cafeteria"] += 1
                # Update player location
                pdata["location"] = "cafeteria"
                # Send state update to player
                await self.send_state_update(pid)

    # Notify all players about the meeting
    await self.broadcast_message(
        {
            "type": "event",
            "payload": {
                "event": "meeting_started",
                "reporter": reporter_id,
                "bodies": reported_bodies,
            },
        }
    )

    # For simplicity, end the meeting immediately
    await self.end_meeting()

async def end_meeting(self):
    self.meeting_in_progress = False

    # Notify all players that the meeting has ended
    await self.broadcast_message(
        {
            "type": "event",
            "payload": {
                "event": "meeting_ended",
            },
        }
    )
```

### **4. Prevent Actions During Meetings**

Modify the `process_message` method to prevent players from performing actions while a meeting is in progress.

```python
async def process_message(self, message, player_id):
    data = json.loads(message)
    if self.meeting_in_progress:
        await self.send_error(player_id, "Cannot perform actions during a meeting.")
        return

    if data["type"] == "action":
        if self.player_status.get(player_id) != "alive":
            await self.send_error(
                player_id, "You are dead and cannot perform actions."
            )
            return
        action = data["payload"]["action"]
        # ... existing action handling ...
```

### **5. Update Client Code**

#### **CLI Client (`CliGameClient`)**

In the `receive_messages` method, handle the new meeting events.

```python
async def receive_messages(self):
    try:
        async for message in self.websocket:
            data = json.loads(message)
            message_type = data.get("type")
            if message_type == "event":
                payload = data.get("payload")
                event = payload.get("event")
                if event == "meeting_started":
                    print("\nMeeting has started. You are in the cafeteria.")
                    print("> ", end="", flush=True)
                elif event == "meeting_ended":
                    print("\nMeeting has ended. Continue playing.")
                    print("> ", end="", flush=True)
            # ... existing message handling ...
```

#### **GUI Client (`GuiGameClient`)**

Similarly, update the `receive_messages` method in the GUI client.

```python
async def receive_messages(self):
    try:
        async for message in self.websocket:
            data = json.loads(message)
            message_type = data.get("type")
            if message_type == "event":
                payload = data.get("payload")
                event = payload.get("event")
                if event == "meeting_started":
                    logging.info("Meeting has started. You are in the cafeteria.")
                    # Update state accordingly
                elif event == "meeting_ended":
                    logging.info("Meeting has ended. Continue playing.")
            # ... existing message handling ...
```

You may also want to update the rendering logic to reflect that a meeting is in progress, possibly by displaying a message or changing the UI state.

---

### **Full Updated Server Code Snippet**

Here's how the updated server code looks with the changes:

```python
class GameServer:
    def __init__(self):
        # ... existing initialization code ...
        self.meeting_in_progress = False  # Tracks if a meeting is in progress

    # ... existing methods ...

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

        # Start the meeting
        await self.start_meeting(reporter_id, reported_bodies)

    async def start_meeting(self, reporter_id, reported_bodies):
        self.meeting_in_progress = True

        # Move all alive players to the cafeteria
        for pid, pdata in self.players.items():
            if self.player_status.get(pid) == "alive":
                current_location = pdata["location"]
                if current_location != "cafeteria":
                    # Update room occupancy
                    self.room_occupancy[current_location] -= 1
                    self.room_occupancy["cafeteria"] += 1
                    # Update player location
                    pdata["location"] = "cafeteria"
                    # Send state update to player
                    await self.send_state_update(pid)

        # Notify all players about the meeting
        await self.broadcast_message(
            {
                "type": "event",
                "payload": {
                    "event": "meeting_started",
                    "reporter": reporter_id,
                    "bodies": reported_bodies,
                },
            }
        )

        # For now, end the meeting immediately
        await self.end_meeting()

    async def end_meeting(self):
        self.meeting_in_progress = False

        # Notify all players that the meeting has ended
        await self.broadcast_message(
            {
                "type": "event",
                "payload": {
                    "event": "meeting_ended",
                },
            }
        )

    async def process_message(self, message, player_id):
        data = json.loads(message)
        if self.meeting_in_progress:
            await self.send_error(player_id, "Cannot perform actions during a meeting.")
            return

        if data["type"] == "action":
            if self.player_status.get(player_id) != "alive":
                await self.send_error(
                    player_id, "You are dead and cannot perform actions."
                )
                return
            action = data["payload"]["action"]
            # ... existing action handling ...
```

---

### **Testing the Functionality**

To test the new meeting functionality:

1. **Start the Server**

   ```bash
   python game.py start_server
   ```

2. **Connect Multiple Clients**

   Open multiple CLI or GUI clients:

   ```bash
   python game.py start_cli_client
   ```

3. **Trigger a Report**

   - Have an impostor kill a crewmate.
   - As another player in the same room, use the `report` command.

4. **Observe the Meeting**

   - All alive players should receive a notification about the meeting.
   - They should all be moved to the cafeteria.
   - Players should be prevented from performing actions during the meeting.

### **Next Steps**

- **Implement Voting Mechanics**: Allow players to discuss and vote to eject a player during the meeting.
- **Add Discussion Time**: Introduce a timer for the discussion phase before voting.
- **Enable Chat During Meetings**: Allow players to communicate during the meeting to discuss who they think is the impostor.
- **Handle Meeting Conclusion**: After voting, apply the results (e.g., eject a player) and resume the game.

### **Note**

This implementation is a basic version of the meeting functionality. It moves all alive players to the cafeteria and notifies them of the meeting. Actions are disabled during the meeting to simulate the pause in gameplay. You can expand upon this foundation by adding more features like voting and discussions to enrich the gameplay experience.

---

Let me know if you need further assistance or additional features implemented!