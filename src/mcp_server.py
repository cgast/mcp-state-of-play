import asyncio
import logging
import os
import json
import time
from typing import Optional
from fastmcp import FastMCP
from .state_manager import StateManager
from .game_engine import GameEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPGameServer:
    def __init__(self, server_id: str, server_name: str, game_config_path: str = None):
        self.server_id = server_id
        self.server_name = server_name
        self.game_config_path = game_config_path or "config/game_config.json"
        self.current_game_id = f"game_{server_id}"
        self.current_player_id = "player_1"
        
        # Initialize components
        self.state_manager: Optional[StateManager] = None
        self.game_engine: Optional[GameEngine] = None
        
        # Create MCP server
        self.mcp = FastMCP(f"state-of-play-{server_id}")
        
        # Register server with registry
        self.registry_url = os.getenv("REGISTRY_URL", "http://dashboard:8000")
        
        # Setup MCP tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.mcp.tool()
        def move_player(direction: str) -> str:
            """Move the player in a given direction (north, south, east, west, up, down)"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            result = self.game_engine.move_player(self.current_game_id, self.current_player_id, direction)
            return result.message

        @self.mcp.tool() 
        def look_around() -> str:
            """Get a description of the current room and its contents"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            return self.game_engine.look_around(self.current_game_id, self.current_player_id)

        @self.mcp.tool()
        def take_item(item_name: str) -> str:
            """Take an item from the current room"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            result = self.game_engine.take_item(self.current_game_id, self.current_player_id, item_name)
            return result.message

        @self.mcp.tool()
        def drop_item(item_name: str) -> str:
            """Drop an item from inventory into current room"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            result = self.game_engine.drop_item(self.current_game_id, self.current_player_id, item_name)
            return result.message

        @self.mcp.tool()
        def use_item(item_name: str, target: str = None) -> str:
            """Use an item, optionally on a target"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            result = self.game_engine.use_item(self.current_game_id, self.current_player_id, item_name, target)
            return result.message

        @self.mcp.tool()
        def talk_to_npc(npc_name: str, message: str = None) -> str:
            """Talk to an NPC in the current room"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            result = self.game_engine.talk_to_npc(self.current_game_id, self.current_player_id, npc_name, message)
            return result.message

        @self.mcp.tool()
        def check_inventory() -> str:
            """List items in player's inventory"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            inventory = self.game_engine.check_inventory(self.current_game_id, self.current_player_id)
            if not inventory:
                return "Your inventory is empty."
            
            items_desc = []
            for item in inventory:
                desc = f"- {item['name']}: {item['description']}"
                if item['useable']:
                    desc += " (useable)"
                items_desc.append(desc)
            
            return "Your inventory contains:\n" + "\n".join(items_desc)

        @self.mcp.tool()
        def get_available_actions() -> str:
            """Get list of available actions in current context"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            actions = self.game_engine.get_available_actions(self.current_game_id, self.current_player_id)
            if not actions:
                return "No actions available."
            
            return "Available actions:\n" + "\n".join(f"- {action}" for action in actions)

        @self.mcp.tool()
        def get_game_status() -> str:
            """Get current game state summary"""
            if not self.state_manager:
                return "State manager not initialized"
            
            world_state = self.state_manager.get_world_state(self.current_game_id)
            if not world_state:
                return "No active game found"
            
            player = None
            if world_state.get("players"):
                player = list(world_state["players"].values())[0]
            
            status = f"**Game Status**\n"
            status += f"Server: {self.server_name}\n"
            status += f"Title: {world_state.get('title', 'Unknown')}\n"
            status += f"Turn: {world_state.get('current_turn', 0)}\n"
            status += f"Active: {world_state.get('active', False)}\n"
            
            if player:
                current_room_id = player.get('location')
                current_room = world_state.get('rooms', {}).get(current_room_id, {})
                status += f"Player Location: {current_room.get('name', 'Unknown')}\n"
                status += f"Inventory Items: {len(player.get('inventory', []))}\n"
            
            return status

        @self.mcp.tool()
        def start_new_game(player_name: str = "Player") -> str:
            """Start a new game with given player name"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            # Load configuration
            scenario_config = self._load_game_config()
            
            # Delete old game
            if self.state_manager.game_exists(self.current_game_id):
                self.state_manager.delete_game(self.current_game_id)
            
            # Start new game
            new_game_id = self.game_engine.start_new_game(scenario_config, player_name)
            
            # Update to use server-specific game ID
            state = self.state_manager.load_game_state(new_game_id)
            if state:
                state.game_id = self.current_game_id
                self.state_manager.save_game_state(self.current_game_id, state)
                self.state_manager.delete_game(new_game_id)
            
            return f"New game started on {self.server_name}! Welcome {player_name}!\n\n" + look_around()

        @self.mcp.tool()
        def end_game() -> str:
            """End the current game and generate summary"""
            if not self.game_engine:
                return "Game engine not initialized"
            
            summary = self.game_engine.end_game(self.current_game_id, "Player ended game")
            
            if "error" in summary:
                return f"Error ending game: {summary['error']}"
            
            result = f"**Game Summary ({self.server_name})**\n"
            result += f"Title: {summary.get('title', 'Unknown')}\n"
            result += f"Outcome: {summary.get('outcome', 'Unknown')}\n"
            result += f"Total Turns: {summary.get('total_turns', 0)}\n"
            result += f"Duration: {summary.get('duration', 'Unknown')}\n"
            result += f"Items Collected: {summary.get('items_collected', 0)}\n"
            
            if summary.get('major_events'):
                result += f"\n**Major Events:**\n"
                for event in summary['major_events']:
                    result += f"- {event}\n"
            
            return result

        @self.mcp.tool()
        def get_server_info() -> str:
            """Get information about this MCP server"""
            return json.dumps({
                "server_id": self.server_id,
                "server_name": self.server_name,
                "game_id": self.current_game_id,
                "status": "running",
                "uptime": time.time() - getattr(self, '_start_time', time.time())
            })

    def _load_game_config(self):
        """Load game configuration from file"""
        if os.path.exists(self.game_config_path):
            with open(self.game_config_path, 'r') as f:
                return json.load(f)
        else:
            # Default minimal config
            return {
                "title": f"Adventure on {self.server_name}",
                "description": "A text adventure game",
                "start_room": "start",
                "rooms": [
                    {
                        "id": "start",
                        "name": "Starting Room",
                        "description": "A simple room to begin your adventure.",
                        "connections": {},
                        "items": [],
                        "npcs": [],
                        "state_flags": {}
                    }
                ],
                "items": [],
                "npcs": [],
                "global_flags": {},
                "win_conditions": []
            }

    def initialize_game_engine(self):
        """Initialize the game engine and load default game"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.state_manager = StateManager(redis_url)
        self.game_engine = GameEngine(self.state_manager)
        
        # Log which config file is being used
        logger.info(f"Server {self.server_id} ({self.server_name}) loading config from: {self.game_config_path}")
        
        # Load game configuration
        scenario_config = self._load_game_config()
        
        # Check if game already exists
        if not self.state_manager.game_exists(self.current_game_id):
            logger.info(f"Creating new game for server {self.server_id}...")
            new_game_id = self.game_engine.start_new_game(scenario_config, "Player")
            # Override game_id to be server-specific
            state = self.state_manager.load_game_state(new_game_id)
            if state:
                state.game_id = self.current_game_id
                self.state_manager.save_game_state(self.current_game_id, state)
                self.state_manager.delete_game(new_game_id)
        else:
            logger.info(f"Loading existing game for server {self.server_id}...")

    async def register_with_dashboard(self):
        """Register this server with the dashboard"""
        try:
            import aiohttp
            server_info = {
                "id": self.server_id,
                "name": self.server_name,
                "url": f"http://mcp-server-{self.server_id}:{os.getenv('MCP_PORT', '8001')}/mcp",
                "game_id": self.current_game_id,
                "status": "running"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.registry_url}/api/register", json=server_info) as response:
                    if response.status == 200:
                        logger.info(f"Successfully registered server {self.server_id} with dashboard")
                    else:
                        logger.warning(f"Failed to register with dashboard: {response.status}")
        except Exception as e:
            logger.warning(f"Could not register with dashboard: {e}")

    def run(self):
        """Run the MCP server"""
        self._start_time = time.time()
        
        # Initialize game engine
        self.initialize_game_engine()
        
        # Get MCP port from environment
        mcp_port = int(os.getenv("MCP_PORT", "8001"))
        
        logger.info(f"Starting MCP server {self.server_id} ({self.server_name}) on port {mcp_port}")
        logger.info(f"MCP server running at http://0.0.0.0:{mcp_port}/mcp")
        
        # Register with dashboard in background using subprocess
        self._register_with_dashboard_async()
        
        # Run MCP server
        self.mcp.run(transport="streamable-http", port=mcp_port, host="0.0.0.0", path="/mcp")

    def _register_with_dashboard_async(self):
        """Register with dashboard in a background process"""
        try:
            import subprocess
            import threading
            
            def register():
                try:
                    # Wait a bit for the server to fully start
                    time.sleep(3)
                    
                    # Use the registration script
                    result = subprocess.run([
                        "python3", "/app/register_server.py"
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully registered server {self.server_id} with dashboard")
                    else:
                        logger.warning(f"Failed to register with dashboard: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"Registration process failed: {e}")
            
            # Start registration in background thread
            registration_thread = threading.Thread(target=register, daemon=True)
            registration_thread.start()
            
        except Exception as e:
            logger.warning(f"Could not start registration process: {e}")


def run_mcp_server():
    """Run MCP server with configuration from environment"""
    server_id = os.getenv("SERVER_ID", "server1")
    server_name = os.getenv("SERVER_NAME", f"Game Server {server_id}")
    config_path = os.getenv("GAME_CONFIG_PATH", "config/game_config.json")
    
    server = MCPGameServer(server_id, server_name, config_path)
    server.run()


if __name__ == "__main__":
    run_mcp_server()