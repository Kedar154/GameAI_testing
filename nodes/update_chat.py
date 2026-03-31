from nodes.gamestate import State, state
def update(state: State):       # lowercase, typed correctly
    npc_name = state['current_npc']
    npc = state['npcs'][npc_name]
    player_inp = state['player_input']
    
    old_chat_history = npc.chat_history.copy()  # avoid mutating in place
    old_chat_history.append({'player': player_inp, npc_name: ''})
    npc.chat_history = old_chat_history
    
    return {
        'npcs': {
            **state['npcs'],
            npc_name: npc
        }
    }
    
    
    
    
    
    ## add retrieval for the officer
    