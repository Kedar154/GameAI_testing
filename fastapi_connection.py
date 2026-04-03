# FastAPI server — The Shimla Ledger
# Run: uvicorn main:app --reload 
# Test: http://localhost:8000/docs

import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

from nodes.graph     import garph
from nodes.gamestate import state

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

THREAD = {"configurable": {"thread_id": "shimla_default"}}


# ── Location keyword map — text search extraction ─────────────
LOCATION_KEYWORDS = {
    "Thorne's study":  ["thorne", "study", "thorne's study"],
    "Arjun's office":  ["arjun", "office", "arjun's office"],
    "Reading hall":    ["reading", "hall", "reading hall"],
    "Storage room":    ["storage", "storage room"],
    "Interrogation":   ["interrogation"],
    "Admin office":    ["admin", "administrative", "admin office"],
    "Pantry":          ["pantry"],
}

VALID_LOCATIONS = list(LOCATION_KEYWORDS.keys())


# ── Request models ────────────────────────────────────────────

class TalkRequest(BaseModel):
    npc_name:     str
    player_input: str

class SearchRequest(BaseModel):
    location:    str | None = None   # button click
    player_text: str | None = None   # text input

class AccuseRequest(BaseModel):
    suspect: str


# ── Helpers ───────────────────────────────────────────────────

def extract_location_from_text(text: str) -> str | None:
    text_lower = text.lower()
    for location, keywords in LOCATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return location
    return None


def extract_response(graph_state: dict) -> dict:
    npcs        = graph_state.get("npcs", {})
    current_npc = graph_state.get("current_npc", "")
    npc_reply   = ""

    if current_npc and current_npc in npcs:
        chat = npcs[current_npc].chat_history
        if chat:
            npc_reply = chat[-1].get("npc", "")

    scores = {
        npc_id: npc.sus
        for npc_id, npc in npcs.items()
        if npc_id != "officer"
    }

    summaries = {
        npc_id: npc.running_summary
        for npc_id, npc in npcs.items()
        if npc_id != "officer"
    }

    lies_caught = {
        npc_id: npc.lies_caught
        for npc_id, npc in npcs.items()
        if npc_id != "officer"
    }

    return {
        "npc_reply":            npc_reply,
        "officer_output":       graph_state.get("officer_output", ""),
        "scores":               scores,
        "total_suspicion":      sum(scores.values()),
        "evidence_found":       graph_state.get("evidence_found", []),
        "locations_unlocked":   graph_state.get("locations_unlocked", {}),
        "accusation_available": graph_state.get("accusation_available", False),
        "summaries":            summaries,
        "lies_caught":          lies_caught,
    }


# ── Endpoints ─────────────────────────────────────────────────

# ENNDPOINT 1
@app.get("/start")
def start_game():
    global THREAD

    # New thread_id = fresh game session every time
    THREAD = {"configurable": {"thread_id": f"shimla_{int(time.time())}"}}

    # Only place that calls invoke(state) — fresh graph start
    result = garph.invoke(state, config=THREAD)

    return {
        "status":    "game_started",
        "thread_id": THREAD["configurable"]["thread_id"],
        **extract_response(result)
    }

#  ENDPOINT 2

@app.post("/talk")
def talk(request: TalkRequest):
    npc_name     = request.npc_name.lower().strip()
    player_input = request.player_input.strip()

    if npc_name not in ["arjun", "graves", "bell", "officer"]:
        return {"error": f"Unknown NPC: {npc_name}"}

    result = garph.invoke(
        Command(
            resume = player_input,
            update = {
                "current_npc":     npc_name,
                "player_input":    player_input,
                "search":          False,
                "search_location": "",
            }
        ),
        config=THREAD
    )

    return extract_response(result)

# ENDPOINT 3

@app.post("/search")
def search(request: SearchRequest):
    location = None

    if request.location:
        # Button path — location sent directly
        location = request.location.strip()

    elif request.player_text:
        # Text path — extract location from player message
        location = extract_location_from_text(request.player_text)
        if not location:
            return {
                "error":   "no_location_found",
                "message": "Could not identify a location. Try mentioning storage room, pantry, admin office etc."
            }
    else:
        return {
            "error":   "missing_input",
            "message": "Provide either a location name or player text."
        }

    if location not in VALID_LOCATIONS:
        return {
            "error":   "invalid_location",
            "message": f"Unknown location: {location}"
        }

    # Both button and text paths resume graph identically from here
    result = garph.invoke(
        Command(
            resume = "",
            update = {
                "search":          True,
                "search_location": location,
                "current_npc":     "",
                "player_input":    "",
            }
        ),
        config=THREAD
    )

    return {
        "script":            result.get("officer_output", ""),
        "location_searched": location,
        **extract_response(result)
    }

# ENDPOINT 4

@app.post("/accuse")
def accuse(request: AccuseRequest):
    suspect = request.suspect.strip().lower()

    result = garph.invoke(
        Command(
            resume = suspect,
            update = {
                "current_npc":     suspect,
                "player_input":    suspect,
                "search":          False,
                "search_location": "",
            }
        ),
        config=THREAD
    )

    return {
        "result":  result.get("officer_output", ""),
        "correct": suspect == "graves",
        **extract_response(result)
    }

# ENDPOINT 5 

@app.get("/state")
def get_state():
    # Read-only — does not resume graph, just reads frozen state
    current = garph.get_state(config=THREAD)
    values  = current.values if current else {}
    return extract_response(values)
