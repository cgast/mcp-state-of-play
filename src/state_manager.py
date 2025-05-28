import redis
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .models.game_state import GameState
from .models.entities import LogEntry


class StateManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.logger = logging.getLogger(__name__)
    
    def save_game_state(self, game_id: str, state: GameState) -> bool:
        """Persist entire game state to Redis"""
        try:
            # Save complete state as JSON
            state_key = f"game:{game_id}:state"
            self.redis_client.set(state_key, state.model_dump_json())
            
            # Save individual components for efficient access
            self._save_entities(game_id, "rooms", state.rooms)
            self._save_entities(game_id, "items", state.items)
            self._save_entities(game_id, "npcs", state.npcs)
            self._save_entities(game_id, "players", state.players)
            
            # Save global flags
            flags_key = f"game:{game_id}:flags"
            self.redis_client.hset(flags_key, mapping=state.global_flags)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to save game state: {e}")
            return False
    
    def load_game_state(self, game_id: str) -> Optional[GameState]:
        """Restore game state from Redis"""
        try:
            state_key = f"game:{game_id}:state"
            state_json = self.redis_client.get(state_key)
            
            if not state_json:
                return None
                
            state_data = json.loads(state_json)
            return GameState(**state_data)
        except Exception as e:
            self.logger.error(f"Failed to load game state: {e}")
            return None
    
    def get_world_state(self, game_id: str) -> dict:
        """Current world snapshot"""
        try:
            state = self.load_game_state(game_id)
            if not state:
                return {}
            
            return {
                "game_id": state.game_id,
                "title": state.title,
                "current_turn": state.current_turn,
                "active": state.active,
                "players": {k: v.model_dump() for k, v in state.players.items()},
                "rooms": {k: v.model_dump() for k, v in state.rooms.items()},
                "items": {k: v.model_dump() for k, v in state.items.items()},
                "npcs": {k: v.model_dump() for k, v in state.npcs.items()},
                "global_flags": state.global_flags
            }
        except Exception as e:
            self.logger.error(f"Failed to get world state: {e}")
            return {}
    
    def update_entity(self, game_id: str, entity_type: str, entity_id: str, data: dict) -> bool:
        """Update specific entities"""
        try:
            entity_key = f"game:{game_id}:{entity_type}"
            self.redis_client.hset(entity_key, entity_id, json.dumps(data))
            
            # Also update in main state
            state = self.load_game_state(game_id)
            if state:
                if entity_type == "rooms" and entity_id in state.rooms:
                    state.rooms[entity_id] = state.rooms[entity_id].model_copy(update=data)
                elif entity_type == "items" and entity_id in state.items:
                    state.items[entity_id] = state.items[entity_id].model_copy(update=data)
                elif entity_type == "npcs" and entity_id in state.npcs:
                    state.npcs[entity_id] = state.npcs[entity_id].model_copy(update=data)
                elif entity_type == "players" and entity_id in state.players:
                    state.players[entity_id] = state.players[entity_id].model_copy(update=data)
                
                state.last_action_at = datetime.now()
                self.save_game_state(game_id, state)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to update entity: {e}")
            return False
    
    def add_log_entry(self, game_id: str, entry: LogEntry) -> bool:
        """Track all game events"""
        try:
            logs_key = f"game:{game_id}:logs"
            self.redis_client.lpush(logs_key, entry.model_dump_json())
            
            # Keep only last 1000 entries to prevent unbounded growth
            self.redis_client.ltrim(logs_key, 0, 999)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to add log entry: {e}")
            return False
    
    def get_game_history(self, game_id: str, limit: int = 100) -> List[LogEntry]:
        """Retrieve event log"""
        try:
            logs_key = f"game:{game_id}:logs"
            log_entries = self.redis_client.lrange(logs_key, 0, limit - 1)
            
            return [LogEntry(**json.loads(entry)) for entry in log_entries]
        except Exception as e:
            self.logger.error(f"Failed to get game history: {e}")
            return []
    
    def game_exists(self, game_id: str) -> bool:
        """Check if game exists"""
        state_key = f"game:{game_id}:state"
        return self.redis_client.exists(state_key) > 0
    
    def delete_game(self, game_id: str) -> bool:
        """Delete all game data"""
        try:
            keys = self.redis_client.keys(f"game:{game_id}:*")
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete game: {e}")
            return False
    
    def _save_entities(self, game_id: str, entity_type: str, entities: dict) -> None:
        """Helper to save entity collections"""
        entity_key = f"game:{game_id}:{entity_type}"
        if entities:
            entity_data = {k: v.model_dump_json() for k, v in entities.items()}
            self.redis_client.hset(entity_key, mapping=entity_data)
        else:
            # Clear the hash if no entities
            self.redis_client.delete(entity_key)