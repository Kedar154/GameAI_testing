from nodes.gamestate import State
from pydantic import BaseModel
from nodes.llms import speed
from nodes.sus import LOCATION_EVIDENCE
#from nodes.prompt import intent_prompt

keys = list(LOCATION_EVIDENCE.keys())
intent_prompt = f'''
    Role: You are an intent classifier. Identify the intention of the user in the given prompt.
    
    The suspects in the game are: arjun, bell, graves.
    The searchable locations in the game are: Bedroom, Kitchen, Garden, Study.
    
    OUTPUT: Return a JSON with the following fields:
    - conversation_with_suspects: true if the user wants to talk to a suspect, else false
    - suspect_name: the name of the suspect (Arjun, Bell, or Graves) if conversation_with_suspects is true, else null
    - conversation_with_officer: true if the user wants to talk to the officer, else false
    - search_for_evidence: true if the user wants to search for evidence, else false
    - search_location: the location to search {keys} if search_for_evidence is true, else null
    - accusing_graves_as_killer: true if the user is accusing a suspect as killer, else false
'''

class intent_engg(BaseModel):
    conversation_with_suspects: bool
    suspect_name: str | None
    conversation_with_officer: bool
    search_for_evidence: bool
    search_location: str | None
    accusing_graves_as_killer: bool

structured_speed = speed.with_structured_output(intent_engg)

def intent(state):
    input = state['player_input']
    result: intent_engg = structured_speed.invoke([
        {"role": "system", "content": intent_prompt},
        {"role": "user", "content": input}
    ])
    if(result.conversation_with_officer):
        return "officer"
    elif(result.suspect_name!=None):
        return result.suspect_name
    elif(result.search_for_evidence):
        if(result.search_location in keys):
            return f"search {result.search_location}"
        else:
            return "wrong_location"
    elif(result.accusing_graves_as_killer):
        return "accusing murder"
