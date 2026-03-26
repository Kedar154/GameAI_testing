
global_state = {
    "phase": 1,
    "input": "",
    "intent": None,

    "npc_states": {
        "arjun": {
            "suspicion": 0,
            "mental_state": "neutral",
            "lies": [],
            "known_location": None
        },
        "mrs_graves": {
            "suspicion": 0,
            "mental_state": "calm",
            "lies": [],
            "known_location": None
        },
        "dr_bell": {
            "suspicion": 0,
            "mental_state": "neutral",
            "lies": [],
            "known_location": None,
            "missing_vial": False
        }
    },

    "collected_evidence": [],

    "locations_unlocked": {
        "Thorne's study": True,
        "Arjun's office": True,
        "Reading hall": True,
        "Storage room": False,
        "Interrogation": False,
        "Admin office": False,
        "Pantry": False
    },

    "accusation_available": False
}


#  EVIDENCE DATABASE 
EVIDENCE_DB = {
    "brandy_glass":                   {"suspect": "mrs_graves", "score": 5,  "script": "The glass on his desk. Bitter. Sharp. That's not the drink."},
    "stopped_clock":                  {"suspect": "mrs_graves", "score": 3,  "script": "The clock stopped. 8:43 PM."},
    "torn_manuscript":                {"suspect": "arjun",      "score": 8,  "script": "Page 42 is gone — torn out cleanly."},
    "thorne_diary":                   {"suspect": "mrs_graves", "score": 8,  "script": "Tonight's entry: 7:10 PM, Mrs. Graves."},
    "page_42":                        {"suspect": "arjun",      "score": 15, "script": "Found it. Page 42 — tucked inside a catalog folder."},
    "arjun_margin_notes":             {"suspect": "arjun",      "score": 5,  "script": "Notes in his handwriting — 'page 42, Thorne reviewing'."},
    "bells_field_journal":            {"suspect": "dr_bell",    "score": 5,  "script": "Aconite extract, concentrated — for separate storage."},
    "bells_smuggling_crates":         {"suspect": "dr_bell",    "score": 10, "script": "Himalayan monkshood. Protected species, falsely labelled."},
    "empty_aconite_vial":             {"suspect": "dr_bell",    "score": 10, "script": "Open vial case. Label reads Aconitum. Empty."},
    "empty_aconite_vial_graves_link": {"suspect": "mrs_graves", "score": 20, "script": None},
    "bells_testimony":                {"suspect": "mrs_graves", "score": 25, "script": "Bell placed Mrs. Graves in the pantry corridor at 7:15."},
    "coal_ledger_discrepancies":      {"suspect": "mrs_graves", "score": 30, "script": "Every approval carries Mrs. Graves's signature."},
    "graves_personal_letters":        {"suspect": "mrs_graves", "score": 10, "script": "Overdue notices. Payment requests. She needed the money."},
    "pantry_service_log":             {"suspect": "mrs_graves", "score": 35, "script": "Thorne's brandy, 7:25 PM. Signed by Mrs. Eleanor Graves."},
    "pantry_bitter_smell":            {"suspect": "mrs_graves", "score": 10, "script": "That smell again. Stronger here."},
    "empty_decanter_residue":         {"suspect": "mrs_graves", "score": 15, "script": "Residue on the stopper. Same bitter compound."}
}


#  LOCATION → EVIDENCE 

LOCATION_EVIDENCE = {
    "Thorne's study": ["thorne_diary"],
    "Arjun's office": ["page_42", "arjun_margin_notes"],
    "Reading hall":   ["bells_field_journal"],
    "Storage room":   ["bells_smuggling_crates", "empty_aconite_vial"],
    "Interrogation":  ["bells_testimony"],
    "Admin office":   ["coal_ledger_discrepancies", "graves_personal_letters"],
    "Pantry":         ["pantry_service_log", "pantry_bitter_smell", "empty_decanter_residue"]
}


# ─ ACCUSATION REQUIREMENTS

ACCUSATION_REQUIRED = {
    "coal_ledger_discrepancies",
    "empty_aconite_vial",
    "pantry_service_log"
}


#  HELPER: TOTAL SUSPICION 

def total_suspicion(global_state):
    return sum(npc["suspicion"] for npc in global_state["npc_states"].values())


#  NODE 1: EVIDENCE DISCOVERY / OFFICER SEARCH 

def discover_evidence(global_state, evidence_id):
    if evidence_id not in EVIDENCE_DB:
        return global_state, "Invalid evidence ID."

    if evidence_id in global_state["collected_evidence"]:
        return global_state, None

    item = EVIDENCE_DB[evidence_id]
    suspect = item["suspect"]
    score = item["score"]

    # Add evidence
    global_state["collected_evidence"].append(evidence_id)

    # Update only target NPC suspicion
    global_state["npc_states"][suspect]["suspicion"] += score

    # Special trigger
    if evidence_id == "empty_aconite_vial":
        global_state["collected_evidence"].append("empty_aconite_vial_graves_link")
        global_state["npc_states"]["mrs_graves"]["suspicion"] += 20
        

    global_state = update_gates(global_state)
    return global_state, item["script"]


def officer_search_node(global_state, location):
    if not global_state["locations_unlocked"].get(location):
        return global_state, "This location is locked."

    for evidence_id in LOCATION_EVIDENCE.get(location, []):
        if evidence_id not in global_state["collected_evidence"]:
            return discover_evidence(global_state, evidence_id)

    return global_state, "Nothing more to find here."

# NODE 2: GATE UPDATES
def update_gates(global_state):
    total = total_suspicion(global_state)
    case = global_state["collected_evidence"]
    npc = global_state["npc_states"]
    unlocked = global_state["locations_unlocked"]

    if total > 15 and "brandy_glass" in case:
        unlocked["Storage room"] = True

    if total > 50 and npc["arjun"]["suspicion"] > 20:
        unlocked["Admin office"] = True

    if total > 90 and npc["dr_bell"]["suspicion"] > 20:
        unlocked["Pantry"] = True

    global_state["accusation_available"] = ACCUSATION_REQUIRED.issubset(set(case))
    return global_state


# NODE 3: INTERROGATION UNLOCK 
# Pipeline can call this when Bell / other suspect "breaks"

def unlock_interrogation(global_state):
    global_state["locations_unlocked"]["Interrogation"] = True
    return global_state

# NODE 4: ACCUSATION CHECK 
def accusation_node(global_state, accused_name):
    if not global_state["accusation_available"]:
        return global_state, "Not enough evidence yet."

    if accused_name.strip().lower() == "mrs_graves":
        return global_state, "Correct. Mrs. Graves is the killer."

    return global_state, f"Wrong. The evidence does not support accusing {accused_name}."


