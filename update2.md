# Update 2: Role Assignment and Basic Actions

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