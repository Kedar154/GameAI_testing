# fastapi_connection.py
# Run: uvicorn fastapi_connection:app --reload
# Test: http://localhost:8000/docs

import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

from nodes.graph     import garph_
from nodes.gamestate import state

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

THREAD       = {"configurable": {"thread_id": "shimla_default"}}
LATEST_STATE = {}

VALID_NPCS = {"arjun", "bell", "graves", "officer"}

VALID_LOCATIONS = {
    "Thorne's study",
    "Arjun's office",
    "Reading hall",
    "Storage room",
    "Interrogation",
    "Admin office",
    "Pantry",
}

LOCATION_KEYWORDS = {
    "Thorne's study": ["thorne", "study", "thorne's study"],
    "Arjun's office": ["arjun", "office", "arjun's office"],
    "Reading hall":   ["reading", "hall", "reading hall"],
    "Storage room":   ["storage", "storage room"],
    "Interrogation":  ["interrogation"],
    "Admin office":   ["admin", "administrative", "admin office"],
    "Pantry":         ["pantry"],
}


# ── Request Models ─────────────────────────────────────────────

class TalkRequest(BaseModel):
    npc_name:     str
    player_input: str

class SearchRequest(BaseModel):
    location:    str | None = None   # button click
    player_text: str | None = None   # text input


# ── Helpers ────────────────────────────────────────────────────

def extract_location_from_text(text: str) -> str | None:
    text_lower = text.lower()
    for location, keywords in LOCATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return location
    return None


def extract_response(graph_state: dict) -> dict:
    npcs        = graph_state.get("npcs", {})
    scores      = {}
    summaries   = {}
    lies_caught = {}

    for npc_id, npc in npcs.items():
        #if npc_id == "officer":
        #    continue
        scores[npc_id]      = getattr(npc, "sus", 0.0)
        summaries[npc_id]   = getattr(npc, "running_summary", "")
        lies_caught[npc_id] = getattr(npc, "lies_caught", [])

    return {
        "current_npc":          graph_state.get("current_npc", ""),
        "npc_reply":            graph_state.get("npc_response", ""),
        "search_result":        graph_state.get("search_result", ""),
        "scores":               scores,
        "total_suspicion":      sum(scores.values()),
        "evidence_found":       graph_state.get("evidence_found", []),
        "locations_unlocked":   graph_state.get("locations_unlocked", {}),
        "accusation_available": graph_state.get("accusation_available", False),
        "summaries":            summaries,
        "lies_caught":          lies_caught,
    }


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/start")
def start_game():
    global THREAD, LATEST_STATE

    THREAD = {"configurable": {"thread_id": f"shimla_{int(time.time())}"}}

    result       = garph_.invoke(state, config=THREAD)
    LATEST_STATE = result

    return {
        "status":    "game_started",
        "thread_id": THREAD["configurable"]["thread_id"],
        **extract_response(result)
    }


@app.post("/talk")
def talk(request: TalkRequest):
    global LATEST_STATE

    npc_name     = request.npc_name.lower().strip()
    player_input = request.player_input.strip()

    if npc_name not in VALID_NPCS:
        return {"error": "invalid_npc", "message": f"Unknown NPC: {npc_name}"}

    if not player_input:
        return {"error": "empty_input", "message": "player_input cannot be empty."}

    result = garph_.invoke(
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
    LATEST_STATE = result

    return {"action": "talk", **extract_response(result)}


@app.post("/search")
def search(request: SearchRequest):
    global LATEST_STATE

    location = None

    if request.location:
        location = request.location.strip()
    elif request.player_text:
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

    result = garph_.invoke(
        Command(
            resume = f"search {location} for me",
            update = {
                "search":          True,
                "search_location": location,
                "current_npc":     "officer",
                "player_input":    f"search {location} for me",
            }
        ),
        config=THREAD
    )
    LATEST_STATE = result

    return {
        "action":            "search",
        "location_searched": location,
        **extract_response(result)
    }


@app.get("/current-situation")
def current_situation():
    npcs = LATEST_STATE.get("npcs", {})

    npc_summaries = {
        npc_id: getattr(npc, "running_summary", "No interactions yet.")
        for npc_id, npc in npcs.items()
        if npc_id != "officer"
    }

    return {
        "status":               "current_game_state",
        "evidence_found":       LATEST_STATE.get("evidence_found", []),
        "locations_unlocked":   LATEST_STATE.get("locations_unlocked", {}),
        "accusation_available": LATEST_STATE.get("accusation_available", False),
        "npc_summaries":        npc_summaries,
    }