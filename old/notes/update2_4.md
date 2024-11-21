**Kill Mechanics Enhancement**

1. **Add Kill Cooldown Timer (Default 3s)**
   - **Purpose**: Prevent impostors from killing too frequently, adding strategic depth to gameplay.
   - **Implementation Details**:
     - **Individual Cooldown**: Each impostor should have their own independent cooldown timer.
     - **Timer Start**: The cooldown timer begins either at the start of the game or immediately after performing a kill.
     - **Visual Indicator**:
       - Impostors should see a countdown timer displaying the remaining cooldown time.
       - The "Kill" button should be disabled or visually indicated as inactive during the cooldown period.
     - **Edge Cases**:
       - If an impostor tries to kill during the cooldown, a notification should inform them of the remaining cooldown time.
       - The cooldown should persist through game events like meetings or reports unless reset by game logic.


**Report Mechanics**

1. **Add Proximity Detection for Bodies**
   - **Purpose**: Require players to be near a dead body to report it, increasing realism and strategic movement.
   - **Implementation Details**:
     - **Detection Radius**: Define a proximity radius = same room as a dead body within which it can be reported.
     - **Continuous Scanning**:
       - Player clients should continuously check for dead bodies within the proximity radius.
       - Optimize scanning to reduce computational load, possibly by checking only when a player moves.
     - **Visual Indicators**:
       - When within proximity, display the "Report" button.
       - Optional: Show a visual cue (e.g., a flashing icon) indicating a body is nearby.
     - **Multiple Bodies**:
       - If multiple bodies are nearby, the report should include information on all detectable bodies.

2. **Remove Always-Visible REPORT Button**
   - **Purpose**: Prevent players from reporting without being near a body, enhancing game fairness.
   - **Implementation Details**:
     - **Default State**: The "Report" button is hidden or disabled when no bodies are nearby.
     - **Activation**:
       - The button appears or becomes active only when the player enters the proximity radius of a dead body.
     - **User Interface**:
       - Ensure the appearance/disappearance of the button is smooth to avoid distracting the player.
       - Optional: Add settings to allow players to toggle visual cues for accessibility.
     - **Audio Cues**:
       - Optionally play a sound when the "Report" button becomes available.
     - **Edge Cases**:
       - Handle scenarios where a body is reported by another player while someone else is approaching it.

**Game Flow Improvements**

1. **Add Minimum Player Count Before Game Can Start (4+)**
   - **Purpose**: Ensure the game has enough players for balanced and enjoyable gameplay.
   - **Implementation Details**:
     - **Lobby System**:
       - Implement a pre-game lobby where players wait until the minimum player count is reached.
       - Display the current number of players and indicate how many more are needed to start.
     - **Configurable Minimum**:
       - Allow the game host or server settings to adjust the minimum player count, defaulting to 4.
     - **Automatic Start**:
       - Once the minimum player count is reached, start a countdown timer (e.g., 10 seconds) before the game begins.
       - Provide an option to start immediately if all players are ready.
     - **Player Readiness**:
       - Include a "Ready" button for players to indicate they're prepared to start.
       - Show a visual indicator of each player's readiness status.
     - **Edge Cases**:
       - If a player disconnects before the game starts, recalculate the player count and adjust accordingly.
       - Prevent the game from starting if the player count drops below the minimum during the countdown.

2. **Add Win Conditions for Both Crews and Impostors**
   - **Purpose**: Define clear objectives and end conditions to conclude the game appropriately.
   - **Implementation Details**:
     - **Crewmate Win Conditions**:
       - **Eliminate All Impostors**: Crewmates win if all impostors are ejected or killed.
       - **Complete Tasks**: If tasks are implemented, crewmates win when all tasks are completed.
     - **Impostor Win Conditions**:
       - **Equal Numbers**: Impostors win when the number of impostors equals or exceeds the number of crewmates.
       - **Sabotage Victory**: If sabotage mechanics exist, impostors can win by triggering critical events not fixed in time.
     - **Game State Monitoring**:
       - Continuously check win conditions after key events (e.g., player ejection, kill, task completion).
     - **End Game Sequence**:
       - Display a victory or defeat screen to all players indicating which team won.
       - Include statistics such as remaining players, tasks completed, and impostor identities.
     - **Post-Game Options**:
       - Provide options to return to the lobby, start a new game, or exit.
     - **Edge Cases**:
       - Handle ties or stalemates gracefully, possibly declaring a draw.
       - Ensure that disconnections or sudden player drops trigger win condition checks.

**Additional Considerations**

- **User Interface Enhancements**:
  - Update the UI to reflect new mechanics, such as cooldown timers and proximity indicators.
  - Ensure all players have clear and accessible information about their status and available actions.

- **Server side**:
  - Implement efficient data structures for tracking player positions and statuses.
