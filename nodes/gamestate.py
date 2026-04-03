from pydantic import BaseModel
from typing import TypedDict, Optional
from nodes.prompt import arjun_prompt, officer_prompt, bell_prompt, graves_prompt


class NPC(BaseModel):
    npc_id:          str        = "" #preset
    prompt:          str        = "" #preset
    retrieved_data:  str        = "" #retrieval
    lies_told:       list[str]  = [] #interaction
    lies_caught:     list[str]  = [] #lie_detection
    chat_history:    list[dict] = [] #interaction
    sus:             float      = 0.0 #update_gates_node 
    running_summary: str        = "" #summarizer


class State(TypedDict):
    current_npc:          str #intent_node
    search:               bool #intent_node
    search_location:      str #intent_node
    accusation_available: bool #update_gates_node
    last_found_evidence:  Optional[list[str]] #discover_evidence_node  #it was missing, caused sus to never update
    evidence_found:       list[str] #discover_evidence_node
    locations_unlocked:   dict[str, bool] #update_gates_node
    npcs:                 dict[str, NPC] #preset
    player_input:         str #input node
    search_result:       str #discover_evidence_node
    npc_response:         str #prompt_response


arjun   = NPC(npc_id='arjun',   prompt=arjun_prompt)
bell    = NPC(npc_id='bell',    prompt=bell_prompt)
graves  = NPC(npc_id='graves',  prompt=graves_prompt)
officer = NPC(npc_id='officer', prompt=officer_prompt)

state: State = {
    "current_npc":          "officer",
    "search":               False,
    "accusation_available": False,
    "search_location":      "",
    "last_found_evidence":  [],

    "evidence_found": [],
    "locations_unlocked": {
        "Thorne's study": True,
        "Arjun's office": True,
        "Reading hall":   True,
        "Storage room":   False,
        "Interrogation":  False,
        "Admin office":   False,
        "Pantry":         False
    },
    "npcs": {
        "arjun":   arjun,
        "bell":    bell,
        "graves":  graves,
        "officer": officer
    },
    "player_input":  "",
    "search_result": "",
    "npc_response":  ""
}