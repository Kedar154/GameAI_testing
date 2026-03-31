from nodes.gamestate import State
from nodes.database_1 import retrieve
from nodes.llms import speed
from pydantic import BaseModel


def retrieval(state: State):
    npc_name = state["current_npc"]
    npc = state["npcs"][npc_name]
    print(npc.chat_history)
    last_message = npc.chat_history[-1]  # last message
    message = f"for {npc_name} player requested: \n{last_message["player"]}"
    answer_from_db = retrieve(message)
    npc.retrieved_data = answer_from_db
    
    return {'npcs':
            {
                **state['npcs'],
                npc_name : npc
            }
            }

class liar(BaseModel):
    caught:str = ""

struct_speed = speed.with_structured_output(liar)

def detect_lie(state: State):
    
    npc_name = state["current_npc"]
    npc = state["npcs"][npc_name]
    
    last_message = npc.chat_history[-1]
    player_message = last_message["player"]
    
    lies_told = npc.lies_told
    lies_caught = npc.lies_caught
    evidence_found = state['evidence_found']
    
    prompt = f"""
You are a lie detection system for a murder mystery game.

PLAYER MESSAGE:
{player_message}

LIES THE NPC HAS TOLD:
{lies_told}

LIES ALREADY CAUGHT:
{lies_caught}

EVIDENCE THE PLAYER HAS FOUND:
{evidence_found}

TASK:
Determine if the player's message has caught or challenged any of the NPC's lies.
A lie is caught if the player references evidence or information that directly contradicts it.

RULES:
- If a lie is caught, return the EXACT words the NPC used in that lie.
- If no lie is caught, return exactly: none
- Do not hallucinate lies that aren't in the list above.
"""

    raw = struct_speed.invoke(prompt)
    #print(raw)
    
    if raw.caught != "none":
        lies_caught.append(raw.caught)
        npc.lies_caught = lies_caught
    
    return {"npcs": {**state["npcs"], npc_name: npc}}
        
print("retrieval_lie_detection.py: run successful")