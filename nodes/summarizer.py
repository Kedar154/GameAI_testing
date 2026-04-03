from nodes.llms import speed


SUMMARY_PROMPT = """You are summarizing one NPC interaction from a detective game.

Write exactly ONE sentence (max 20 words) that captures the most useful investigative signal from this exchange.

Focus on:
- what the NPC denied, avoided, or revealed
- what topic made them nervous or defensive
- what clue or accusation came up
- any contradiction or suspicious reaction

Do NOT write emotional fluff. Do NOT start with "The player". Be direct and factual.

Examples:
Bell denied poisoning Thorne but became defensive when aconite was mentioned.
Arjun appeared anxious when page 42 was brought up.
Mrs. Graves stayed calm and redirected questions about the pantry.
"""


def summarization_node(state):
    npc_name = state["current_npc"]

    if not npc_name or npc_name not in state["npcs"]:
        return {}

    # officer conversations DO need summarising
    '''if npc_name == "officer":
        return {}'''

    npc          = state["npcs"][npc_name]
    chat_history = npc.chat_history

    if not chat_history:
        return {}

    lastchat = chat_history[-1]

    # only summarise once the NPC has actually replied
    if "npc" not in lastchat:
        return {}

    player_msg  = lastchat["player"]
    npc_reply   = lastchat["npc"]

    prompt = f"""{SUMMARY_PROMPT}

NPC: {npc_name}
Player said: {player_msg}
NPC replied: {npc_reply}

Write the one-line summary now (no quotes, no preamble):"""

    try:
        response     = speed.invoke(prompt)
        summary_line = response.content.strip() if hasattr(response, "content") else str(response).strip()
    except Exception as e:
        print(f"[summarizer] LLM error: {e}")
        return {}

    if not summary_line:
        return {}

    # ✅ Pydantic attribute access — npc is a BaseModel, not a dict
    old_summary        = npc.running_summary or ""
    npc.running_summary = (old_summary + " " + summary_line).strip()

    return {
        "npcs": {
            **state["npcs"],
            npc_name: npc
        }
    }