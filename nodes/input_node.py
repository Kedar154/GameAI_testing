from nodes.gamestate import State
from langgraph.types import interrupt


def input_node(state: State):
    # Pause here and wait for player input.
    # intent_node (next) handles pushing the message into chat history.
    player_input = interrupt(state.get("npc_response", ""))
    return {"player_input": player_input}