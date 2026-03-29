from nodes.gamestate import State
from langgraph.types import interrupt


def input_node(state):
    player_input = interrupt(state["npc_response"])  # ← (2) graph freezes here
    return {'player_input': player_input }

