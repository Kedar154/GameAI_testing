from nodes.gamestate import State
from nodes.database_1 import retrieve
from nodes.llms import speed


def retrieval(state: State):
    npc_name = state["current_npc"]
    npc = state["npcs"][npc_name]
    
    last_message = npc.chat_history[-1]  # last message
    message = last_message["player"]
    answer_from_db = retrieve(message)
    npc.retrieved_data = answer_from_db
    
    return {'npcs':
            {
                **state['npcs'],
                npc_name : npc
            }
            }

### add the llm file
## install json....


def detect_lie(state: State):
    
    npc_name = state["current_npc"]
    npc = state["npcs"][npc_name]
    
    last_message = npc.chat_history[-1]  # last message
    player_message = last_message["player"]
    
    lies_told = npc.lies_told
    lies_caught = npc.lies_caught
    evidence_found = state.evidence_found
    
    prompt = f"""
You are a lie detection system for a murder mystery game. 
Respond in JSON only. No explanation. No extra text.

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

REMEMBER: 
dont halucinate and create your own lies

OUTPUT:
resond with this exact structured JSON
{{
"caught" : Respond with the EXACT words used by npc in the lie without altering it or adding any fillers to it,
(if lie is not caught then return "none" nothing else)
}}
[/INST]"""

    raw = speed.invoke(prompt)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        ans = raw[start:end]
        if(ans['caught'] != 'none'):
            lies_caught.append(ans)
            npc.lies_caught = lies_caught
            return {'npcs':
                {
                npc_name: npc
                }
            }
            
    except Exception:
        print("json failed, lie cant be sent, sending no change")
        return {'npcs':
                {
                    **state['npcs'],
                    npc_name: npc
                }
            }
        
print("retrieval_lie_detection.py: run successful")