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