# Update 3: Discussion and Voting Phases

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