import asyncio
import logging
import os
import json
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import aiohttp
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServerInfo(BaseModel):
    id: str
    name: str
    url: str
    game_id: str
    status: str
    last_seen: Optional[float] = None


class MCPDashboard:
    def __init__(self):
        self.app = FastAPI(title="MCP State of Play Dashboard")
        self.registered_servers: Dict[str, MCPServerInfo] = {}
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def homepage():
            """Multi-server dashboard homepage"""
            return self._get_homepage_html()

        @self.app.get("/server/{server_id}", response_class=HTMLResponse)
        async def server_view(server_id: str):
            """Individual server state view"""
            if server_id not in self.registered_servers:
                raise HTTPException(status_code=404, detail="Server not found")
            
            return self._get_server_view_html(server_id)

        @self.app.post("/api/register")
        async def register_server(server_info: MCPServerInfo):
            """Register a new MCP server"""
            server_info.last_seen = time.time()
            self.registered_servers[server_info.id] = server_info
            logger.info(f"Registered MCP server: {server_info.id} ({server_info.name})")
            return {"message": "Server registered successfully"}

        @self.app.get("/api/servers")
        async def list_servers():
            """Get list of registered servers"""
            return {
                "servers": [server.model_dump() for server in self.registered_servers.values()],
                "count": len(self.registered_servers)
            }

        @self.app.get("/api/server/{server_id}/state")
        async def get_server_state(server_id: str):
            """Get state from a specific MCP server"""
            if server_id not in self.registered_servers:
                raise HTTPException(status_code=404, detail="Server not found")
            
            server = self.registered_servers[server_id]
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Fetch state from the MCP server's game engine
                    # Since MCP servers don't have HTTP endpoints, we'll proxy through their Redis state
                    return await self._fetch_server_state_via_redis(server)
            except Exception as e:
                logger.error(f"Failed to fetch state from server {server_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch server state: {str(e)}")

        @self.app.get("/api/server/{server_id}/logs")
        async def get_server_logs(server_id: str):
            """Get logs from a specific MCP server"""
            if server_id not in self.registered_servers:
                raise HTTPException(status_code=404, detail="Server not found")
            
            try:
                return await self._fetch_server_logs_via_redis(server_id)
            except Exception as e:
                logger.error(f"Failed to fetch logs from server {server_id}: {e}")
                return []

        @self.app.delete("/api/server/{server_id}")
        async def unregister_server(server_id: str):
            """Unregister an MCP server"""
            if server_id in self.registered_servers:
                del self.registered_servers[server_id]
                logger.info(f"Unregistered MCP server: {server_id}")
                return {"message": "Server unregistered successfully"}
            else:
                raise HTTPException(status_code=404, detail="Server not found")

    async def _fetch_server_state_via_redis(self, server: MCPServerInfo):
        """Fetch server state through Redis since MCP servers don't expose HTTP APIs"""
        try:
            # Import here to avoid circular imports
            from .state_manager import StateManager
            
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            state_manager = StateManager(redis_url)
            
            world_state = state_manager.get_world_state(server.game_id)
            if not world_state:
                return {"error": "No game state found", "server_id": server.id}
            
            # Add server metadata
            world_state["server_id"] = server.id
            world_state["server_name"] = server.name
            world_state["server_url"] = server.url
            
            return world_state
            
        except Exception as e:
            logger.error(f"Failed to fetch state for {server.id}: {e}")
            return {"error": str(e), "server_id": server.id}

    async def _fetch_server_logs_via_redis(self, server_id: str):
        """Fetch server logs through Redis"""
        try:
            from .state_manager import StateManager
            
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            state_manager = StateManager(redis_url)
            
            server = self.registered_servers[server_id]
            logs = state_manager.get_game_history(server.game_id, limit=50)
            return [log.model_dump() for log in logs]
            
        except Exception as e:
            logger.error(f"Failed to fetch logs for {server_id}: {e}")
            return []

    def _get_homepage_html(self) -> str:
        """Generate homepage HTML with server list"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MCP State of Play - Dashboard</title>
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
                    font-size: 2.5em;
                }
                
                .subtitle {
                    text-align: center;
                    margin-bottom: 40px;
                    color: #888;
                    font-size: 1.2em;
                }
                
                .server-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }
                
                .server-card {
                    background-color: #2a2a2a;
                    border: 2px solid #00ff00;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
                    transition: all 0.3s ease;
                    cursor: pointer;
                }
                
                .server-card:hover {
                    border-color: #00ffff;
                    box-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
                    transform: translateY(-2px);
                }
                
                .server-card.offline {
                    border-color: #ff4444;
                    box-shadow: 0 0 15px rgba(255, 68, 68, 0.3);
                }
                
                .server-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }
                
                .server-name {
                    color: #00ffff;
                    font-weight: bold;
                    font-size: 1.3em;
                }
                
                .server-status {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: bold;
                }
                
                .status-running {
                    background-color: #004400;
                    color: #00ff00;
                }
                
                .status-offline {
                    background-color: #440000;
                    color: #ff4444;
                }
                
                .server-info {
                    margin-bottom: 15px;
                }
                
                .info-row {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 8px;
                }
                
                .info-label {
                    color: #aaa;
                }
                
                .info-value {
                    color: #fff;
                    font-weight: bold;
                }
                
                .server-actions {
                    display: flex;
                    gap: 10px;
                }
                
                .btn {
                    background-color: #333;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-family: inherit;
                    font-size: 0.9em;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: inline-block;
                    text-align: center;
                }
                
                .btn:hover {
                    background-color: #00ff00;
                    color: #1a1a1a;
                }
                
                .btn-danger {
                    border-color: #ff4444;
                    color: #ff4444;
                }
                
                .btn-danger:hover {
                    background-color: #ff4444;
                    color: #1a1a1a;
                }
                
                .no-servers {
                    text-align: center;
                    padding: 60px 20px;
                    color: #888;
                    font-size: 1.2em;
                }
                
                .controls {
                    text-align: center;
                    margin-bottom: 30px;
                }
                
                .auto-refresh {
                    color: #888;
                    font-size: 0.8em;
                    text-align: center;
                    margin-top: 20px;
                }
                
                @media (max-width: 768px) {
                    .server-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .server-header {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 10px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎮 MCP STATE OF PLAY 🎮</h1>
                <div class="subtitle">Multi-Server Game Dashboard</div>
                
                <div class="controls">
                    <button class="btn" onclick="refreshServers()">🔄 Refresh Servers</button>
                </div>
                
                <div id="server-list">
                    <div class="no-servers">
                        Loading servers...
                    </div>
                </div>
                
                <div class="auto-refresh">
                    Auto-refreshing every 10 seconds
                </div>
            </div>
            
            <script>
                let refreshInterval;
                
                async function fetchServers() {
                    try {
                        const response = await fetch('/api/servers');
                        if (!response.ok) throw new Error('Failed to fetch servers');
                        return await response.json();
                    } catch (error) {
                        console.error('Error fetching servers:', error);
                        return { servers: [], count: 0 };
                    }
                }
                
                function formatServerCard(server) {
                    const isOnline = server.status === 'running';
                    const statusClass = isOnline ? 'status-running' : 'status-offline';
                    const cardClass = isOnline ? '' : 'offline';
                    
                    return `
                        <div class="server-card ${cardClass}" onclick="viewServer('${server.id}')">
                            <div class="server-header">
                                <div class="server-name">${server.name}</div>
                                <div class="server-status ${statusClass}">
                                    ${isOnline ? '🟢 ONLINE' : '🔴 OFFLINE'}
                                </div>
                            </div>
                            
                            <div class="server-info">
                                <div class="info-row">
                                    <span class="info-label">Server ID:</span>
                                    <span class="info-value">${server.id}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Game ID:</span>
                                    <span class="info-value">${server.game_id}</span>
                                </div>
                                <div class="info-row">
                                    <span class="info-label">Last Seen:</span>
                                    <span class="info-value">
                                        ${server.last_seen ? new Date(server.last_seen * 1000).toLocaleString() : 'Never'}
                                    </span>
                                </div>
                            </div>
                            
                            <div class="server-actions" onclick="event.stopPropagation()">
                                <a href="/server/${server.id}" class="btn">📊 View Details</a>
                                <button class="btn btn-danger" onclick="removeServer('${server.id}')">🗑️ Remove</button>
                            </div>
                        </div>
                    `;
                }
                
                async function updateServerList() {
                    const data = await fetchServers();
                    const serverListDiv = document.getElementById('server-list');
                    
                    if (data.count === 0) {
                        serverListDiv.innerHTML = `
                            <div class="no-servers">
                                📭 No MCP servers registered yet<br>
                                <small>Servers will appear here when they connect to the dashboard</small>
                            </div>
                        `;
                    } else {
                        const serverCards = data.servers.map(formatServerCard).join('');
                        serverListDiv.innerHTML = `
                            <div class="server-grid">
                                ${serverCards}
                            </div>
                        `;
                    }
                }
                
                function viewServer(serverId) {
                    window.location.href = `/server/${serverId}`;
                }
                
                async function removeServer(serverId) {
                    if (confirm('Are you sure you want to remove this server from the dashboard?')) {
                        try {
                            const response = await fetch(`/api/server/${serverId}`, { method: 'DELETE' });
                            if (response.ok) {
                                await updateServerList();
                            } else {
                                alert('Failed to remove server');
                            }
                        } catch (error) {
                            alert('Error removing server: ' + error.message);
                        }
                    }
                }
                
                async function refreshServers() {
                    await updateServerList();
                }
                
                // Initialize dashboard
                updateServerList();
                
                // Set up auto-refresh
                refreshInterval = setInterval(updateServerList, 10000);
                
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

    def _get_server_view_html(self, server_id: str) -> str:
        """Generate individual server view HTML"""
        server = self.registered_servers[server_id]
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{server.name} - MCP Dashboard</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Courier New', monospace;
                    background-color: #1a1a1a;
                    color: #00ff00;
                    line-height: 1.6;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                }}
                
                h1 {{
                    color: #00ffff;
                    text-shadow: 0 0 10px #00ffff;
                }}
                
                .back-btn {{
                    background-color: #333;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    text-decoration: none;
                    transition: all 0.3s ease;
                }}
                
                .back-btn:hover {{
                    background-color: #00ff00;
                    color: #1a1a1a;
                }}
                
                .grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                
                .panel {{
                    background-color: #2a2a2a;
                    border: 2px solid #00ff00;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
                }}
                
                .panel h2 {{
                    color: #ffff00;
                    margin-bottom: 15px;
                    border-bottom: 1px solid #555;
                    padding-bottom: 5px;
                }}
                
                .status-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 10px;
                    margin-bottom: 15px;
                }}
                
                .status-item {{
                    background-color: #333;
                    padding: 10px;
                    border-radius: 4px;
                    border-left: 4px solid #00ff00;
                }}
                
                .status-label {{
                    color: #aaa;
                    font-size: 0.9em;
                }}
                
                .status-value {{
                    color: #fff;
                    font-weight: bold;
                    font-size: 1.1em;
                }}
                
                .room-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 15px;
                }}
                
                .room-card {{
                    background-color: #333;
                    border: 1px solid #555;
                    border-radius: 6px;
                    padding: 15px;
                    transition: all 0.3s ease;
                }}
                
                .room-card:hover {{
                    border-color: #00ff00;
                    box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
                }}
                
                .room-card.current {{
                    border-color: #ffff00;
                    background-color: #3a3a00;
                }}
                
                .room-title {{
                    color: #00ffff;
                    font-weight: bold;
                    margin-bottom: 8px;
                }}
                
                .room-description {{
                    color: #ccc;
                    margin-bottom: 10px;
                    font-size: 0.9em;
                }}
                
                .room-contents {{
                    font-size: 0.8em;
                }}
                
                .room-contents div {{
                    margin-bottom: 5px;
                }}
                
                .items {{
                    color: #ffa500;
                }}
                
                .npcs {{
                    color: #ff69b4;
                }}
                
                .exits {{
                    color: #98fb98;
                }}
                
                .log-container {{
                    max-height: 400px;
                    overflow-y: auto;
                    background-color: #1a1a1a;
                    border: 1px solid #444;
                    padding: 15px;
                    border-radius: 6px;
                }}
                
                .log-entry {{
                    margin-bottom: 8px;
                    padding: 5px;
                    border-left: 3px solid #00ff00;
                    padding-left: 10px;
                }}
                
                .log-timestamp {{
                    color: #888;
                    font-size: 0.8em;
                }}
                
                .log-message {{
                    color: #fff;
                }}
                
                .controls {{
                    text-align: center;
                    margin: 20px 0;
                }}
                
                .btn {{
                    background-color: #2a2a2a;
                    color: #00ff00;
                    border: 2px solid #00ff00;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-family: inherit;
                    margin: 0 10px;
                    transition: all 0.3s ease;
                }}
                
                .btn:hover {{
                    background-color: #00ff00;
                    color: #1a1a1a;
                    box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
                }}
                
                .full-width {{
                    grid-column: 1 / -1;
                }}
                
                .auto-refresh {{
                    color: #888;
                    font-size: 0.8em;
                    text-align: center;
                    margin-top: 10px;
                }}
                
                @media (max-width: 768px) {{
                    .grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .header {{
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 15px;
                    }}
                    
                    .room-grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .status-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎮 {server.name}</h1>
                    <a href="/" class="back-btn">← Back to Dashboard</a>
                </div>
                
                <div id="content">
                    <div class="panel">
                        <h2>Loading game state...</h2>
                        <p>Please wait while the server data loads.</p>
                    </div>
                </div>
                
                <div class="controls">
                    <button class="btn" onclick="refreshData()">🔄 Refresh</button>
                </div>
                
                <div class="auto-refresh">
                    Auto-refreshing every 5 seconds
                </div>
            </div>
            
            <script>
                const serverId = '{server_id}';
                let refreshInterval;
                
                async function fetchGameState() {{
                    try {{
                        const response = await fetch(`/api/server/${{serverId}}/state`);
                        if (!response.ok) throw new Error('Failed to fetch state');
                        return await response.json();
                    }} catch (error) {{
                        console.error('Error fetching game state:', error);
                        return null;
                    }}
                }}
                
                async function fetchGameLogs() {{
                    try {{
                        const response = await fetch(`/api/server/${{serverId}}/logs`);
                        if (!response.ok) throw new Error('Failed to fetch logs');
                        return await response.json();
                    }} catch (error) {{
                        console.error('Error fetching game logs:', error);
                        return [];
                    }}
                }}
                
                function formatRooms(rooms, playerLocation) {{
                    if (!rooms || Object.keys(rooms).length === 0) {{
                        return '<p>No rooms available</p>';
                    }}
                    
                    return Object.values(rooms).map(room => {{
                        const isCurrentRoom = room.id === playerLocation;
                        const items = room.items && room.items.length > 0 ? 
                            `<div class="items">📦 Items: ${{room.items.join(', ')}}</div>` : '';
                        const npcs = room.npcs && room.npcs.length > 0 ? 
                            `<div class="npcs">👥 NPCs: ${{room.npcs.join(', ')}}</div>` : '';
                        const exits = room.connections && Object.keys(room.connections).length > 0 ? 
                            `<div class="exits">🚪 Exits: ${{Object.keys(room.connections).join(', ')}}</div>` : '';
                        
                        return `
                            <div class="room-card ${{isCurrentRoom ? 'current' : ''}}">
                                <div class="room-title">
                                    ${{isCurrentRoom ? '👤 ' : ''}}${{room.name}}
                                </div>
                                <div class="room-description">${{room.description}}</div>
                                <div class="room-contents">
                                    ${{items}}
                                    ${{npcs}}
                                    ${{exits}}
                                </div>
                            </div>
                        `;
                    }}).join('');
                }}
                
                function formatLogs(logs) {{
                    if (!logs || logs.length === 0) {{
                        return '<p>No recent activity</p>';
                    }}
                    
                    return logs.map(log => `
                        <div class="log-entry">
                            <div class="log-timestamp">Turn ${{log.turn}} - ${{new Date(log.timestamp).toLocaleTimeString()}}</div>
                            <div class="log-message">${{log.message}}</div>
                        </div>
                    `).join('');
                }}
                
                async function updateDashboard() {{
                    const [gameState, logs] = await Promise.all([
                        fetchGameState(),
                        fetchGameLogs()
                    ]);
                    
                    const contentDiv = document.getElementById('content');
                    
                    if (!gameState || gameState.error) {{
                        contentDiv.innerHTML = `
                            <div class="panel">
                                <h2>❌ Error</h2>
                                <p>Unable to load game state: ${{gameState?.error || 'Unknown error'}}</p>
                            </div>
                        `;
                        return;
                    }}
                    
                    const player = gameState.players ? Object.values(gameState.players)[0] : null;
                    const playerLocation = player ? player.location : '';
                    const currentRoom = gameState.rooms ? gameState.rooms[playerLocation] : null;
                    
                    contentDiv.innerHTML = `
                        <div class="grid">
                            <div class="panel">
                                <h2>🎯 Game Status</h2>
                                <div class="status-grid">
                                    <div class="status-item">
                                        <div class="status-label">Server</div>
                                        <div class="status-value">${{gameState.server_name || '{server.name}'}}</div>
                                    </div>
                                    <div class="status-item">
                                        <div class="status-label">Title</div>
                                        <div class="status-value">${{gameState.title || 'Unknown'}}</div>
                                    </div>
                                    <div class="status-item">
                                        <div class="status-label">Turn</div>
                                        <div class="status-value">${{gameState.current_turn || 0}}</div>
                                    </div>
                                    <div class="status-item">
                                        <div class="status-label">Status</div>
                                        <div class="status-value">${{gameState.active ? '🟢 Active' : '🔴 Inactive'}}</div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="panel">
                                <h2>👤 Player Info</h2>
                                ${{player ? `
                                    <div class="status-grid">
                                        <div class="status-item">
                                            <div class="status-label">Player Name</div>
                                            <div class="status-value">${{player.name}}</div>
                                        </div>
                                        <div class="status-item">
                                            <div class="status-label">Current Location</div>
                                            <div class="status-value">${{currentRoom ? currentRoom.name : 'Unknown'}}</div>
                                        </div>
                                        <div class="status-item">
                                            <div class="status-label">Inventory Items</div>
                                            <div class="status-value">${{player.inventory ? player.inventory.length : 0}}</div>
                                        </div>
                                    </div>
                                    ${{player.inventory && player.inventory.length > 0 ? 
                                        `<div style="margin-top: 10px;"><strong>Inventory:</strong> ${{player.inventory.join(', ')}}</div>` : 
                                        '<div style="margin-top: 10px; color: #888;">Inventory is empty</div>'
                                    }}
                                ` : '<p>No player found</p>'}}
                            </div>
                            
                            <div class="panel full-width">
                                <h2>🗺️ World Map</h2>
                                <div class="room-grid">
                                    ${{formatRooms(gameState.rooms, playerLocation)}}
                                </div>
                            </div>
                            
                            <div class="panel full-width">
                                <h2>📜 Recent Activity</h2>
                                <div class="log-container">
                                    ${{formatLogs(logs)}}
                                </div>
                            </div>
                        </div>
                    `;
                }}
                
                async function refreshData() {{
                    await updateDashboard();
                }}
                
                // Initialize dashboard
                updateDashboard();
                
                // Set up auto-refresh
                refreshInterval = setInterval(updateDashboard, 5000);
                
                // Clean up on page unload
                window.addEventListener('beforeunload', () => {{
                    if (refreshInterval) {{
                        clearInterval(refreshInterval);
                    }}
                }});
            </script>
        </body>
        </html>
        """

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the dashboard server"""
        import uvicorn
        logger.info(f"Starting MCP Dashboard on http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="info")


def run_dashboard():
    """Run the MCP dashboard server"""
    dashboard = MCPDashboard()
    
    web_port = int(os.getenv("WEB_PORT", "8000"))
    dashboard.run(port=web_port)


if __name__ == "__main__":
    run_dashboard()