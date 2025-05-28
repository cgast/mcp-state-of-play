# State of Play - LLM-Powered Text Adventure MCP Server

A minimal MCP (Model Context Protocol) server that manages the state of text adventure games. Built with Python, FastMCP, Redis, and FastAPI.

## Features

- **MCP Server**: Exposes game actions as MCP tools for LLM interaction
- **Redis State Management**: Persistent game state storage
- **Web Dashboard**: Real-time game state monitoring
- **Docker Support**: Easy deployment with Docker Compose
- **Zork-style Gameplay**: Classic text adventure mechanics

## Architecture

```
state-of-play/
├── src/
│   ├── main.py              # MCP server entry point
│   ├── game_engine.py       # Core game logic
│   ├── state_manager.py     # Redis state management
│   ├── web_interface.py     # FastAPI web server
│   └── models/
│       ├── game_state.py    # Game state models
│       └── entities.py      # Room, Item, NPC models
├── config/
│   └── game_config.json    # Game scenario configuration
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Quick Start

### With Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd state-of-play
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access the web dashboard at `http://localhost:8000`

4. To run the MCP server separately (for LLM interaction):
```bash
# Set environment for MCP mode
RUN_MODE=mcp python -m src.main
```

### Local Development

1. Install Redis:
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis
```

2. Start Redis:
```bash
redis-server
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Run the web server:
```bash
python -m src.main
```

Or run the MCP server for LLM interaction:
```bash
RUN_MODE=mcp python -m src.main
```

## MCP Tools

The server exposes these MCP tools for LLM interaction:

- `move_player(direction)` - Move in a direction (north, south, east, west, up, down)
- `look_around()` - Get current room description
- `take_item(item_name)` - Take an item from the current room
- `drop_item(item_name)` - Drop an item into the current room
- `use_item(item_name, target)` - Use an item, optionally on a target
- `talk_to_npc(npc_name, message)` - Talk to an NPC
- `check_inventory()` - List player's inventory
- `get_available_actions()` - Get context-aware action list
- `get_game_status()` - Get current game state summary
- `start_new_game(player_name)` - Start a new game
- `end_game()` - End game and generate summary

## Game Configuration

Games are configured via `config/game_config.json`. The included example features:

- **Setting**: Mysterious laboratory escape room
- **Objective**: Find and assemble the master key to escape
- **Mechanics**: Item collection, NPC dialogue, puzzle solving
- **Rooms**: Laboratory entrance, main lab, storage room, secure vault
- **Items**: Key cards, power cells, tools, key fragments
- **NPCs**: Helpful scientist with dialogue tree

## Web Dashboard

The web interface at `http://localhost:8000` provides:

- Real-time game state visualization
- Interactive room map with player location
- Inventory and item tracking
- Event log with game history
- Game reset functionality
- Auto-refreshing display (every 5 seconds)

## Redis Data Structure

Game state is stored in Redis with these key patterns:

- `game:{game_id}:state` - Complete game state JSON
- `game:{game_id}:rooms` - Room data hash
- `game:{game_id}:items` - Item data hash
- `game:{game_id}:npcs` - NPC data hash
- `game:{game_id}:players` - Player data hash
- `game:{game_id}:logs` - Chronological event list
- `game:{game_id}:flags` - Global game flags

## Environment Variables

- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379`)
- `MCP_PORT` - MCP server port (default: `3000`)
- `WEB_PORT` - Web interface port (default: `8000`)
- `RUN_MODE` - Server mode: `web` (default), `mcp`, or `combined`

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Style

The project follows PEP 8 and uses type hints throughout. Format code with:

```bash
pip install black isort
black .
isort .
```

## Extending the Game

### Adding New Rooms

Edit `config/game_config.json` and add room objects with:
- Unique `id`
- Descriptive `name` and `description`
- `connections` to other rooms
- `items` and `npcs` lists
- Optional `access_requirements`

### Adding Items

Items support:
- `takeable` and `useable` flags
- Custom `properties`
- `use_effects` for game state changes
- Location tracking (room, player, or NPC)

### Adding NPCs

NPCs feature:
- Dialogue trees with state transitions
- Inventory management
- Location-based interactions

## API Reference

### Web API Endpoints

- `GET /` - Game dashboard HTML
- `GET /api/state` - Current game state JSON
- `GET /api/logs` - Game event history JSON
- `POST /api/reset` - Reset game to initial state

### Game Engine Methods

See `src/game_engine.py` for the complete API including:
- Player movement and actions
- Item manipulation
- NPC interactions
- State persistence
- Event logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the GitHub issues page
- Review the configuration examples
- Examine the web dashboard for state debugging