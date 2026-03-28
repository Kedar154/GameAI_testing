
# EVIDENCE DATABASE

EVIDENCE_DB = {
    "brandy_glass": {"suspect": "graves", "score": 5, "script": "The glass on his desk. Bitter. Sharp. That's not the drink."},
    "stopped_clock": {"suspect": "graves", "score": 3, "script": "The clock stopped. 8:43 PM."},
    "torn_manuscript": {"suspect": "arjun", "score": 8, "script": "Page 42 is gone — torn out cleanly."},
    "thorne_diary": {"suspect": "graves", "score": 8, "script": "Tonight's entry: 7:10 PM, Mrs. Graves."},
    "page_42": {"suspect": "arjun", "score": 15, "script": "Found it. Page 42 — tucked inside a catalog folder."},
    "arjun_margin_notes": {"suspect": "arjun", "score": 5, "script": "Notes in his handwriting — 'page 42, Thorne reviewing'."},
    "bells_field_journal": {"suspect": "bell", "score": 5, "script": "Aconite extract, concentrated — for separate storage."},
    "bells_smuggling_crates": {"suspect": "bell", "score": 10, "script": "Himalayan monkshood. Protected species, falsely labelled."},
    "empty_aconite_vial": {"suspect": "bell", "score": 10, "script": "Open vial case. Label reads Aconitum. Empty."},
    "empty_aconite_vial_graves_link": {"suspect": "graves", "score": 20, "script": None},
    "bells_testimony": {"suspect": "graves", "score": 25, "script": "Bell placed Mrs. Graves in the pantry corridor at 7:15."},
    "coal_ledger_discrepancies": {"suspect": "graves", "score": 30, "script": "Every approval carries Mrs. Graves's signature."},
    "graves_personal_letters": {"suspect": "graves", "score": 10, "script": "Overdue notices. Payment requests. She needed the money."},
    "pantry_service_log": {"suspect": "graves", "score": 35, "script": "Thorne's brandy, 7:25 PM. Signed by Mrs. Eleanor Graves."},
    "pantry_bitter_smell": {"suspect": "graves", "score": 10, "script": "That smell again. Stronger here."},
    "empty_decanter_residue": {"suspect": "graves", "score": 15, "script": "Residue on the stopper. Same bitter compound."}
}


# LOCATION → EVIDENCE

LOCATION_EVIDENCE = {
    "Thorne's study": ["thorne_diary"],
    "Arjun's office": ["page_42", "arjun_margin_notes"],
    "Reading hall": ["bells_field_journal"],
    "Storage room": ["bells_smuggling_crates", "empty_aconite_vial"],
    "Interrogation": ["bells_testimony"],
    "Admin office": ["coal_ledger_discrepancies", "graves_personal_letters"],
    "Pantry": ["pantry_service_log", "pantry_bitter_smell", "empty_decanter_residue"]
}


# ACCUSATION REQUIREMENTS

ACCUSATION_REQUIRED = {
    "coal_ledger_discrepancies",
    "empty_aconite_vial",
    "pantry_service_log"
}


# HELPER

def total_suspicion(state: State) -> float:
    return (
        state["npcs"]["arjun"].sus
        + state["npcs"]["bell"].sus
        + state["npcs"]["graves"].sus
    )


# NODE 1: DISCOVER EVIDENCE
# Uses state["last_found_evidence"]

def discover_evidence_node(state: State) -> dict:
    evidence_id = state["last_found_evidence"]

    if not evidence_id:
        return {"officer_output": "No evidence selected."}

    if evidence_id not in EVIDENCE_DB:
        return {"officer_output": "Invalid evidence ID."}

    if evidence_id in state["evidence_found"]:
        return {"officer_output": "Evidence already found."}

    item = EVIDENCE_DB[evidence_id]
    suspect = item["suspect"]
    score = item["score"]

    updated_evidence = state["evidence_found"].copy()
    updated_evidence.append(evidence_id)

    updated_npcs = state["npcs"].copy()
    updated_npcs[suspect].sus += score

    if evidence_id == "empty_aconite_vial":
        if "empty_aconite_vial_graves_link" not in updated_evidence:
            updated_evidence.append("empty_aconite_vial_graves_link")
            updated_npcs["graves"].sus += 20

    return {
        "evidence_found": updated_evidence,
        "npcs": updated_npcs,
        "officer_output": item["script"] or ""
    }


# NODE 2: OFFICER SEARCH
# Uses state["current_location"]

def officer_search_node(state: State) -> dict:
    location = state["current_location"]

    if not state["locations_unlocked"].get(location, False):
        return {
            "officer_output": "This location is locked.",
            "last_found_evidence": None
        }

    for evidence_id in LOCATION_EVIDENCE.get(location, []):
        if evidence_id not in state["evidence_found"]:
            return {
                "last_found_evidence": evidence_id
            }

    return {
        "officer_output": "Nothing more to find here.",
        "last_found_evidence": None
    }


# NODE 3: GATE UPDATES

def update_gates_node(state: State) -> dict:
    total = total_suspicion(state)
    case = state["evidence_found"]

    updated_locations = state["locations_unlocked"].copy()

    arjun_sus = state["npcs"]["arjun"].sus
    bell_sus = state["npcs"]["bell"].sus

    if total > 15 and "brandy_glass" in case:
        updated_locations["Storage room"] = True

    if total > 50 and arjun_sus > 20:
        updated_locations["Admin office"] = True

    if total > 90 and bell_sus > 20:
        updated_locations["Pantry"] = True

    accusation_available = ACCUSATION_REQUIRED.issubset(set(case))

    return {
        "locations_unlocked": updated_locations,
        "accusation_available": accusation_available
    }


# NODE 4: INTERROGATION UNLOCK

def unlock_interrogation_node(state: State) -> dict:
    updated_locations = state["locations_unlocked"].copy()
    updated_locations["Interrogation"] = True

    return {
        "locations_unlocked": updated_locations
    }


# NODE 5: ACCUSATION

def accusation_node(state: State) -> dict:
    accused_name = state["current_npc"].strip().lower()

    if not state["accusation_available"]:
        return {
            "officer_output": "Not enough evidence yet."
        }

    if accused_name == "graves":
        return {
            "officer_output": "Correct. Mrs. Graves is the killer."
        }

    return {
        "officer_output": f"Wrong. The evidence does not support accusing {accused_name}."
    }
