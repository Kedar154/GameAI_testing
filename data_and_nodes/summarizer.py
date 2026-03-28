from llms import speed


SUMMARY_PROMPT = """You are summarizing one NPC interaction from a detective game.

Write exactly ONE sentence (max 20 words) that captures the most useful investigative signal from this exchange.

Focus on:
- what the NPC denied, avoided, or revealed
- what topic made them nervous or defensive
- what clue or accusation came up
- any contradiction or suspicious reaction

Do NOT write emotional fluff. Do NOT start with "The player". Be direct and factual.

Examples:
"Bell denied poisoning Thorne but became defensive when aconite was mentioned."
"Arjun appeared anxious when page 42 was brought up."
"Mrs. Graves stayed calm and redirected questions about the pantry."
"""


def summarization_node(state):
    npc_name = state["current_npc"]

    if not npc_name or npc_name not in state["npcs"]:
        return {}

    npc = state["npcs"][npc_name]
    chat_history = npc.chat_history

    if not chat_history:
        return {}

    lastchat = chat_history[-1]
    player_input = lastchat["player"]
    npc_response = lastchat["npc"]

    prompt_edited = f"""
{SUMMARY_PROMPT}

Here is the data:
NPC: {npc_name}
Player said: {player_input}
NPC replied: {npc_response}

Write the one-line summary now:
"""

    response = speed.invoke(prompt_edited)

    summary_line = response.content.strip() if hasattr(response, "content") else str(response).strip()

    old_summary = npc["running_summary"]
    new_summary = old_summary+ summary_line
    npc['running_summary'] = new_summary
    return {'npcs':
            {
                **global_state['npcs'],
                npc_name: npc
            }
    }