from nodes.gamestate import State, state
from nodes.retrieval_lie_detection import retrieval, detect_lie
from nodes.summarizer import summarization_node
from nodes.interaction import prompt_response
from nodes.input_node import input_node
from nodes.sus import officer_search_node, discover_evidence_node, accusation_node, update_gates_node
from nodes.intent import intent, intent_node

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

checkpoint = MemorySaver()
garph = StateGraph(State)

garph.add_node("input",                  input_node)
garph.add_node("intent_node",            intent_node)
garph.add_node("retrieve",               retrieval)
garph.add_node("lie_detection",          detect_lie)
garph.add_node("prompt_response",        prompt_response)
garph.add_node("summary",                summarization_node)
garph.add_node("officer_search_node",    officer_search_node)
garph.add_node("discover_evidence_node", discover_evidence_node)
garph.add_node("update_gates_node",      update_gates_node)
garph.add_node("accusation_node",        accusation_node)

garph.set_entry_point("input")
garph.add_edge("input", "intent_node")

garph.add_conditional_edges(
    "intent_node",
    intent,
    {
        "search":               "officer_search_node",
        "npc":                  "retrieve",
        "accusation_available": "accusation_node",
        "officer":              "retrieve",   # officer also goes through retrieval now
    }
)

# both NPC and officer go through retrieve → lie_detection → prompt_response
garph.add_edge("retrieve",               "lie_detection")
garph.add_edge("lie_detection",          "prompt_response")
garph.add_edge("prompt_response",        "summary")
garph.add_edge("summary",                "input")

garph.add_edge("officer_search_node",    "discover_evidence_node")
garph.add_edge("discover_evidence_node", "update_gates_node")
garph.add_edge("update_gates_node",      "input")

garph.add_edge("accusation_node",        "input")

garph_ = garph.compile(checkpointer=checkpoint)
print("graph compiled")