from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime
from .entities import Player, Room, Item, NPC, LogEntry


class GameState(BaseModel):
    game_id: str
    title: str
    description: str
    current_turn: int
    active: bool
    players: Dict[str, Player]
    rooms: Dict[str, Room] 
    items: Dict[str, Item]
    npcs: Dict[str, NPC]
    global_flags: Dict[str, Any]
    win_conditions: List[dict]
    event_log: List[LogEntry]
    created_at: datetime
    last_action_at: datetime