# Update 5: Advanced Impostor Mechanics

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