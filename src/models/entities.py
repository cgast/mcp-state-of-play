from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class Room(BaseModel):
    id: str
    name: str
    description: str
    connections: Dict[str, str]  # direction -> room_id
    items: List[str]  # item_ids
    npcs: List[str]   # npc_ids
    state_flags: Dict[str, Any]
    access_requirements: Dict[str, Any] = {}


class Item(BaseModel):
    id: str
    name: str
    description: str
    location: str  # room_id or player_id or npc_id
    takeable: bool
    useable: bool
    properties: Dict[str, Any]
    use_effects: Dict[str, Any] = {}


class NPC(BaseModel):
    id: str
    name: str
    description: str
    location: str  # room_id
    dialogue_state: str
    dialogue_tree: Dict[str, Any]
    inventory: List[str]


class Player(BaseModel):
    id: str
    name: str
    location: str  # room_id
    inventory: List[str]  # item_ids
    stats: Dict[str, Any] = {}


class LogEntry(BaseModel):
    timestamp: str
    turn: int
    action: str
    player_id: str
    message: str
    state_changes: Dict[str, Any] = {}


class ActionResult(BaseModel):
    success: bool
    message: str
    state_changes: Dict[str, Any]
    triggered_events: List[str]
    game_ended: bool = False