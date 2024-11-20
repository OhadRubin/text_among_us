# Expanded Specification for Progressive Implementation

To facilitate a step-by-step development of the Text-Based Among Us game, the entire project is divided into **six major updates**. Each update builds upon the previous ones, gradually introducing new features and complexities. This approach allows for testing and validation at each stage, ensuring a robust final product.

---

## **Update 1: Basic Client-Server Communication and Movement**

### **Objective**

Establish the foundational client-server architecture and enable basic player movement within a simplified map.

### **Server Components**

- **WebSocket Server Setup**
  - Implement an **asynchronous WebSocket server** using `asyncio` and the `websockets` library.
  - Handle player connections and disconnections gracefully.

- **Player Session Management**
  - Assign a **unique `player_id`** to each connected player.
  - Maintain a **dictionary** of connected players with their attributes:
    - `player_id`
    - `location` (initially a default starting point)

- **Map Implementation**
  - Create a **simplified graph-based map** consisting of interconnected rooms and corridors.
  - Represent the map as a **dictionary or adjacency list** for easy navigation.

- **Movement Handling**
  - Process movement commands (`move north`, `move south`, etc.).
  - Update player locations on the server.
  - Notify nearby players of movements if applicable.

### **Client Components**

- **CLI Interface**
  - Develop a **command-line interface** for player input.
  - Accept movement commands and display feedback.

- **HUD Display**
  - Show the player's current location.
  - List available directions for movement.
  - Display nearby players if any are present.

### **Communication Protocol**

- **Message Types**
  - `action`: Client-to-server messages for player actions (e.g., movement).
  - `state`: Server-to-client messages for game state updates.

- **Message Format**
  ```json
  {
    "type": "action" | "state",
    "payload": { ... },
    "timestamp": "<timestamp>",
    "player_id": "<unique_player_id>"
  }
  ```

### **Game Flow**

- **Free Roam Phase**
  - Players can **move freely** within the map.
  - No roles or additional actions are assigned yet.

### **Technical Requirements**

- **Python Compatibility**
  - Use **Python 3.8+** for `asyncio` enhancements.

- **Dependencies**
  - Install `asyncio` and `websockets` libraries.

- **Testing**
  - Implement basic **unit tests** for client-server connectivity and movement.

- **Logging**
  - Log player connections, disconnections, and movements for debugging.

---

## **Update 2: Role Assignment and Basic Actions**

### **Objective**

Introduce player roles (Crewmate and Impostor) and implement basic actions like killing and reporting.

### **Server Components**

- **Role Assignment**
  - Randomly assign roles to players upon game start:
    - **Crewmates**
    - **Impostors**
  - Update player attributes to include `role` and `status` (`alive` or `dead`).

- **Action Handling**
  - Implement `kill` action for Impostors with a configurable **cooldown period**.
  - Implement `report` action for Crewmates to report dead bodies.

- **Cooldown Management**
  - Track cooldown timers for each Impostor.
  - Prevent actions if cooldown is active.

- **Priority System**
  - Define action priorities:
    - **Highest**: `report`
    - **Medium**: `kill`
    - **Lowest**: `movement`, `tasks`

### **Client Components**

- **Command Interface**
  - Extend the CLI to accept new commands based on roles:
    - **Impostors**: `kill <player_id>`
    - **Crewmates**: `report`

- **HUD Enhancements**
  - Display role-specific options and cooldown timers.
  - Indicate nearby players who can be interacted with.

### **Communication Protocol**

- **Message Types**
  - `action`: `kill`, `report`
  - `event`: Notifications about kills and reports

- **Message Handling**
  - Ensure actions are only processed if valid (e.g., player is alive, cooldown is over).

### **Game Flow**

- **Free Roam Phase Updates**
  - Players perform actions according to their roles.
  - Transition to the **Discussion Phase** upon a report.

### **Technical Requirements**

- **Action Validation**
  - Server-side validation of actions to prevent cheating.

- **Testing**
  - Unit tests for role assignment, action processing, and cooldowns.

- **Logging**
  - Log all actions with timestamps for auditing.

---

## **Update 3: Discussion and Voting Phases**

### **Objective**

Implement the Discussion and Voting phases with chat functionality and voting mechanics.

### **Server Components**

- **Discussion Phase Management**
  - Triggered when a body is reported or an emergency meeting is called.
  - Set a **configurable timer** for the discussion period.

- **Chat System**
  - Allow alive players to exchange messages during the Discussion Phase.
  - Messages are broadcasted to all alive players.

- **Voting Phase Management**
  - After the discussion timer ends, transition to the Voting Phase.
  - Collect votes anonymously from each player.
  - Determine if a player is ejected based on the majority.

- **Ejection Handling**
  - Update the status of ejected players.
  - Optionally reveal the role of the ejected player.

### **Client Components**

- **Chat Interface**
  - Enable players to send chat messages during the Discussion Phase.
  - Display incoming messages in real-time.

- **Voting Interface**
  - Allow players to cast a vote for another player or skip.
  - Provide feedback on successful vote submission.

### **Communication Protocol**

- **Message Types**
  - `chat`: Player messages during discussions.
  - `vote`: Vote submissions.
  - `event`: Announcements of voting results and ejections.

### **Game Flow**

- **Phase Transitions**
  - **Free Roam** → **Discussion** → **Voting** → **Free Roam** (or end game if conditions met).

- **Voting Logic**
  - Calculate votes and handle ties appropriately (e.g., no ejection on tie).

### **Technical Requirements**

- **Timer Implementation**
  - Accurately track and enforce discussion and voting durations.

- **Anonymity**
  - Ensure that votes are anonymous and not traceable by other players.

- **Testing**
  - Test the full cycle of phases and validate correct transitions.

- **Logging**
  - Log chat messages (with timestamps) and voting outcomes.

---

## **Update 4: Tasks and Win Conditions**

### **Objective**

Introduce tasks for Crewmates and define win conditions for both Crewmates and Impostors.

### **Server Components**

- **Task Assignment**
  - Assign a set of tasks to each Crewmate at game start.
  - Store task progress for each player.

- **Task Mechanics**
  - Implement a variety of **text-based mini-games** (e.g., "Fix Wiring", "Swipe Card").
  - Validate task completion based on player input and location.

- **Win Condition Checking**
  - Monitor task completion progress.
  - Declare a **Crewmate victory** when all tasks are completed.
  - Declare an **Impostor victory** when they outnumber Crewmates or meet other conditions.

### **Client Components**

- **Task Interface**
  - Display assigned tasks and their locations.
  - Provide interactive prompts to perform tasks.

- **HUD Enhancements**
  - Show overall task progress (e.g., a progress bar).

### **Communication Protocol**

- **Message Types**
  - `action`: Task-related actions (start, progress, complete).
  - `state`: Updates on individual and collective task progress.

### **Game Mechanics**

- **Ghost Mechanics**
  - Allow dead Crewmates to continue completing tasks.
  - Dead Impostors may have limited abilities (e.g., observe but not interact).

### **Technical Requirements**

- **Task Validation**
  - Ensure tasks can only be completed at the correct locations.
  - Prevent multiple completions of the same task by the same player.

- **Testing**
  - Comprehensive tests for task assignment, completion, and win conditions.

- **Logging**
  - Log task interactions for debugging and analytics.

---

## **Update 5: Advanced Impostor Mechanics**

### **Objective**

Enhance Impostor abilities with the Sabotage system and vent mechanics.

### **Server Components**

- **Sabotage System**
  - Allow Impostors to trigger sabotages affecting game systems (e.g., lights, communications).
  - Implement **critical sabotages** that can lead to an Impostor win if not addressed in time (e.g., Oxygen depletion).

- **Vent System**
  - Define vent locations and connections on the map.
  - Enable Impostors to move between vents unseen.

- **Sabotage Handling**
  - Introduce timers and conditions for sabotages.
  - Allow Crewmates to fix sabotages via specific actions.

### **Client Components**

- **Sabotage Interface**
  - Provide commands for Impostors to initiate sabotages.
  - Display cooldowns for sabotage actions.

- **Repair Interface**
  - Allow Crewmates to perform repair actions at designated locations.

- **Vent Interface**
  - Enable Impostors to enter and exit vents.
  - Display vent options when available.

### **Communication Protocol**

- **Message Types**
  - `action`: Sabotage initiation, vent movement, repair actions.
  - `event`: Sabotage alerts, vent usage notifications (to Impostors only).

### **Game Mechanics**

- **Time-Sensitive Challenges**
  - Critical sabotages require prompt attention from Crewmates.
  - Failure to address critical sabotages results in an Impostor win.

### **Technical Requirements**

- **Timer Management**
  - Accurately track sabotage durations and repair times.

- **Visibility Control**
  - Ensure that vent movements are hidden from Crewmates.

- **Testing**
  - Test sabotage initiation, repair mechanics, and vent navigation.

- **Logging**
  - Record sabotage events and repairs for game balance analysis.

---

## **Update 6: Security Enhancements and Configuration Options**

### **Objective**

Implement security measures, finalize game features, and introduce configurable game settings.

### **Server Components**

- **Input Validation and Sanitization**
  - Validate all incoming data to prevent injection attacks and invalid actions.

- **Role-Based Action Verification**
  - Ensure players can only perform actions permitted by their role and game state.

- **Fog of War Implementation**
  - Limit information sent to players based on their location and line of sight.

- **Secure Connections**
  - Upgrade to **Secure WebSockets (`wss://`)** to encrypt data transmission.

- **Configuration Options**
  - Implement server-side settings for:
    - **Impostor count**
    - **Task quantity and types**
    - **Discussion and voting times**
    - **Vote anonymity**
    - **Ghost mechanics**

### **Client Components**

- **Error Handling**
  - Provide informative error messages for invalid commands or actions.

- **Dynamic HUD Adjustments**
  - Adjust displays based on game configurations (e.g., show/hide certain HUD elements).

### **Security Measures**

- **Server Authority**
  - Maintain the server as the authoritative source for all game state.

- **Data Encryption**
  - Use SSL/TLS certificates to secure WebSocket communications.

### **Technical Requirements**

- **Unit Testing Framework**
  - Utilize `unittest` or `pytest` for comprehensive testing of all components.

- **Logging and Analytics**
  - Implement detailed logging with different levels (info, warning, error).
  - Collect analytics for game metrics and performance monitoring.

- **Documentation**
  - Provide thorough documentation for code, APIs, and configuration settings.

### **Game Mechanics Finalization**

- **Ghost Mechanics**
  - Finalize features for dead players based on configurations:
    - **Ghost chat**: Allow dead players to communicate separately.
    - **Task completion**: Enable or disable ghosts completing tasks.

- **Win Condition Enhancements**
  - Refine conditions for tie scenarios or special circumstances.

---

# **Conclusion**

By dividing the development into six progressive updates, each focusing on specific features and mechanics, the implementation of the Text-Based Among Us game becomes manageable and systematic. This approach allows developers to:

- **Test and validate** each component thoroughly before moving on.
- **Iteratively build** upon previous updates, ensuring stability.
- **Adjust and refine** features based on testing outcomes and potential feedback.
- **Ensure security and performance** through dedicated updates focusing on optimization.

This expanded specification serves as a roadmap for the development process, outlining clear objectives and requirements at each stage.