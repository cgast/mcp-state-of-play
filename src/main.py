import asyncio
import logging
import os
import json
from typing import Optional
from fastmcp import FastMCP
from .state_manager import StateManager
from .game_engine import GameEngine
from .web_interface import create_web_app


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
state_manager: Optional[StateManager] = None
game_engine: Optional[GameEngine] = None
current_game_id: str = "default"
current_player_id: str = "player_1"

# Create MCP server
mcp = FastMCP("state-of-play")


def initialize_game_engine():
    """Initialize the game engine and load default game"""
    global state_manager, game_engine, current_game_id
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    state_manager = StateManager(redis_url)
    game_engine = GameEngine(state_manager)
    
    # Load game configuration
    config_path = "config/game_config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            scenario_config = json.load(f)
        
        # Check if default game already exists
        if not state_manager.game_exists("default"):
            logger.info("Creating new default game...")
            current_game_id = game_engine.start_new_game(scenario_config, "Player")
            # Override game_id to be "default" for consistency
            state = state_manager.load_game_state(current_game_id)
            if state:
                state.game_id = "default"
                state_manager.save_game_state("default", state)
                state_manager.delete_game(current_game_id)
                current_game_id = "default"
        else:
            logger.info("Loading existing default game...")
            current_game_id = "default"
    else:
        logger.warning("No game configuration found, creating minimal game...")
        minimal_config = {
            "title": "Simple Adventure",
            "description": "A basic text adventure",
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
        current_game_id = game_engine.start_new_game(minimal_config, "Player")


@mcp.tool()
def move_player(direction: str) -> str:
    """Move the player in a given direction (north, south, east, west, up, down)"""
    if not game_engine:
        return "Game engine not initialized"
    
    result = game_engine.move_player(current_game_id, current_player_id, direction)
    return result.message


@mcp.tool() 
def look_around() -> str:
    """Get a description of the current room and its contents"""
    if not game_engine:
        return "Game engine not initialized"
    
    return game_engine.look_around(current_game_id, current_player_id)


@mcp.tool()
def take_item(item_name: str) -> str:
    """Take an item from the current room"""
    if not game_engine:
        return "Game engine not initialized"
    
    result = game_engine.take_item(current_game_id, current_player_id, item_name)
    return result.message


@mcp.tool()
def drop_item(item_name: str) -> str:
    """Drop an item from inventory into current room"""
    if not game_engine:
        return "Game engine not initialized"
    
    result = game_engine.drop_item(current_game_id, current_player_id, item_name)
    return result.message


@mcp.tool()
def use_item(item_name: str, target: str = None) -> str:
    """Use an item, optionally on a target"""
    if not game_engine:
        return "Game engine not initialized"
    
    result = game_engine.use_item(current_game_id, current_player_id, item_name, target)
    return result.message


@mcp.tool()
def talk_to_npc(npc_name: str, message: str = None) -> str:
    """Talk to an NPC in the current room"""
    if not game_engine:
        return "Game engine not initialized"
    
    result = game_engine.talk_to_npc(current_game_id, current_player_id, npc_name, message)
    return result.message


@mcp.tool()
def check_inventory() -> str:
    """List items in player's inventory"""
    if not game_engine:
        return "Game engine not initialized"
    
    inventory = game_engine.check_inventory(current_game_id, current_player_id)
    if not inventory:
        return "Your inventory is empty."
    
    items_desc = []
    for item in inventory:
        desc = f"- {item['name']}: {item['description']}"
        if item['useable']:
            desc += " (useable)"
        items_desc.append(desc)
    
    return "Your inventory contains:\n" + "\n".join(items_desc)


@mcp.tool()
def get_available_actions() -> str:
    """Get list of available actions in current context"""
    if not game_engine:
        return "Game engine not initialized"
    
    actions = game_engine.get_available_actions(current_game_id, current_player_id)
    if not actions:
        return "No actions available."
    
    return "Available actions:\n" + "\n".join(f"- {action}" for action in actions)


@mcp.tool()
def get_game_status() -> str:
    """Get current game state summary"""
    if not state_manager:
        return "State manager not initialized"
    
    world_state = state_manager.get_world_state(current_game_id)
    if not world_state:
        return "No active game found"
    
    player = None
    if world_state.get("players"):
        player = list(world_state["players"].values())[0]
    
    status = f"**Game Status**\n"
    status += f"Title: {world_state.get('title', 'Unknown')}\n"
    status += f"Turn: {world_state.get('current_turn', 0)}\n"
    status += f"Active: {world_state.get('active', False)}\n"
    
    if player:
        current_room_id = player.get('location')
        current_room = world_state.get('rooms', {}).get(current_room_id, {})
        status += f"Player Location: {current_room.get('name', 'Unknown')}\n"
        status += f"Inventory Items: {len(player.get('inventory', []))}\n"
    
    return status


@mcp.tool()
def start_new_game(player_name: str = "Player") -> str:
    """Start a new game with given player name"""
    global current_game_id, current_player_id
    
    if not game_engine:
        return "Game engine not initialized"
    
    # Load configuration
    config_path = "config/game_config.json"
    scenario_config = {}
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            scenario_config = json.load(f)
    else:
        scenario_config = {
            "title": "New Adventure",
            "description": "A fresh start to your adventure",
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
    
    # Delete old default game
    if state_manager.game_exists("default"):
        state_manager.delete_game("default")
    
    # Start new game
    new_game_id = game_engine.start_new_game(scenario_config, player_name)
    
    # Update to use "default" as the game ID
    state = state_manager.load_game_state(new_game_id)
    if state:
        state.game_id = "default"
        state_manager.save_game_state("default", state)
        state_manager.delete_game(new_game_id)
        current_game_id = "default"
    
    return f"New game started! Welcome {player_name}!\n\n" + look_around()


@mcp.tool()
def end_game() -> str:
    """End the current game and generate summary"""
    if not game_engine:
        return "Game engine not initialized"
    
    summary = game_engine.end_game(current_game_id, "Player ended game")
    
    if "error" in summary:
        return f"Error ending game: {summary['error']}"
    
    result = f"**Game Summary**\n"
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


def run_mcp_server():
    """Run MCP server in stdio mode"""
    # Initialize game engine
    initialize_game_engine()
    logger.info("Starting MCP server on stdio")
    mcp.run(transport="stdio")


def run_web_server():
    """Run web server only"""
    # Initialize game engine
    initialize_game_engine()
    
    # Create web app
    web_app = create_web_app(state_manager)
    
    # Get port from environment
    web_port = int(os.getenv("WEB_PORT", "8000"))
    
    logger.info(f"Starting web server on port {web_port}")
    
    import uvicorn
    uvicorn.run(web_app, host="0.0.0.0", port=web_port, log_level="info")


async def run_combined_servers():
    """Run both MCP and web servers concurrently"""
    # Initialize game engine
    initialize_game_engine()
    
    # Create web app
    web_app = create_web_app(state_manager)
    
    # Get ports from environment
    web_port = int(os.getenv("WEB_PORT", "8000"))
    
    logger.info(f"Starting web server on port {web_port}")
    
    import uvicorn
    
    # Start web server
    web_config = uvicorn.Config(web_app, host="0.0.0.0", port=web_port, log_level="info")
    web_server = uvicorn.Server(web_config)
    
    try:
        await web_server.serve()
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")


if __name__ == "__main__":
    # Check if we should run in MCP mode or web mode
    mode = os.getenv("RUN_MODE", "web")
    
    if mode == "mcp":
        run_mcp_server()
    elif mode == "combined":
        asyncio.run(run_combined_servers())
    else:
        run_web_server()