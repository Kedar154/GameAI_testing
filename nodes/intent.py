from nodes.gamestate import State
'''from nodes.prompt import intent_prompt'''

def intent(state: State) -> str:
    current_npc = state['current_npc']
    
    '''if state['accusation_available'] and current_npc == "graves":
        return "accusation_available"'''
    if state['search'] != False and state['search_location']!= "":
        return "search"
    elif current_npc == "officer":
        return "officer"
    elif current_npc in ['arjun', 'bell', 'graves']:
        return "npc"  # current_npc is arjun, bell, or graves