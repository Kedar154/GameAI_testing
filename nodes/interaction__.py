from nodes.gamestate import State
from nodes.llms import conv
from pydantic import BaseModel, Field
import re #json cleaning
class LLMOutput(BaseModel):
    response: str
    lies_told: list[str] = Field(default_factory=list)



BREAKDOWNS = {
    "graves": [25, 55, 85],
    "bell": [20, 40, 65],
    "arjun": [15, 35, 60]
}

STATE_LABELS = {
    "graves": ["composed", "crack", "shaken", "collapse"],
    "bell": ["defensive", "uneasy", "shaken", "break"],
    "arjun": ["guarded", "fracture", "shaken", "collapse"]
}

BEHAVIOR_RULES = {
    "graves": {
        "composed": "calm, controlled, superior tone, answers cleanly, no over-explaining",
        "crack": "irritated, shorter replies, defensive tone, subtle contradictions",
        "shaken": "loses composure, reframes evidence, partial admissions, fear beneath anger",
        "collapse": "mask slips, bitter, near-confession fragments, emotional fatigue, no counter-questions"
    },
    "bell": {
        "defensive": "irritated, sarcastic, dismissive",
        "uneasy": "over-explains, reacts strongly to poison, defensive",
        "shaken": "contradictions increase, partial admissions, visible fear",
        "break": "blurts details, self-preserving, may implicate others"
    },
    "arjun": {
        "guarded": "hesitant, indirect answers, intellectual tone",
        "fracture": "anxious, defensive, overexplains",
        "shaken": "fear visible, partial truth, emotional tone",
        "collapse": "admits concealment, emotional breakdown, stops lying"
    }
}


def get_breakdown_state(npc_id, sus):
    b1, b2, b3 = BREAKDOWNS[npc_id]

    if sus < b1:
        return STATE_LABELS[npc_id][0]
    elif sus < b2:
        return STATE_LABELS[npc_id][1]
    elif sus < b3:
        return STATE_LABELS[npc_id][2]
    else:
        return STATE_LABELS[npc_id][3]


def prompt_repsonse(state: State):

    npc_id = state["current_npc"]
    if not npc_id:
        raise ValueError("current_npc not set")

    npc = state['npcs'][npc_id]
    chat_hist = npc.chat_history.copy()  # don't mutate original

    if not chat_hist or 'player' not in chat_hist[-1]:
        raise ValueError("No player message found in chat history")

    player_message = chat_hist[-1]['player']
    running_summ = npc.running_summary

    if npc_id == "officer":
        prompt_final = f"""
{npc.prompt}

--- CASE FILE ---
evidence: {state["evidence_found"]}
locations: {state['locations_unlocked']}
accusation_available: {state['accusation_available']}

summary: {running_summ}
player: {player_message}

RULES:
- Creatively craft responses that feel natural and adhere to facts and dont say something contradictory

OUTPUT JSON ONLY:
{{
"response": "..."
}}
"""

    else:
        breakdown_state = get_breakdown_state(npc_id, npc.sus)
        behavior = BEHAVIOR_RULES[npc_id][breakdown_state]

        prompt_final = f"""
{npc.prompt}

--- STATE ---
breakdown_state: {breakdown_state}
behavior: {behavior}

evidence: {state["evidence_found"]}
lies_caught: {npc.lies_caught}
sus: {npc.sus}

summary: {running_summ}
player: {player_message}

DEFINITION OF LIE:
A lie is any statement that contradicts your SECRET, LIE, or TIMELINE.
Only include lies explicitly stated.
Do NOT invent hidden lies.

BEHAVIOR RULES:
- Follow breakdown state strictly
- Answer only what is asked
- Do not volunteer extra information unless pressured

TASK:
Respond while protecting your interests.

OUTPUT JSON ONLY:
{{
"response": "...",
"lies_told": []
}}
"""

    response = conv.invoke(prompt_final)
    raw_output = response.content

    cleaned = re.sub(r"```json\s*|\s*```", "", raw_output).strip()

    try:
        parsed = LLMOutput.model_validate_json(cleaned)
    except Exception:
        parsed = LLMOutput(response=cleaned, lies_told=[])

    chat_hist[-1] = {
        "player": player_message,
        "npc": parsed.response
    }

    #print(f"trial: {parsed.response}")

    npc.chat_history =  chat_hist

    if npc_id != 'officer':
        npc.lies_told = list(set(npc.lies_told + parsed.lies_told))


    #print(f"chat hist: {npc.chat_history}")
    
    
    return {
        "npcs": {
            **state['npcs'],
            npc_id: npc
        }
    }
    
print("interaction.py ran succesfully")