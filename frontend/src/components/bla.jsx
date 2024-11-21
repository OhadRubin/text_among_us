import React, { useState, useEffect, useRef } from 'react';
import { Send, LogOut, Navigation, Skull, Flag, MessageCircle, Users } from 'lucide-react';

const Card = ({ children, className = '' }) => <div className={`bg-white rounded-lg shadow p-4 ${className}`}>{children}</div>;
const CardHeader = ({ children }) => <div className="mb-4">{children}</div>;
const CardTitle = ({ children }) => <h2 className="text-xl font-bold">{children}</h2>;
const CardContent = ({ children }) => <div>{children}</div>;

const GameClient = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [gameState, setGameState] = useState({
        location: '',
        players_in_room: [],
        available_exits: [],
        role: '',
        status: '',
        bodies_in_room: [],
        player_id: null
    });
    const [connected, setConnected] = useState(false);
    const ws = useRef(null);
    const reconnectTimeout = useRef(null);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    };

    useEffect(() => {
        let socket;

        const connectWebSocket = () => {
            socket = new WebSocket('ws://localhost:8009');
            ws.current = socket;

            socket.onopen = () => {
                setConnected(true);
                addMessage('System', 'Connected to game server');
            };

            socket.onerror = (error) => {
                addMessage('System', 'Connection error');
                setConnected(false);
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleServerMessage(data);
                } catch (error) {
                    console.error('Failed to parse message:', error);
                    addMessage('System', 'Received invalid message from server');
                }
            };

            socket.onclose = () => {
                setConnected(false);
                addMessage('System', 'Disconnected from server');

                if (reconnectTimeout.current) {
                    clearTimeout(reconnectTimeout.current);
                }

                reconnectTimeout.current = setTimeout(() => {
                    connectWebSocket();
                }, 5000);
            };
        };

        connectWebSocket();

        return () => {
            if (socket) {
                socket.close();
            }
            if (reconnectTimeout.current) {
                clearTimeout(reconnectTimeout.current);
            }
        };
    }, []);

    const addMessage = (sender, text) => {
        setMessages(prev => [...prev, { sender, text, timestamp: new Date().toLocaleTimeString() }]);
    };

    const handleServerMessage = (data) => {
        console.log('Received message:', data);
        switch (data.type) {
            case 'state_update':
                setGameState(data.state || data);
                break;
            case 'player_connected':
                addMessage('System', `Player ${data.player_id} connected at ${data.location}`);
                break;
            case 'player_disconnected':
                addMessage('System', `Player ${data.player_id} disconnected`);
                break;
            case 'player_moved':
                addMessage('System', `Player ${data.player_id} moved from ${data.from} to ${data.to}`);
                break;
            case 'player_killed':
                addMessage('System', `Player ${data.victim} was killed by ${data.killer} at ${data.location}`);
                break;
            case 'chat_message':
                addMessage(data.player_id, data.message);
                break;
            case 'phase_change':
                addMessage('System', `Phase changed to ${data.phase}. Duration: ${data.duration} seconds`);
                break;
            default:
                if (data.message) {
                    addMessage('System', data.message);
                }
        }
    };

    const sendCommand = (action, params = {}) => {
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            addMessage('System', 'Not connected to server');
            return;
        }
        try {
            ws.current.send(JSON.stringify({ action, ...params }));
        } catch (error) {
            console.error('Failed to send message:', error);
            addMessage('System', 'Failed to send message');
        }
    };

    const handleMove = (destination) => {
        sendCommand('move', { destination });
    };

    const handleKill = (target) => {
        sendCommand('kill', { target });
    };

    const handleChat = (e) => {
        e.preventDefault();
        if (inputMessage.trim()) {
            sendCommand('chat', { message: inputMessage.trim() });
            setInputMessage('');
        }
    };

    return (
        <div className="flex h-screen bg-gray-100 p-4">
            <div className="w-1/4 mr-4 space-y-4">
                <Card>
                    <CardHeader>
                        <CardTitle>Player Info</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            <p><strong>ID:</strong> {gameState.player_id}</p>
                            <p><strong>Role:</strong> {gameState.role}</p>
                            <p><strong>Status:</strong> {gameState.status}</p>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Location</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p><strong>Current:</strong> {gameState.location}</p>
                        <div className="mt-2">
                            <p className="font-semibold">Available Exits:</p>
                            <div className="flex flex-wrap gap-2 mt-1">
                                {gameState.available_exits.map(exit => (
                                    <button key={exit} onClick={() => handleMove(exit)} className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
                                        {exit}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Room Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div>
                                <p className="font-semibold flex items-center gap-2">
                                    <Users size={16} /> Players Present:
                                </p>
                                <div className="ml-6 mt-1">
                                    {gameState.players_in_room.map(player => (
                                        <div key={player} className="flex items-center justify-between">
                                            <span>{player}</span>
                                            {gameState.role === 'impostor' && player !== gameState.player_id && (
                                                <button onClick={() => handleKill(player)} className="text-red-500 hover:text-red-700">
                                                    <Skull size={16} />
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {gameState.bodies_in_room.length > 0 && (
                                <div>
                                    <p className="font-semibold text-red-500">Bodies Found:</p>
                                    <ul className="ml-6">
                                        {gameState.bodies_in_room.map(body => (
                                            <li key={body}>{body}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <div className="space-x-2">
                    <button onClick={() => sendCommand('report')} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                        Report Body
                    </button>
                    <button onClick={() => sendCommand('call_meeting')} className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors">
                        Call Meeting
                    </button>
                </div>
            </div>

            <div className="flex-1 flex flex-col bg-white rounded-lg shadow">
                <div className="flex-1 p-4 overflow-y-auto">
                    {messages.map((msg, idx) => (
                        <div key={idx} className="mb-2">
                            <span className="text-gray-500 text-sm">[{msg.timestamp}]</span>
                            <span className="font-semibold"> {msg.sender}: </span>
                            <span> {msg.text} </span>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                <form onSubmit={handleChat} className="p-4 border-t">
                    <div className="flex gap-2">
                        <input type="text" value={inputMessage} onChange={(e) => setInputMessage(e.target.value)} placeholder="Type a message..." className="flex-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        <button type="submit" className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
                            <Send size={16} />
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default GameClient;

GameClient.jsx