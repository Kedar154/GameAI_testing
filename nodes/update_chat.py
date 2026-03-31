from nodes.gamestate import State, state
def update(State):
    npc_name = state['current_npc']
    npc = state['npcs'][npc_name]
    player_inp = state['player_input']
    '''
       [ { 'player' : ... , 'npc' : ....}, { ... }, ]
    '''
    
    old_chat_history = npc.chat_history
    s = [{
        'player' : player_inp, 'npc' : ""
    }]
    old_chat_history.extend(s)
    npc.chat_history = old_chat_history
    
    return {'npcs':
            {
                **state['npcs'],
                npc_name : npc
            }
            }