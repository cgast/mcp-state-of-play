import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .models.game_state import GameState
from .models.entities import Player, Room, Item, NPC, ActionResult, LogEntry
from .state_manager import StateManager


class GameEngine:
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        self.current_game_id = "default"
    
    def start_new_game(self, scenario_config: dict, player_name: str = "Player") -> str:
        """Start a new game and return game_id"""
        try:
            game_id = str(uuid.uuid4())
            
            # Create initial game state
            game_state = GameState(
                game_id=game_id,
                title=scenario_config.get("title", "Text Adventure"),
                description=scenario_config.get("description", "A mysterious adventure awaits..."),
                current_turn=0,
                active=True,
                players={},
                rooms={},
                items={},
                npcs={},
                global_flags=scenario_config.get("global_flags", {}),
                win_conditions=scenario_config.get("win_conditions", []),
                event_log=[],
                created_at=datetime.now(),
                last_action_at=datetime.now()
            )
            
            # Load rooms from config
            for room_data in scenario_config.get("rooms", []):
                room = Room(**room_data)
                game_state.rooms[room.id] = room
            
            # Load items from config
            for item_data in scenario_config.get("items", []):
                item = Item(**item_data)
                game_state.items[item.id] = item
            
            # Load NPCs from config
            for npc_data in scenario_config.get("npcs", []):
                npc = NPC(**npc_data)
                game_state.npcs[npc.id] = npc
            
            # Create player
            player_id = "player_1"
            start_room = scenario_config.get("start_room", list(game_state.rooms.keys())[0] if game_state.rooms else "")
            
            player = Player(
                id=player_id,
                name=player_name,
                location=start_room,
                inventory=[],
                stats={}
            )
            game_state.players[player_id] = player
            
            # Save initial state
            self.state_manager.save_game_state(game_id, game_state)
            self.current_game_id = game_id
            
            # Log game start
            self._log_action(game_id, player_id, "start_game", f"Started new game: {game_state.title}")
            
            return game_id
            
        except Exception as e:
            self.logger.error(f"Failed to start new game: {e}")
            return ""
    
    def move_player(self, game_id: str, player_id: str, direction: str) -> ActionResult:
        """Move player in given direction"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return ActionResult(success=False, message="Game not found or inactive", state_changes={}, triggered_events=[])
            
            player = state.players.get(player_id)
            if not player:
                return ActionResult(success=False, message="Player not found", state_changes={}, triggered_events=[])
            
            current_room = state.rooms.get(player.location)
            if not current_room:
                return ActionResult(success=False, message="Current room not found", state_changes={}, triggered_events=[])
            
            # Check if direction exists
            target_room_id = current_room.connections.get(direction.lower())
            if not target_room_id:
                return ActionResult(
                    success=False, 
                    message=f"You cannot go {direction} from here.", 
                    state_changes={}, 
                    triggered_events=[]
                )
            
            target_room = state.rooms.get(target_room_id)
            if not target_room:
                return ActionResult(success=False, message="Target room not found", state_changes={}, triggered_events=[])
            
            # Check access requirements
            if target_room.access_requirements:
                if not self._check_access_requirements(state, player_id, target_room.access_requirements):
                    return ActionResult(
                        success=False,
                        message="You cannot access that room yet.",
                        state_changes={},
                        triggered_events=[]
                    )
            
            # Move player
            old_location = player.location
            player.location = target_room_id
            state.current_turn += 1
            state.last_action_at = datetime.now()
            
            # Save state
            self.state_manager.save_game_state(game_id, state)
            
            # Log action
            self._log_action(game_id, player_id, "move", f"Moved {direction} to {target_room.name}")
            
            return ActionResult(
                success=True,
                message=f"You go {direction} to {target_room.name}.\n{target_room.description}",
                state_changes={"player_location": target_room_id},
                triggered_events=[]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to move player: {e}")
            return ActionResult(success=False, message="An error occurred", state_changes={}, triggered_events=[])
    
    def take_item(self, game_id: str, player_id: str, item_name: str) -> ActionResult:
        """Take an item from current room"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return ActionResult(success=False, message="Game not found or inactive", state_changes={}, triggered_events=[])
            
            player = state.players.get(player_id)
            if not player:
                return ActionResult(success=False, message="Player not found", state_changes={}, triggered_events=[])
            
            current_room = state.rooms.get(player.location)
            if not current_room:
                return ActionResult(success=False, message="Current room not found", state_changes={}, triggered_events=[])
            
            # Find item in current room
            item = None
            item_id = None
            for iid in current_room.items:
                if iid in state.items:
                    candidate = state.items[iid]
                    if candidate.name.lower() == item_name.lower():
                        item = candidate
                        item_id = iid
                        break
            
            if not item:
                return ActionResult(
                    success=False,
                    message=f"There is no {item_name} here.",
                    state_changes={},
                    triggered_events=[]
                )
            
            if not item.takeable:
                return ActionResult(
                    success=False,
                    message=f"You cannot take the {item_name}.",
                    state_changes={},
                    triggered_events=[]
                )
            
            # Move item to player inventory
            current_room.items.remove(item_id)
            player.inventory.append(item_id)
            item.location = player_id
            state.current_turn += 1
            state.last_action_at = datetime.now()
            
            # Save state
            self.state_manager.save_game_state(game_id, state)
            
            # Log action
            self._log_action(game_id, player_id, "take", f"Took {item.name}")
            
            return ActionResult(
                success=True,
                message=f"You take the {item.name}.",
                state_changes={"item_location": player_id},
                triggered_events=[]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to take item: {e}")
            return ActionResult(success=False, message="An error occurred", state_changes={}, triggered_events=[])
    
    def drop_item(self, game_id: str, player_id: str, item_name: str) -> ActionResult:
        """Drop an item from inventory into current room"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return ActionResult(success=False, message="Game not found or inactive", state_changes={}, triggered_events=[])
            
            player = state.players.get(player_id)
            if not player:
                return ActionResult(success=False, message="Player not found", state_changes={}, triggered_events=[])
            
            current_room = state.rooms.get(player.location)
            if not current_room:
                return ActionResult(success=False, message="Current room not found", state_changes={}, triggered_events=[])
            
            # Find item in player inventory
            item = None
            item_id = None
            for iid in player.inventory:
                if iid in state.items:
                    candidate = state.items[iid]
                    if candidate.name.lower() == item_name.lower():
                        item = candidate
                        item_id = iid
                        break
            
            if not item:
                return ActionResult(
                    success=False,
                    message=f"You don't have a {item_name}.",
                    state_changes={},
                    triggered_events=[]
                )
            
            # Move item to current room
            player.inventory.remove(item_id)
            current_room.items.append(item_id)
            item.location = current_room.id
            state.current_turn += 1
            state.last_action_at = datetime.now()
            
            # Save state
            self.state_manager.save_game_state(game_id, state)
            
            # Log action
            self._log_action(game_id, player_id, "drop", f"Dropped {item.name}")
            
            return ActionResult(
                success=True,
                message=f"You drop the {item.name}.",
                state_changes={"item_location": current_room.id},
                triggered_events=[]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to drop item: {e}")
            return ActionResult(success=False, message="An error occurred", state_changes={}, triggered_events=[])
    
    def use_item(self, game_id: str, player_id: str, item_name: str, target: str = None) -> ActionResult:
        """Use an item, optionally on a target"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return ActionResult(success=False, message="Game not found or inactive", state_changes={}, triggered_events=[])
            
            player = state.players.get(player_id)
            if not player:
                return ActionResult(success=False, message="Player not found", state_changes={}, triggered_events=[])
            
            # Find item in player inventory
            item = None
            item_id = None
            for iid in player.inventory:
                if iid in state.items:
                    candidate = state.items[iid]
                    if candidate.name.lower() == item_name.lower():
                        item = candidate
                        item_id = iid
                        break
            
            if not item:
                return ActionResult(
                    success=False,
                    message=f"You don't have a {item_name}.",
                    state_changes={},
                    triggered_events=[]
                )
            
            if not item.useable:
                return ActionResult(
                    success=False,
                    message=f"You cannot use the {item_name}.",
                    state_changes={},
                    triggered_events=[]
                )
            
            # Apply use effects
            message = f"You use the {item.name}."
            state_changes = {}
            triggered_events = []
            
            if item.use_effects:
                # Process item effects (simplified implementation)
                for effect_type, effect_data in item.use_effects.items():
                    if effect_type == "unlock_room":
                        room_id = effect_data.get("room_id")
                        if room_id in state.rooms:
                            state.rooms[room_id].access_requirements = {}
                            message += f" The {item.name} unlocks access to new areas."
                            triggered_events.append(f"unlocked_{room_id}")
                    elif effect_type == "set_flag":
                        flag_name = effect_data.get("flag")
                        flag_value = effect_data.get("value", True)
                        state.global_flags[flag_name] = flag_value
                        state_changes[f"flag_{flag_name}"] = flag_value
                    elif effect_type == "consume":
                        if effect_data.get("consumed", False):
                            player.inventory.remove(item_id)
                            del state.items[item_id]
                            message += f" The {item.name} is consumed."
            
            state.current_turn += 1
            state.last_action_at = datetime.now()
            
            # Save state
            self.state_manager.save_game_state(game_id, state)
            
            # Log action
            self._log_action(game_id, player_id, "use", f"Used {item.name}" + (f" on {target}" if target else ""))
            
            return ActionResult(
                success=True,
                message=message,
                state_changes=state_changes,
                triggered_events=triggered_events
            )
            
        except Exception as e:
            self.logger.error(f"Failed to use item: {e}")
            return ActionResult(success=False, message="An error occurred", state_changes={}, triggered_events=[])
    
    def talk_to_npc(self, game_id: str, player_id: str, npc_name: str, message: str = None) -> ActionResult:
        """Talk to an NPC in current room"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return ActionResult(success=False, message="Game not found or inactive", state_changes={}, triggered_events=[])
            
            player = state.players.get(player_id)
            if not player:
                return ActionResult(success=False, message="Player not found", state_changes={}, triggered_events=[])
            
            current_room = state.rooms.get(player.location)
            if not current_room:
                return ActionResult(success=False, message="Current room not found", state_changes={}, triggered_events=[])
            
            # Find NPC in current room
            npc = None
            for npc_id in current_room.npcs:
                if npc_id in state.npcs:
                    candidate = state.npcs[npc_id]
                    if candidate.name.lower() == npc_name.lower():
                        npc = candidate
                        break
            
            if not npc:
                return ActionResult(
                    success=False,
                    message=f"There is no {npc_name} here.",
                    state_changes={},
                    triggered_events=[]
                )
            
            # Get dialogue response (simplified)
            dialogue_tree = npc.dialogue_tree
            current_state = npc.dialogue_state
            
            response = "Hello there!"
            if current_state in dialogue_tree:
                dialogue_data = dialogue_tree[current_state]
                response = dialogue_data.get("text", response)
                
                # Check for state transitions
                if "next_state" in dialogue_data:
                    npc.dialogue_state = dialogue_data["next_state"]
            
            state.current_turn += 1
            state.last_action_at = datetime.now()
            
            # Save state
            self.state_manager.save_game_state(game_id, state)
            
            # Log action
            self._log_action(game_id, player_id, "talk", f"Talked to {npc.name}")
            
            return ActionResult(
                success=True,
                message=f"{npc.name}: {response}",
                state_changes={"npc_dialogue_state": npc.dialogue_state},
                triggered_events=[]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to talk to NPC: {e}")
            return ActionResult(success=False, message="An error occurred", state_changes={}, triggered_events=[])
    
    def look_around(self, game_id: str, player_id: str) -> str:
        """Get current room description"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return "Game not found or inactive"
            
            player = state.players.get(player_id)
            if not player:
                return "Player not found"
            
            current_room = state.rooms.get(player.location)
            if not current_room:
                return "Current room not found"
            
            description = f"**{current_room.name}**\n{current_room.description}\n"
            
            # List items
            if current_room.items:
                items_here = []
                for item_id in current_room.items:
                    if item_id in state.items:
                        items_here.append(state.items[item_id].name)
                if items_here:
                    description += f"\nItems here: {', '.join(items_here)}"
            
            # List NPCs
            if current_room.npcs:
                npcs_here = []
                for npc_id in current_room.npcs:
                    if npc_id in state.npcs:
                        npcs_here.append(state.npcs[npc_id].name)
                if npcs_here:
                    description += f"\nPeople here: {', '.join(npcs_here)}"
            
            # List exits
            if current_room.connections:
                exits = list(current_room.connections.keys())
                description += f"\nExits: {', '.join(exits)}"
            
            return description
            
        except Exception as e:
            self.logger.error(f"Failed to look around: {e}")
            return "An error occurred"
    
    def check_inventory(self, game_id: str, player_id: str) -> List[dict]:
        """Get player's inventory"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return []
            
            player = state.players.get(player_id)
            if not player:
                return []
            
            inventory = []
            for item_id in player.inventory:
                if item_id in state.items:
                    item = state.items[item_id]
                    inventory.append({
                        "name": item.name,
                        "description": item.description,
                        "useable": item.useable
                    })
            
            return inventory
            
        except Exception as e:
            self.logger.error(f"Failed to check inventory: {e}")
            return []
    
    def get_available_actions(self, game_id: str, player_id: str) -> List[str]:
        """Get available actions in current context"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state or not state.active:
                return []
            
            player = state.players.get(player_id)
            if not player:
                return []
            
            current_room = state.rooms.get(player.location)
            if not current_room:
                return []
            
            actions = ["look around"]
            
            # Movement actions
            for direction in current_room.connections.keys():
                actions.append(f"go {direction}")
            
            # Item actions
            for item_id in current_room.items:
                if item_id in state.items:
                    item = state.items[item_id]
                    if item.takeable:
                        actions.append(f"take {item.name}")
            
            # Inventory actions
            for item_id in player.inventory:
                if item_id in state.items:
                    item = state.items[item_id]
                    actions.append(f"drop {item.name}")
                    if item.useable:
                        actions.append(f"use {item.name}")
            
            # NPC actions
            for npc_id in current_room.npcs:
                if npc_id in state.npcs:
                    npc = state.npcs[npc_id]
                    actions.append(f"talk to {npc.name}")
            
            actions.append("check inventory")
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Failed to get available actions: {e}")
            return []
    
    def end_game(self, game_id: str, outcome: str) -> dict:
        """End game and generate summary"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if not state:
                return {"error": "Game not found"}
            
            state.active = False
            state.last_action_at = datetime.now()
            
            # Generate summary
            history = self.state_manager.get_game_history(game_id)
            
            summary = {
                "game_id": game_id,
                "title": state.title,
                "outcome": outcome,
                "total_turns": state.current_turn,
                "duration": str(state.last_action_at - state.created_at),
                "final_player_location": list(state.players.values())[0].location if state.players else "",
                "items_collected": len(list(state.players.values())[0].inventory) if state.players else 0,
                "major_events": [entry.message for entry in history if entry.action in ["use", "talk", "start_game"]][:10]
            }
            
            # Save final state
            self.state_manager.save_game_state(game_id, state)
            
            # Log game end
            if state.players:
                player_id = list(state.players.keys())[0]
                self._log_action(game_id, player_id, "end_game", f"Game ended: {outcome}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to end game: {e}")
            return {"error": "Failed to end game"}
    
    def _log_action(self, game_id: str, player_id: str, action: str, message: str) -> None:
        """Helper to log actions"""
        try:
            state = self.state_manager.load_game_state(game_id)
            if state:
                log_entry = LogEntry(
                    timestamp=datetime.now().isoformat(),
                    turn=state.current_turn,
                    action=action,
                    player_id=player_id,
                    message=message
                )
                self.state_manager.add_log_entry(game_id, log_entry)
        except Exception as e:
            self.logger.error(f"Failed to log action: {e}")
    
    def _check_access_requirements(self, state: GameState, player_id: str, requirements: dict) -> bool:
        """Check if player meets access requirements"""
        if not requirements:
            return True
        
        player = state.players.get(player_id)
        if not player:
            return False
        
        # Check inventory requirements
        if "required_items" in requirements:
            required_items = requirements["required_items"]
            player_items = [state.items[item_id].name.lower() for item_id in player.inventory if item_id in state.items]
            for required_item in required_items:
                if required_item.lower() not in player_items:
                    return False
        
        # Check flag requirements
        if "required_flags" in requirements:
            required_flags = requirements["required_flags"]
            for flag_name, required_value in required_flags.items():
                if state.global_flags.get(flag_name) != required_value:
                    return False
        
        return True