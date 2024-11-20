# Update 4: Tasks and Win Conditions

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