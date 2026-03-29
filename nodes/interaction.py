
from nodes.gamestate import State
from nodes.llms import conv
from pydantic import BaseModel
from typing import Optional

class LLMOutput(BaseModel):
    response: str
    lies_told: list[str] = []
    

def prompt_repsonse(state: State):
    npc_id = state["current_npc"]
    if not npc_id:
        raise ValueError("current_npc not set")
    
    
    npc = state['npcs'][npc_id]


    # SPECIAL CASE: OFFICER
    if npc_id == "officer":
        chat_hist = state['npcs'][npc_id].chat_history
        player_message = chat_hist[-1]['player']
        running_summ = state['npcs'][npc_id].running_summary
        prompt_final = f"""
            {npc.prompt}

            --- CASE FILE ---
            Evidence Found: {state["evidence_found"]}
            current npc: {state['current_npc']}
            Can the player accuse a killer: {state['accusation_available']}
            locations for search: {state['locations_unlocked']}
            lies caught by player of the current npc: {state['npcs'][npc_id].lies_caught}
            running summary of the conversation: {running_summ}
            
            Player's message: {player_message}
            
            *VERY IMPORTANT:*
            Respond ONLY in JSON:
            {{
            "response": "...",
            }}
            """
    else:
        # NORMAL NPC PROMPT BUILD
        
        player_message = chat_hist[-1]['player']
        running_summ = state['npcs'][npc_id].running_summary
        prompt_final = f"""
            {npc.prompt}

            --- GAME STATE ---
            Evidence Found: {state["evidence_found"]}
            Lies Told by {npc_id}: {npc.lies_told}
            Lies Caught by player: {npc.lies_caught}
            Suspicion Level: {npc.sus}
            running summary of the conversation: {running_summ}
            
            Player's message: {player_message}

            Your task is to generate reponse to player message and protect your interests
            you must make sure that in your generated response you make note of what lies you have told 
            This is a very important task, you have to find the lies in the response by checking if it contradicts your believes or knowledge or history to hide what you have done 
            
            your behaviour has to change with sus score, you must get more and more nerveous with increase in sus score and lies_caught
            you must output a json with field as mentioned below 
            *VERY IMPORTANT:*
            Respond ONLY in JSON:
            {{
            "response": "...",
            "lies_told": ["..."] //only the new lies told in the response, DO NOT include previous lies here
            }}
            
            DO NOT HALUCINATE
            """

    # LLM CALL needed to be changes based on the llm used and required module to be imported
    
    response = conv.invoke(prompt_final)
    raw_output = response.content

    # PARSE OUTPUT
    try:
        parsed = LLMOutput.model_validate_json(raw_output)
    except:
        parsed = LLMOutput(response=raw_output, lies_told=[])

    # UPDATE STATE
    del chat_hist[-1]['player']
    last_message = { 'player' : player_message, 'npc' : parsed.response}
    chat_hist.append(last_message)
    npc.chat_history = chat_hist

    if(npc_id != 'officer'):
        new_lies = parsed.lies_told
        old_lies = npc.lies_told
        old_lies.extend(new_lies)
        npc.lies_told = old_lies

    state["npcs"][npc_id] = npc

    return {'npcs': {
            **state['npcs'], npc_id : npc
    }}

print("interaction.py: run successful")