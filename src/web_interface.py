from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
from .state_manager import StateManager


def create_web_app(state_manager: StateManager) -> FastAPI:
    """Create FastAPI web application"""
    app = FastAPI(title="State of Play - Text Adventure Dashboard")
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Game state dashboard HTML page"""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>State of Play - Text Adventure Dashboard</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Courier New', monospace;
                    background-color: #1a1a1a;
                    color: #00ff00;
                    line-height: 1.6;
                    padding: 20px;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                
                h1 {
                    text-align: center;
                    margin-bottom: 30px;
                    color: #00ffff;
                    text-shadow: 0 0 10px #00ffff;
                }
                
                .grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 20px;
                }
                
                .panel {
                    background-color: #2a2a2a;
                    border: 2px solid #00ff00;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
                }
                
                .panel h2 {
                    color: #ffff00;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #555;
                    padding-bottom: 5px;
                }
                
                .status-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 10px;
                    margin-bottom: 15px;
                }
                
                .status-item {
                    background-color: #333;
                    padding: 10px;
                    border-radius: 4px;
                    border-left: 4px solid #00ff00;
                }
                
                .status-label {
                    color: #aaa;
                    font-size: 0.9em;
                }
                
                .status-value {
                    color: #fff;
                    font-weight: bold;
                    font-size: 1.1em;
                }
                
                .room-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 15px;
                }
                
                .room-card {
                    background-color: #333;
                    border: 1px solid #555;
                    border-radius: 6px;
                    padding: 15px;
                    transition: all 0.3s ease;
                }
                
                .room-card:hover {
                    border-color: #00ff00;
                    box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
                }
                
                .room-card.current {
                    border-color: #ffff00;
                    background-color: #3a3a00;
                }
                
                .room-title {
                    color: #00ffff;
                    font-weight: bold;
                    margin-bottom: 8px;
                }
                
                .room-description {
                    color: #ccc;
                    margin-bottom: 10px;
                    font-size: 0.9em;
                }
                
                .room-contents {
                    font-size: 0.8em;
                }
                
                .room-contents div {
                    margin-bottom: 5px;
                }
                
                .items {
                    color: #ffa500;
                }
                
                .npcs {
                    color: #ff69b4;
                }
                
                .exits {
                    color: #98fb98;
                }
                
                .log-container {
                    max-height: 400px;
                    overflow-y: auto;
                    background-color: #1a1a1a;
                    border: 1px solid #444;
                    padding: 15px;
                    border-radius: 6px;
                }
                
                .log-entry {
                    margin-bottom: 8px;
                    padding: 5px;
                    border-left: 3px solid #00ff00;
                    padding-left: 10px;
                }
                
                .log-timestamp {
                    color: #888;
                    font-size: 0.8em;
                }
                
                .log-message {
                    color: #fff;
                }
                
                .controls {
                    text-align: center;
                    margin-top: 20px;
                }
                
                .btn {
                    background-color: #2a2a2a;
                    color: #00ff00;
                    border: 2px solid #00ff00;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    margin: 0 10px;
                    transition: all 0.3s ease;
                }
                
                .btn:hover {
                    background-color: #00ff00;
                    color: #1a1a1a;
                    box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
                }
                
                .full-width {
                    grid-column: 1 / -1;
                }
                
                .auto-refresh {
                    color: #888;
                    font-size: 0.8em;
                    text-align: center;
                    margin-top: 10px;
                }
                
                @media (max-width: 768px) {
                    .grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .room-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .status-grid {
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎮 STATE OF PLAY 🎮</h1>
                <div id="content">
                    <div class="panel">
                        <h2>Loading game state...</h2>
                        <p>Please wait while the dashboard loads.</p>
                    </div>
                </div>
                
                <div class="controls">
                    <button class="btn" onclick="refreshData()">🔄 Refresh</button>
                    <button class="btn" onclick="resetGame()">🔄 Reset Game</button>
                </div>
                
                <div class="auto-refresh">
                    Auto-refreshing every 5 seconds
                </div>
            </div>
            
            <script>
                let refreshInterval;
                
                async function fetchGameState() {
                    try {
                        const response = await fetch('/api/state');
                        if (!response.ok) throw new Error('Failed to fetch state');
                        return await response.json();
                    } catch (error) {
                        console.error('Error fetching game state:', error);
                        return null;
                    }
                }
                
                async function fetchGameLogs() {
                    try {
                        const response = await fetch('/api/logs');
                        if (!response.ok) throw new Error('Failed to fetch logs');
                        return await response.json();
                    } catch (error) {
                        console.error('Error fetching game logs:', error);
                        return [];
                    }
                }
                
                function formatRooms(rooms, playerLocation) {
                    if (!rooms || Object.keys(rooms).length === 0) {
                        return '<p>No rooms available</p>';
                    }
                    
                    return Object.values(rooms).map(room => {
                        const isCurrentRoom = room.id === playerLocation;
                        const items = room.items && room.items.length > 0 ? 
                            `<div class="items">📦 Items: ${room.items.join(', ')}</div>` : '';
                        const npcs = room.npcs && room.npcs.length > 0 ? 
                            `<div class="npcs">👥 NPCs: ${room.npcs.join(', ')}</div>` : '';
                        const exits = room.connections && Object.keys(room.connections).length > 0 ? 
                            `<div class="exits">🚪 Exits: ${Object.keys(room.connections).join(', ')}</div>` : '';
                        
                        return `
                            <div class="room-card ${isCurrentRoom ? 'current' : ''}">
                                <div class="room-title">
                                    ${isCurrentRoom ? '👤 ' : ''}${room.name}
                                </div>
                                <div class="room-description">${room.description}</div>
                                <div class="room-contents">
                                    ${items}
                                    ${npcs}
                                    ${exits}
                                </div>
                            </div>
                        `;
                    }).join('');
                }
                
                function formatLogs(logs) {
                    if (!logs || logs.length === 0) {
                        return '<p>No recent activity</p>';
                    }
                    
                    return logs.map(log => `
                        <div class="log-entry">
                            <div class="log-timestamp">Turn ${log.turn} - ${new Date(log.timestamp).toLocaleTimeString()}</div>
                            <div class="log-message">${log.message}</div>
                        </div>
                    `).join('');
                }
                
                async function updateDashboard() {
                    const [gameState, logs] = await Promise.all([
                        fetchGameState(),
                        fetchGameLogs()
                    ]);
                    
                    const contentDiv = document.getElementById('content');
                    
                    if (!gameState) {
                        contentDiv.innerHTML = `
                            <div class="panel">
                                <h2>❌ Error</h2>
                                <p>Unable to load game state. Make sure the game server is running.</p>
                            </div>
                        `;
                        return;
                    }
                    
                    const player = gameState.players ? Object.values(gameState.players)[0] : null;
                    const playerLocation = player ? player.location : '';
                    const currentRoom = gameState.rooms ? gameState.rooms[playerLocation] : null;
                    
                    contentDiv.innerHTML = `
                        <div class="grid">
                            <div class="panel">
                                <h2>🎯 Game Status</h2>
                                <div class="status-grid">
                                    <div class="status-item">
                                        <div class="status-label">Title</div>
                                        <div class="status-value">${gameState.title || 'Unknown'}</div>
                                    </div>
                                    <div class="status-item">
                                        <div class="status-label">Turn</div>
                                        <div class="status-value">${gameState.current_turn || 0}</div>
                                    </div>
                                    <div class="status-item">
                                        <div class="status-label">Status</div>
                                        <div class="status-value">${gameState.active ? '🟢 Active' : '🔴 Inactive'}</div>
                                    </div>
                                    <div class="status-item">
                                        <div class="status-label">Player</div>
                                        <div class="status-value">${player ? player.name : 'None'}</div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="panel">
                                <h2>👤 Player Info</h2>
                                ${player ? `
                                    <div class="status-grid">
                                        <div class="status-item">
                                            <div class="status-label">Current Location</div>
                                            <div class="status-value">${currentRoom ? currentRoom.name : 'Unknown'}</div>
                                        </div>
                                        <div class="status-item">
                                            <div class="status-label">Inventory Items</div>
                                            <div class="status-value">${player.inventory ? player.inventory.length : 0}</div>
                                        </div>
                                    </div>
                                    ${player.inventory && player.inventory.length > 0 ? 
                                        `<div style="margin-top: 10px;"><strong>Inventory:</strong> ${player.inventory.join(', ')}</div>` : 
                                        '<div style="margin-top: 10px; color: #888;">Inventory is empty</div>'
                                    }
                                ` : '<p>No player found</p>'}
                            </div>
                            
                            <div class="panel full-width">
                                <h2>🗺️ World Map</h2>
                                <div class="room-grid">
                                    ${formatRooms(gameState.rooms, playerLocation)}
                                </div>
                            </div>
                            
                            <div class="panel full-width">
                                <h2>📜 Recent Activity</h2>
                                <div class="log-container">
                                    ${formatLogs(logs)}
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                async function refreshData() {
                    await updateDashboard();
                }
                
                async function resetGame() {
                    if (confirm('Are you sure you want to reset the game? This will lose all progress.')) {
                        try {
                            const response = await fetch('/api/reset', { method: 'POST' });
                            if (response.ok) {
                                alert('Game reset successfully!');
                                await updateDashboard();
                            } else {
                                alert('Failed to reset game');
                            }
                        } catch (error) {
                            alert('Error resetting game: ' + error.message);
                        }
                    }
                }
                
                // Initialize dashboard
                updateDashboard();
                
                // Set up auto-refresh
                refreshInterval = setInterval(updateDashboard, 5000);
                
                // Clean up on page unload
                window.addEventListener('beforeunload', () => {
                    if (refreshInterval) {
                        clearInterval(refreshInterval);
                    }
                });
            </script>
        </body>
        </html>
        """
        return html_content
    
    @app.get("/api/state")
    async def get_game_state():
        """Get current game state as JSON"""
        try:
            world_state = state_manager.get_world_state("default")
            if not world_state:
                raise HTTPException(status_code=404, detail="Game not found")
            return world_state
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/logs")
    async def get_game_logs():
        """Get game event log as JSON"""
        try:
            logs = state_manager.get_game_history("default", limit=50)
            return [log.model_dump() for log in logs]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/reset")
    async def reset_game():
        """Reset game to initial state"""
        try:
            # Delete current game
            if state_manager.game_exists("default"):
                state_manager.delete_game("default")
            
            # This would require access to game_engine to recreate the game
            # For now, just indicate success - the game will be recreated on next MCP interaction
            return {"message": "Game reset successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app