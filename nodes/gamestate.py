#pip install pydantic
from pydantic import BaseModel
from typing import TypedDict
from nodes.prompt import arjun_prompt, officer_prompt, bell_prompt, graves_prompt


class NPC(BaseModel):
    npc_id: str = ""
    prompt: str = ""

    retrieved_data: str = ""
    lies_told: list[str] = []
    lies_caught: list[str] = []
    chat_history: list[dict] = []
    sus: float = 0.0
    running_summary: str = ""
    prompt_final: str = ""


class State(TypedDict):
    current_npc: str
    evidence_found: list[str]
    locations_unlocked: dict[str, bool]
    accusation_available: bool = False
    npcs: dict[str, NPC]
    player_input: str = "",
    to_Search: str = "",
    
    ## to be changed
    current_location: str = "",
    officer_output: str = "",
    npc_response: str = ""

arjun = NPC(npc_id='arjun', prompt=arjun_prompt)
bell = NPC(npc_id='bell', prompt=bell_prompt)
graves = NPC(npc_id='graves', prompt=graves_prompt)
officer = NPC(npc_id='officer', prompt=officer_prompt)

state: State = {
    "current_npc": "",
    "evidence_found": [],
    "locations_unlocked": {
        "Thorne's study": True,
        "Arjun's office": True,
        "Reading hall": True,
        "Storage room": False,
        "Interrogation": False,
        "Admin office": False,
        "Pantry": False
    },
    "accusation_available": False,
    "npcs": {
        "arjun": arjun,
        "bell": bell,
        "graves": graves,
        'officer': officer
    },
    "player_input": "",
    "to_search": "",
    #to be changed 
    "current_location": "",
    "officer_output": "",
    "action": "",
    "npc_response": ""
}