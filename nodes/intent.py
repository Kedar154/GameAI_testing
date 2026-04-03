from nodes.gamestate import State
from nodes.sus import LOCATION_EVIDENCE

keys = list(LOCATION_EVIDENCE.keys())


def intent_node(state: State) -> dict:
    text         = state.get("player_input", "").lower()
    player_input = state.get("player_input", "")

    # ── Search detection ──────────────────────────────────────────────────────
    if "search" in text:
        for location in keys:
            if location.lower() in text:
                return {
                    "search":          True,
                    "search_location": location,   # original casing
                    "current_npc":     "officer",  # always officer when searching
                    "npc_response":    "",          # clear stale response
                }

    # ── NPC switching ─────────────────────────────────────────────────────────
    if "talk to arjun" in text:
        new_npc = "arjun"
    elif "talk to bell" in text:
        new_npc = "bell"
    elif "talk to graves" in text:
        new_npc = "graves"
    elif "talk to officer" in text:
        new_npc = "officer"
    else:
        new_npc = state.get("current_npc", "officer")

    npcs = state["npcs"]
    npc  = npcs[new_npc]
    if npc.chat_history is None:
        npc.chat_history = []
    npc.chat_history.append({"player": player_input})

    return {
        "search":          False,
        "search_location": "",
        "current_npc":     new_npc,
        "npcs":            {**npcs, new_npc: npc},
        "search_result": ""
    }


def router(state: State) -> str:
    if state.get("search") and state.get("search_location", "") != "":
        return "search"
    '''if state.get("accusation_available"):
        return "accusation_available"'''
    current_npc = state.get("current_npc", "officer")
    if current_npc in ("arjun", "bell", "graves"):
        return "npc"
    return "officer"