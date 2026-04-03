from nodes.gamestate import State, state
def update(state: State):       # lowercase, typed correctly
    player_inp = state['player_input']
    
    if(state['current_npc'] != "search"):
        npc_name = state['current_npc'] if state['current_npc'] else "officer"
        npc = state['npcs'][npc_name]
        
        
        old_chat_history = npc.chat_history.copy()  # avoid mutating in place
        old_chat_history.append({'player': player_inp, npc_name: ''})
        npc.chat_history = old_chat_history
        
        return {
            'npcs': {
                **state['npcs'],
                npc_name: npc
            }
        }
    else:
        print("i forgot wht to put here")
    
    
    
    
    
    ## add retrieval for the officer
    
    
    
    
    
    