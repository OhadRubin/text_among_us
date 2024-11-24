import React, { useEffect, useState, useRef } from 'react';

const GameClient = () => {
  const [ws, setWs] = useState(null);
  const [playerId, setPlayerId] = useState(null);
  const [location, setLocation] = useState('');
  const [availableExits, setAvailableExits] = useState([]);
  const [playersInRoom, setPlayersInRoom] = useState([]);
  const [role, setRole] = useState('');
  const [status, setStatus] = useState('alive');
  const [bodiesInRoom, setBodiesInRoom] = useState([]);
  const [messages, setMessages] = useState([]);
  const [phase, setPhase] = useState('free_roam');
  const [chatMessages, setChatMessages] = useState([]);
  const [error, setError] = useState('');
  const [inputMessage, setInputMessage] = useState('');
  const [alivePlayers, setAlivePlayers] = useState([]);
  const [emergencyMeetingsLeft, setEmergencyMeetingsLeft] = useState(1);
  const [timeLeft, setTimeLeft] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8765');
    setWs(websocket);

    websocket.onopen = () => {
      console.log('WebSocket connection established');
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleMessage(message);
    };

    websocket.onclose = () => {
      console.log('WebSocket connection closed');
    };

    return () => {
      websocket.close();
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const handleMessage = (message) => {
    console.log('Received message:', message);
    
    try {
      switch (message.type) {
        case 'welcome':
          setPlayerId(message.player_id);
          setMessages((prev) => [...prev, `Welcome! You are ${message.player_id}`]);
          break;
        case 'player_connected':
          setMessages((prev) => [...prev, `${message.player_id} connected.`]);
          break;
        case 'game_started':
          setMessages((prev) => [...prev, `Game started!`]);
          break;
        case 'state_update':
          // Update player state
          if (!playerId) setPlayerId(message.player_id);
          setLocation(message.location);
          setAvailableExits(message.available_exits);
          setPlayersInRoom(message.players_in_room);
          setRole(message.role);
          setStatus(message.status);
          setBodiesInRoom(message.bodies_in_room);
          setAlivePlayers(message.alive_players);
          setEmergencyMeetingsLeft(message.emergency_meetings_left);
          break;
        case 'player_moved':
          setMessages((prev) => [
            ...prev,
            `${message.player_id} moved from ${message.from} to ${message.to}`,
          ]);
          break;
        case 'player_killed':
          setMessages((prev) => [
            ...prev,
            `${message.victim} was killed in ${message.location}`,
          ]);
          if (message.victim === playerId) {
            setStatus('dead');
          }
          break;
        case 'error':
          setError(message.message);
          break;
        case 'chat_message':
          console.log('Processing chat message:', message);
          setChatMessages((prev) => [
            ...prev,
            `${message.player_id}: ${message.message}`,
          ]);
          break;
        case 'phase_change':
          setPhase(message.phase);
          setMessages((prev) => [
            ...prev,
            `Phase changed to ${message.phase} for ${message.duration} seconds`,
          ]);
          setChatMessages([]);
          startTimer(message.duration);
          break;
        case 'vote_received':
          setMessages((prev) => [...prev, `Your vote has been received.`]);
          break;
        case 'player_ejected':
          setMessages((prev) => [
            ...prev,
            `${message.player_id} was ejected. They were a ${message.role}.`,
          ]);
          break;
        case 'no_ejection':
          setMessages((prev) => [...prev, message.message]);
          break;
        case 'player_disconnected':
          setMessages((prev) => [...prev, `${message.player_id} disconnected.`]);
          break;
        case 'emergency_meeting_called':
          setMessages((prev) => [
            ...prev,
            `${message.player_id} called an emergency meeting!`
          ]);
          break;
        default:
          console.log('Unknown message type:', message);
      }
    } catch (error) {
      console.error('Error handling message:', error);
    }
  };

  const sendAction = (action, data = {}) => {
    if (ws) {
      const message = { action, ...data };
      console.log('Sending action:', message);
      try {
        ws.send(JSON.stringify(message));
        console.log('Action sent successfully');
      } catch (error) {
        console.error('Error sending action:', error);
      }
    } else {
      console.warn('WebSocket not connected');
    }
  };

  const moveTo = (destination) => {
    sendAction('move', { destination });
  };

  const killPlayer = (target) => {
    sendAction('kill', { target });
  };

  const reportBody = () => {
    sendAction('report');
  };

  const votePlayer = (vote) => {
    sendAction('vote', { vote });
  };

  const callMeeting = () => {
    sendAction('call_meeting');
  };

  const sendChat = () => {
    console.log('Attempting to send chat:', inputMessage);
    if (inputMessage.trim()) {
      sendAction('chat', { message: inputMessage });
      setInputMessage('');
    } else {
      console.log('Empty message, not sending');
    }
  };

  const startTimer = (duration) => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    setTimeLeft(duration);
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  console.log({
    phase,
    status,
    availableExits,
    role
  });

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Among Us Game Client</h1>
      <div className="space-y-4">
        <p>
          <span className="font-semibold">Player ID:</span> {playerId}
        </p>
        <p>
          <span className="font-semibold">Status:</span> {status}
        </p>
        <p>
          <span className="font-semibold">Role:</span> {role}
        </p>
        <p>
          <span className="font-semibold">Location:</span> {location}
        </p>
        <p>
          <span className="font-semibold">Available Exits:</span> {availableExits.join(', ')}
        </p>
        <p>
          <span className="font-semibold">Players in Room:</span> {playersInRoom.join(', ')}
        </p>
        <p>
          <span className="font-semibold">Bodies in Room:</span> {bodiesInRoom.join(', ')}
        </p>
        <p>
          <span className="font-semibold">Phase:</span> {phase}
        </p>
        <p>
          <span className="font-semibold">Emergency Meetings Left:</span> {emergencyMeetingsLeft}
        </p>
        {error && <p className="text-red-500">Error: {error}</p>}
      </div>

      {phase === 'free_roam' && status === 'alive' && (
        <div className="mt-6 bg-gray-100 p-4 rounded-lg">
          <h2 className="text-2xl font-bold mb-4">Actions</h2>
          
          {/* Move Section */}
          <div className="mb-6">
            <h3 className="text-xl font-semibold mb-2">Move</h3>
            <div className="flex flex-wrap gap-2">
              {availableExits.map((exit) => (
                <button
                  key={exit}
                  onClick={() => moveTo(exit)}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition-colors"
                >
                  {exit}
                </button>
              ))}
            </div>
          </div>

          {/* Impostor Actions */}
          {role === 'Impostor' && (
            <div className="mb-6">
              <h3 className="text-xl font-semibold mb-2">Kill</h3>
              <div className="flex flex-wrap gap-2">
                {playersInRoom
                  .filter((pid) => pid !== playerId)
                  .map((pid) => (
                    <button
                      key={pid}
                      onClick={() => killPlayer(pid)}
                      className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded transition-colors"
                    >
                      Kill {pid}
                    </button>
                  ))}
              </div>
            </div>
          )}

          {/* Report Body Button */}
          {bodiesInRoom.length > 0 && (
            <div className="mb-6">
              <button 
                onClick={reportBody}
                className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded transition-colors"
              >
                Report Body
              </button>
            </div>
          )}

          <div className="mb-6">
            <button 
              onClick={callMeeting}
              className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded transition-colors"
            >
              Call Emergency Meeting
            </button>
          </div>
        </div>
      )}

      {(phase === 'discussion' || phase === 'voting') && (
        <div className="mt-6 bg-gray-100 p-4 rounded-lg">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">
              {phase === 'discussion' ? 'Discussion' : 'Voting'}
            </h2>
            <div className="text-xl font-bold text-blue-600">
              Time Left: {timeLeft}s
            </div>
          </div>
          <div className="mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendChat()}
                className="flex-1 px-3 py-2 border rounded"
                placeholder="Type your message..."
              />
              <button 
                onClick={sendChat}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition-colors"
              >
                Send
              </button>
            </div>
          </div>

          <div>
            <h3 className="text-xl font-semibold mb-2">Chat Messages</h3>
            <div className="bg-white p-3 rounded max-h-60 overflow-y-auto">
              {chatMessages.map((msg, index) => (
                <div key={index} className="mb-1">{msg}</div>
              ))}
            </div>
          </div>
        </div>
      )}

      {phase === 'voting' && (
        <div className="mt-6 bg-gray-100 p-4 rounded-lg">
          <h2 className="text-2xl font-bold mb-4">Voting Phase</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {alivePlayers
              .filter((pid) => pid !== playerId)
              .concat(['skip'])
              .map((pid) => (
                <button
                  key={pid}
                  onClick={() => votePlayer(pid)}
                  className={`
                    p-4 rounded-lg text-center transition-all
                    ${pid === 'skip' 
                      ? 'bg-gray-500 hover:bg-gray-600 text-white' 
                      : 'bg-blue-500 hover:bg-blue-600 text-white'}
                    transform hover:scale-105
                    flex flex-col items-center justify-center
                    min-h-[100px]
                  `}
                >
                  {pid === 'skip' ? (
                    <>
                      <span className="text-xl mb-1">⏭️</span>
                      <span className="font-bold">Skip Vote</span>
                    </>
                  ) : (
                    <>
                      <span className="text-2xl mb-1">👤</span>
                      <span className="font-bold">Vote {pid}</span>
                    </>
                  )}
                </button>
              ))}
          </div>
        </div>
      )}

      <div>
        <h3>Messages</h3>
        <ul>
          {messages.map((msg, index) => (
            <li key={index}>{msg}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default GameClient;
