NPC_ID_MAP = {
    "arjun": "Arjun Singh",
    "bell":  "Dr. Arthur Bell",
    "graves":"Mrs. Eleanor Graves",
}

EVIDENCE_WEIGHTS = {
    "brandy_glass":               {"npc": "graves", "score": 5},
    "stopped_clock":              {"npc": "graves", "score": 3},
    "thornes_appointment_diary":  {"npc": "graves", "score": 8},
    "torn_manuscript":            {"npc": "arjun",  "score": 8},
    "page_42":                    {"npc": "arjun",  "score": 15},
    "arjuns_margin_notes":        {"npc": "arjun",  "score": 5},
    "bells_field_journal":        {"npc": "bell",   "score": 5},
    "bells_smuggling_crates":     {"npc": "bell",   "score": 10},
    "empty_aconite_vial_bell":    {"npc": "bell",   "score": 10},
    "empty_aconite_vial_graves":  {"npc": "graves", "score": 20},
    "bells_testimony":            {"npc": "graves", "score": 25},
    "coal_ledger":                {"npc": "graves", "score": 30},
    "graves_personal_letters":    {"npc": "graves", "score": 10},
    "pantry_service_log":         {"npc": "graves", "score": 35},
    "pantry_bitter_smell":        {"npc": "graves", "score": 10},
    "empty_decanter_residue":     {"npc": "graves", "score": 15},
}

LOCATION_GATES = {
    "thornes_study":  None,
    "arjuns_office":  None,
    "reading_hall":   None,
    "storage_room":   {"total_sus": 15, "case_file_requires": "brandy_glass"},
    "admin_office":   {"total_sus": 50, "npc_sus": {"arjun": 20}},
    "pantry":         {"total_sus": 90, "npc_sus": {"bell": 20}},
}

ACCUSATION_REQUIRED = {
    "coal_ledger", "empty_aconite_vial_graves", "pantry_service_log"
}

EMOTION_THRESHOLDS = {
    "graves": {"breakdown": 95, "pre_breakdown": 75, "defensive": 25},
    "arjun":  {"breakdown": 28, "defensive": 16},
    "bell":   {"breakdown": 25, "defensive": 15},
}