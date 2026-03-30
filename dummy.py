# main.py
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Literal

app = FastAPI()
checkpointer = MemorySaver()

# ── State ─────────────────────────────────────────────────────────────────────

class NPCState(TypedDict):
    chat_history:    list[dict]   # {"player": ..., "npc": ...}
    running_summary: str
    suspicion_score: float

class GameState(TypedDict):
    # updated every turn by Unity
    player_input: str
    current_npc:  str                              # "arjun" | "bell" | "graves" | "officer"
    action_type:  str                              # "interrogate" | "search"

    # updated by graph nodes
    intent:       str
    npc_response: str
    search_result: str

    # one entry per NPC, persists across the whole game
    npcs: dict[str, NPCState]

# ── Nodes ─────────────────────────────────────────────────────────────────────

def wait_for_input_node(state: GameState):
    # Freeze. Surface npc_response. Receive next turn's data when resumed.
    turn_data = interrupt(state["npc_response"])
    # turn_data is the dict Unity sends: {player_input, current_npc, action_type}
    return {
        "player_input": turn_data["player_input"],
        "current_npc":  turn_data["current_npc"],
        "action_type":  turn_data["action_type"],
    }

def intent_node(state: GameState):
    # TODO: replace with your LLM intent classifier
    return {"intent": "interrogate"}

def search_node(state: GameState):
    # TODO: query Neo4j based on player_input
    return {"search_result": f"[SEARCH] Found nothing about '{state['player_input']}'"}

def retrieval_node(state: GameState):
    # TODO: Neo4j retrieval for interrogation context
    return {}

def lie_detection_node(state: GameState):
    # TODO: HuggingFace call
    npc_name    = state["current_npc"]
    updated_npcs = dict(state["npcs"])
    updated_npc  = dict(updated_npcs[npc_name])
    updated_npc["suspicion_score"] = 0.72          # dummy
    updated_npcs[npc_name] = updated_npc
    return {"npcs": updated_npcs}

def prompt_construction_node(state: GameState):
    # TODO: build prompt and call NPC LLM
    npc_name = state["current_npc"]
    return {"npc_response": f"[{npc_name.upper()}] I have nothing more to say."}

def search_response_node(state: GameState):
    # Formats search result as npc_response so the graph output is always uniform
    return {"npc_response": state["search_result"]}

def summarization_node(state: GameState):
    npc_name     = state["current_npc"]
    updated_npcs = dict(state["npcs"])
    updated_npc  = dict(updated_npcs[npc_name])

    updated_npc["chat_history"].append({
        "player": state["player_input"],
        "npc":    state["npc_response"],
    })
    updated_npc["running_summary"] += (
        f"\nPlayer: {state['player_input']}\nNPC: {state['npc_response']}"
    )
    updated_npcs[npc_name] = updated_npc
    return {"npcs": updated_npcs}

# ── Routing ───────────────────────────────────────────────────────────────────

def route_action(state: GameState) -> Literal["search_node", "retrieval_node"]:
    # Unity sets action_type — graph routes based on it
    if state["action_type"] == "search":
        return "search_node"
    return "retrieval_node"

# ── Graph ─────────────────────────────────────────────────────────────────────

builder = StateGraph(GameState)

builder.add_node("wait_for_input",    wait_for_input_node)
builder.add_node("intent",            intent_node)
builder.add_node("search_node",       search_node)
builder.add_node("retrieval",         retrieval_node)
builder.add_node("lie_detection",     lie_detection_node)
builder.add_node("prompt_construct",  prompt_construction_node)
builder.add_node("search_response",   search_response_node)
builder.add_node("summarize",         summarization_node)

builder.set_entry_point("wait_for_input")

builder.add_edge("wait_for_input", "intent")

# ← conditional branch after intent
builder.add_conditional_edges("intent", route_action, {
    "search_node":    "search_node",
    "retrieval_node": "retrieval_node",
})

# search path
builder.add_edge("search_node",      "search_response")
builder.add_edge("search_response",  "summarize")

# interrogation path
builder.add_edge("retrieval",        "lie_detection")
builder.add_edge("lie_detection",    "prompt_construct")
builder.add_edge("prompt_construct", "summarize")

# both paths rejoin at summarize → loop
builder.add_edge("summarize",        "wait_for_input")

graph = builder.compile(checkpointer=checkpointer)

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_npc_response(config: dict) -> str:
    snapshot = graph.get_state(config)
    if not snapshot.tasks:
        raise RuntimeError("Graph did not interrupt — check your edges")
    return snapshot.tasks[0].interrupts[0].value

def run_graph(command, config: dict) -> str:
    for _ in graph.stream(command, config=config):
        pass
    return get_npc_response(config)

def make_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}

def empty_npc_state() -> NPCState:
    return {"chat_history": [], "running_summary": "", "suspicion_score": 0.0}

# ── Request / Response Models ─────────────────────────────────────────────────

class StartResponse(BaseModel):
    session_id:   str
    npc_response: str

class TurnRequest(BaseModel):
    session_id:   str
    player_input: str
    current_npc:  Literal["arjun", "bell", "graves", "officer"]
    action_type:  Literal["interrogate", "search"]

class TurnResponse(BaseModel):
    npc_response: str
    current_npc:  str

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/start", response_model=StartResponse)
def start_game():
    session_id = str(uuid.uuid4())
    config     = make_config(session_id)

    initial_state: GameState = {
        "player_input":  "",
        "current_npc":   "officer",
        "action_type":   "interrogate",
        "intent":        "",
        "npc_response":  "Good evening, Detective. Where would you like to begin?",
        "search_result": "",
        "npcs": {
            "officer": empty_npc_state(),
            "arjun":   empty_npc_state(),
            "bell":    empty_npc_state(),
            "graves":  empty_npc_state(),
        }
    }

    npc_response = run_graph(initial_state, config)
    return StartResponse(session_id=session_id, npc_response=npc_response)


@app.post("/turn", response_model=TurnResponse)
def player_turn(req: TurnRequest):
    config   = make_config(req.session_id)
    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Session not found. Call /start first.")

    # Pass all three values Unity sent as the resume payload.
    # wait_for_input_node receives this dict as the return of interrupt().
    resume_payload = {
        "player_input": req.player_input,
        "current_npc":  req.current_npc,
        "action_type":  req.action_type,
    }

    npc_response = run_graph(Command(resume=resume_payload), config)

    return TurnResponse(npc_response=npc_response, current_npc=req.current_npc)


@app.get("/state/{session_id}")   # debug — inspect full game state anytime
def get_state(session_id: str):
    snapshot = graph.get_state(make_config(session_id))
    return snapshot.values


## What Unity Does
'''
Game starts
→ POST /start
← { session_id: "abc-123", npc_response: "Good evening, Detective." }

Player walks up to Arjun, types "where were you?"
→ POST /turn { session_id: "abc-123", player_input: "where were you?",
               current_npc: "arjun", action_type: "interrogate" }
← { npc_response: "[ARJUN] I have nothing more to say.", current_npc: "arjun" }

Player clicks "search library"
→ POST /turn { session_id: "abc-123", player_input: "library",
               current_npc: "arjun", action_type: "search" }
← { npc_response: "[SEARCH] Found nothing about 'library'", current_npc: "arjun" }

Player walks to Bell
→ POST /turn { session_id: "abc-123", player_input: "did you know Arjun?",
               current_npc: "bell", action_type: "interrogate" }
← { npc_response: "[BELL] I have nothing more to say.", current_npc: "bell" }
'''