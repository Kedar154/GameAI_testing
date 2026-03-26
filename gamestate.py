#pip install pydantic
from pydantic import BaseModel
from typing import TypedDict

### ARUSHI MAKE CHANGES HERE 
arjun_prompt=""
bell_prompt=""
graves_prompt=""
officer_prompt=""
###


class NPC(BaseModel):
    npc_id: str
    prompt: str

    retrieved_data: dict = {}
    lies_told: list[str] = []
    lies_caught: list[str] = []
    chat_history: list[dict] = []
    sus: float = 0.0
    running_summary: str = ""
    prompt_final: str = ""
    
    


class Officer(BaseModel):
    chat_history: list[dict] = []
    summary: str = ""
    prompt: str = ""
    prompt_final: str = ""

class State(TypedDict):
    current_npc: str
    evidence_found: list
    npcs: dict[str, NPC]
    officer: Officer

arjun = NPC(npc_id='arjun', prompt=arjun_prompt)
bell = NPC(npc_id='bell', prompt=bell_prompt)
graves = NPC(npc_id='graves', prompt=graves_prompt)
officer = Officer(prompt_final=officer_prompt)
state: State = {
    'current_npc' : "",
    'evidence_found' : [],
    'npcs' : {
        'arjun': arjun,
        'bell': bell,
        'graves': graves
    },
    'officer': officer
    
}