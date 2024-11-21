# Detailed Plan for Simplifying game.py Based on wasd_game.py Design

## 1. Data Models
### Current Issues
- Multiple fragmented dictionaries tracking state
- No type validation
- Complex state updates
- Redundant data structures

### Proposed Changes
- Create structured dataclasses:
  ```python
  Player:
    - id
    - location 
    - role
    - is_alive
    - emergency_meetings_left
  
  GameState:
    - players
    - bodies
    - map_layout
    - current_phase
    - discussion_timer
    - voting_timer
  ```

### Benefits
- Type checking at runtime
- Cleaner serialization
- Centralized state management
- Reduced code duplication
- Better IDE support

## 2. State Management
### Current Issues
- State spread across multiple dictionaries
- Inconsistent state updates
- Complex state synchronization
- Difficult to track state changes

### Proposed Changes
- Single GameState class managing:
  - Player states
  - Game phase
  - Map state
  - Voting state
  - Discussion state
- Methods for atomic state updates
- State validation methods
- State change event system

### Benefits
- Single source of truth
- Atomic state updates
- Easier debugging
- Better state consistency
- Simplified state synchronization

## 3. Room Navigation
### Current Issues
- Complex movement validation
- Redundant room connection checks
- Unclear navigation structure

### Proposed Changes
- WASD-style movement system:
  - Direction mapping (N,S,E,W)
  - Room connection validation
  - Movement cooldown
  - Clear movement feedback
- Simplified room structure

### Benefits
- Intuitive controls
- Reduced complexity
- Better user experience
- Easier maintenance

## 4. UI Organization
### Current Issues
- Mixed rendering logic
- Redundant drawing code
- Complex UI state management
- Unclear component boundaries

### Proposed Changes
- Separate UI components:
  - RoomRenderer
  - PlayerListRenderer
  - ActionButtonRenderer
  - ChatRenderer
  - VotingRenderer
- Clear component hierarchy
- Event-based UI updates

### Benefits
- Modular UI code
- Easier testing
- Clear separation of concerns
- Simplified maintenance

## 5. Event Handling
### Current Issues
- Large message processing functions
- Mixed event handling logic
- Complex state updates in handlers
- Unclear event flow

### Proposed Changes
- Dedicated handlers:
  - MovementHandler
  - CombatHandler
  - ReportingHandler
  - VotingHandler
  - ChatHandler
- Event validation
- Clear event flow
- State update protocols

### Benefits
- Clear event handling
- Easier debugging
- Better error handling
- Simplified testing

## 6. Feature Simplification
### Current Issues
- Complex game phases
- Intertwined feature logic
- Difficult to modify features
- High maintenance overhead

### Proposed Changes
- Core features:
  - Basic movement
  - Simple combat
  - Basic reporting
- Optional features:
  - Discussion system
  - Voting system
  - Emergency meetings
- Feature flags

### Benefits
- Focused core gameplay
- Easier testing
- Modular features
- Simplified maintenance

## 7. Connection Management
### Current Issues
- Complex websocket handling
- Redundant connection checks
- Mixed connection/game logic
- Difficult error handling

### Proposed Changes
- ConnectionManager class
- Clear connection lifecycle
- Connection state tracking
- Error recovery protocols
- Connection validation

### Benefits
- Reliable connections
- Clear error handling
- Better reconnection support
- Simplified debugging

## 8. Integration Considerations

### Player State Management
- Current challenges:
  - Player state split between multiple dictionaries
  - No validation when updating player attributes
  - Inconsistent state access patterns
  - Complex state synchronization

- Integration requirements:
  - Migrate existing player data from dictionaries
  - Maintain websocket references in Player objects
  - Preserve existing player ID generation
  - Handle player disconnection cleanup
  - Update all references to player state

### Game Phase Transitions 
- Current challenges:
  - Phase transitions spread across multiple methods
  - Timer management mixed with game logic
  - Complex state updates during phase changes
  - Inconsistent phase-specific behavior

- Integration requirements:
  - Preserve existing phase transition triggers
  - Maintain timer functionality
  - Keep phase-specific UI states
  - Handle interrupted phases
  - Update phase-dependent validations

### Room Navigation System
- Current challenges:
  - Movement validation tied to room connections
  - Complex position tracking
  - Mixed movement and state updates
  - Unclear room boundaries

- Integration requirements:
  - Preserve existing room connection data
  - Maintain movement validation rules
  - Update position tracking system
  - Handle room capacity limits
  - Integrate with new Player objects

### Event Broadcasting
- Current challenges:
  - Event handling mixed with state updates
  - Complex message formatting
  - Inconsistent event propagation
  - Mixed client/server concerns

- Integration requirements:
  - Maintain existing event types
  - Preserve message format compatibility
  - Update event validation
  - Handle new event types
  - Integrate with new state system

### Client-Server Communication
- Current challenges:
  - Complex message processing
  - Mixed state synchronization
  - Inconsistent error handling
  - Redundant state updates

- Integration requirements:
  - Maintain websocket compatibility
  - Update message handlers
  - Preserve client connections
  - Handle state synchronization
  - Update error responses

## 9. Critical Dependencies

### State Management Dependencies
- GameState must handle:
  - Existing player dictionary format
  - Current phase system
  - Room occupancy tracking
  - Body location management
  - Vote tracking system

### Player Management Dependencies
- Player class must support:
  - Current websocket integration
  - Existing role system
  - Status tracking
  - Location management
  - Meeting limitations

### UI System Dependencies
- UI components must handle:
  - Current rendering system
  - Existing event handlers
  - Phase-specific displays
  - Player interaction
  - Game state visualization

### Network Dependencies
- ConnectionManager must maintain:
  - Current websocket protocol
  - Existing message format
  - State synchronization
  - Error handling
  - Client tracking

## 10. Migration Risks

### State Management Risks
- Data loss during migration
- Inconsistent state updates
- Broken validation rules
- Phase transition errors
- Lost player connections

### Player Management Risks
- Broken player references
- Lost player state
- Role assignment issues
- Movement validation errors
- Meeting system failures

### UI System Risks
- Broken rendering
- Incorrect state display
- Lost player interactions
- Phase transition issues
- Event handling failures

### Network Risks
- Connection interruptions
- Message format incompatibility
- State synchronization issues
- Lost client connections
- Websocket protocol breaks

## 11. Mitigation Strategies

### State Migration
1. Create parallel state system
2. Validate state consistency
3. Implement rollback mechanism
4. Test state transitions
5. Monitor state integrity

### Player Management
1. Create temporary player mappings
2. Validate player state transfer
3. Test role system
4. Verify movement system
5. Monitor player connections

### UI Updates
1. Implement UI component tests
2. Create rendering fallbacks
3. Validate event handling
4. Test phase transitions
5. Monitor UI performance

### Network Handling
1. Create connection backup system
2. Validate message formats
3. Test state synchronization
4. Implement recovery mechanism
5. Monitor connection stability

## 12. Testing Requirements

### Unit Testing
- Test all new classes
- Validate state transitions
- Verify player management
- Test room navigation
- Validate event handling

### Integration Testing
- Test state migration
- Verify player interactions
- Test phase transitions
- Validate UI components
- Test network handling

### System Testing
- Full gameplay testing
- Performance testing
- Load testing
- Error recovery testing
- State consistency testing

## 13. Rollout Strategy

### Phase 1: Core Systems
1. Implement data models
2. Create state management
3. Test core functionality
4. Validate state handling
5. Monitor system stability

### Phase 2: Player Management
1. Implement Player class
2. Migrate player data
3. Test player interactions
4. Validate role system
5. Monitor player state

### Phase 3: UI Updates
1. Implement UI components
2. Update rendering system
3. Test user interactions
4. Validate phase displays
5. Monitor UI performance

### Phase 4: Network Updates
1. Implement ConnectionManager
2. Update message handling
3. Test state synchronization
4. Validate error handling
5. Monitor connection stability

## 14. Success Criteria

### Technical Metrics
- Code complexity reduction
- Improved test coverage
- Reduced error rates
- Better performance
- Cleaner architecture

### Functional Metrics
- Maintained game functionality
- Improved state consistency
- Better error handling
- Smoother transitions
- Reliable networking

### User Experience Metrics
- Reduced latency
- Better responsiveness
- Clearer feedback
- Improved stability
- Consistent behavior

## 15. Documentation Updates

### Code Documentation
- Update type hints
- Revise docstrings
- Add implementation notes
- Document dependencies
- Update examples

### Architecture Documentation
- Update component diagrams
- Document state flow
- Detail event handling
- Describe interactions
- Update protocols

### User Documentation
- Update setup guide
- Revise controls
- Document features
- Add troubleshooting
- Update examples

## Implementation Strategy
1. Create data models
   - Define dataclasses
   - Add validation
   - Implement serialization

2. Implement state management
   - Create GameState class
   - Add state update methods
   - Implement validation

3. Simplify movement
   - Implement WASD system
   - Add movement validation
   - Create feedback system

4. Reorganize UI
   - Create component classes
   - Implement rendering system
   - Add event handling

5. Refactor event handling
   - Create handler classes
   - Implement validation
   - Add error handling

6. Modularize features
   - Identify core features
   - Create feature flags
   - Add configuration

7. Improve networking
   - Create ConnectionManager
   - Add error handling
   - Implement recovery

## Testing Strategy
1. Unit tests for:
   - Data models
   - State management
   - Movement system
   - Event handlers

2. Integration tests for:
   - UI components
   - Network handling
   - Game flow

3. System tests for:
   - Full gameplay
   - Error scenarios
   - Performance

## Documentation Requirements
1. Code documentation:
   - Type hints
   - Docstrings
   - Comments

2. Architecture documentation:
   - Component diagrams
   - State flows
   - Event handling

3. User documentation:
   - Setup guide
   - Controls
   - Features

## Migration Plan
1. Create new structure
2. Implement core features
3. Add optional features
4. Test thoroughly
5. Deploy gradually
6. Monitor performance
7. Gather feedback

## Success Metrics
- Reduced code complexity
- Improved test coverage
- Better error handling
- Faster development
- Easier maintenance
- Clearer architecture